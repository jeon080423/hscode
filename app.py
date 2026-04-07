import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math
import numpy as np
import base64
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import api_client
import data_processor

# 초기화
client = api_client.CustomsAPIClient()
processor = data_processor.DataProcessor()

# 페이지 설정
st.set_page_config(page_title="ICT 수출입 실적 모니터링", layout="wide", initial_sidebar_state="expanded")

# 캐시 초기화 등은 함수의 내부 로직으로 관리
@st.cache_data(ttl=3600)
def load_ict_data():
    """가장 핵심적인 ICT 품목만 확실하고 빠르게 로드합니다."""
    # 확실한 화력을 가진 3대 품목 우선 (반도체, 휴대폰, 컴퓨터)
    target_hs = {
        "반도체": "8542",
        "휴대폰/통신": "8517",
        "컴퓨터/SSD": "8471"
    }
    
    # 확실한 데이터가 있는 202602, 202601월 위주
    dates = ["202602", "202601", "202512"]
    all_results = []
    
    with st.status("📊 ICT 핵심 실적 분석 중...", expanded=False) as status:
        for d in dates:
            for name, code in target_hs.items():
                df_part, _ = client.fetch_monthly_data(d, code)
                if df_part is not None and not df_part.empty:
                    # 요약 합산
                    row = df_part.iloc[0].copy()
                    row['exp_amount'] = df_part['exp_amount'].sum()
                    row['imp_amount'] = df_part['imp_amount'].sum()
                    row['item_name'] = name
                    row['year_month'] = d
                    row['hs_code'] = code
                    all_results.append(pd.DataFrame([row]))
        status.update(label="✅ 데이터 동기화 완료", state="complete")

    if not all_results: return pd.DataFrame()
    df = pd.concat(all_results, ignore_index=True)
    
    # 간단한 카테고리 매핑
    def map_cat(hs):
        if hs == "8542": return "전자부품"
        if hs == "8517": return "통신장비"
        return "컴퓨터 및 주변기기"
    
    df['category'] = df['hs_code'].apply(map_cat)
    return df

@st.cache_data(ttl=3600)
def load_history_simple():
    """역사 데이터를 단순화하여 로드합니다."""
    # ICT 합계 트렌드용 (반도체 대표 코드 활용)
    dates = [f"2025{m:02d}" for m in range(1, 13)]
    hist = []
    for d in dates:
        df, _ = client.fetch_monthly_data(d, "8542")
        if df is not None:
            hist.append({'year_month': d, 'category': 'ICT합계', 'exp_amount': df['exp_amount'].sum()})
    return pd.DataFrame(hist)

# 헤더 섹션 (CI 로고 포함)
logo_path = "assets/metrix_logo.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_data}" style="height:40px; margin-left:20px;">'
else:
    logo_html = ""

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; background:#f8fafc; padding:15px 25px; border-bottom:2px solid #3b82f6; margin-bottom:25px; border-radius:8px;">
    <div style="font-size:26px; font-weight:800; color:#1e293b;">
        2026년 ICT통계조사 실사 용역 {logo_html}
    </div>
    <div style="text-align:right; font-size:12px; color:#64748b;">
        ICT 수출입 실적 모니터링 시스템<br>Data Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>
</div>
""", unsafe_allow_html=True)

# 사이드바
with st.sidebar:
    st.title("🚢 거시지표 설정")
    st.info("💡 관세청 및 한국은행 실측 API 연동 중")
    if st.button("🔄 데이터 강제 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 메인 데이터 로드
df = load_ict_data()
df_history = load_history_simple()

if not df.empty:
    all_months = sorted(df['year_month'].unique())
    latest_month = all_months[-1]
    prev_month = all_months[-2] if len(all_months) > 1 else latest_month
    
    curr_df = df[df['year_month'] == latest_month]
    prev_df = df[df['year_month'] == prev_month]
    
    tabs = st.tabs(["📌 품목군별 분석", "📈 10개년 성장률", "☁️ 서비스 무역"])
    
    with tabs[0]:
        st.subheader(f"📊 {latest_month[:4]}년 {latest_month[4:]}월 ICT 주요 품목 실적")
        cols = st.columns(3)
        cat_data = curr_df.groupby('category').sum().reset_index()
        
        for i, row in cat_data.iterrows():
            with cols[i % 3]:
                # 전월비 계산
                p_val = prev_df[prev_df['category'] == row['category']]['exp_amount'].sum()
                mom = ((row['exp_amount'] - p_val) / p_val * 100) if p_val > 0 else 0
                
                color = "#ef4444" if mom > 0 else "#3b82f6"
                st.markdown(f"""
                <div style="background:white; padding:20px; border-radius:12px; box-shadow:0 4px 6px -1px rgb(0 0 0 / 0.1); border-left:5px solid {color};">
                    <div style="font-size:14px; color:#64748b; font-weight:600;">{row['category']}</div>
                    <div style="font-size:28px; font-weight:800; color:#1e293b; margin:10px 0;">${row['exp_amount']:,.0f} <span style="font-size:14px; color:#64748b;">M</span></div>
                    <div style="font-size:14px; color:{color}; font-weight:700;">MoM {mom:+.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
                st.write("")

    with tabs[1]:
        if not df_history.empty:
            st.subheader("🌐 ICT 수출 연간 트렌드 (실측 기반)")
            fig = px.line(df_history, x='year_month', y='exp_amount', title="연도별 ICT 수출액 추이",
                         template="plotly_white", line_shape="spline", markers=True)
            fig.update_traces(line_color='#3b82f6', line_width=4)
            st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        st.info("서비스 무역 API 연동 데이터를 준비 중입니다.")
else:
    st.warning("⚠️ API로부터 유효한 ICT 데이터를 가져오지 못했습니다. 잠시 후 다시 시도하거나 사이드바의 새로고침을 눌러주세요.")
    st.write("진단 정보: 수집된 데이터셋이 비어있습니다.")
