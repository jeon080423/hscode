import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math
import numpy as np
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import api_client
import data_processor

# 페이지 설정
st.set_page_config(page_title="ICT 품목 및 서비스 무역 실적 통계 대시보드", layout="wide")

# 스타일 설정
st.markdown("""
<style>
    .metric-card {
        background-color: white;
        padding: 12px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 10px;
        min-height: 120px;
    }
    .metric-label { font-size: 0.85rem; color: #4b5563; font-weight: 600; margin-bottom: 4px; }
    .metric-value { font-size: 1.15rem; font-weight: 700; color: #111827; margin-bottom: 10px; }
    .delta-row { display: flex; justify-content: flex-start; gap: 10px; border-top: 1px solid #f3f4f6; padding-top: 8px; }
    .delta-box { display: flex; flex-direction: column; }
    .delta-tag { font-size: 0.7rem; color: #9ca3af; margin-bottom: 1px; }
    .delta-val { font-size: 0.85rem; font-weight: 600; }
    .up { color: #059669; }
    .down { color: #dc2626; }
    .yoy-up { color: #2563eb; }
    .yoy-down { color: #d97706; }
    h1, h2, h3 { color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# 인스턴스 초기화
client = api_client.CustomsAPIClient()
processor = data_processor.DataProcessor()

@st.cache_data(ttl=3600)
def fetch_month_bulk(date_str):
    """특정 월의 데이터를 HS 2자리 벌크 조회로 빠르게 가져옵니다."""
    bulk_prefixes = ["84", "85", "90"]
    month_data = []
    for prefix in bulk_prefixes:
        df_range, _ = client.fetch_monthly_data(date_str, prefix)
        if df_range is not None and not df_range.empty:
            month_data.append(df_range)
    return pd.concat(month_data, ignore_index=True) if month_data else pd.DataFrame()

# 관세청 HS코드와 ICT 품목 분류 간의 가교 매핑 (MTI 코드 불일치 해결용)
HS_TO_ICT_MAPPING = {
    "반도체": "8542",
    "휴대폰": "8517",
    "컴퓨터": "8471",
    "디스플레이": "8524",
    "보조기억장치(SSD)": "847170",
    "센서/개별소자": "8541",
    "유선통신기기": "851762",
    "방송장비": "8525",
    "영상기기": "8528",
    "컴퓨터부품": "8473"
}

@st.cache_data(ttl=3600)
def load_data(months=13):
    """HS-ICT 매핑을 활용하여 데이터를 정밀 필터링 및 복구합니다."""
    if not os.path.exists("data"): os.makedirs("data")
    
    end_date = datetime.now()
    base_date = end_date - timedelta(days=20) 
    dates = [(base_date - timedelta(days=30*i)).strftime("%Y%m") for i in range(months)]
    dates.sort()

    # bulk_prefixes는 API 호출 시 사용
    bulk_prefixes = ["84", "85", "90"]
    tasks = [(d, p) for d in dates for p in bulk_prefixes]
    total_tasks = len(tasks)
    
    raw_data_map = {d: [] for d in dates}
    
    with st.status("⚡ 실시간 데이터 복구 및 동기화 중...", expanded=True) as status:
        pbar = st.progress(0, text="글로벌 통계 서버 접속 중...")
        
        with ThreadPoolExecutor(max_workers=15) as executor:
            future_to_task = {executor.submit(client.fetch_monthly_data, d, p): (d, p) for d, p in tasks}
            
            completed = 0
            for future in as_completed(future_to_task):
                d, p = future_to_task[future]
                try:
                    df_part, _ = future.result()
                    if df_part is not None and not df_part.empty:
                        raw_data_map[d].append(df_part)
                except Exception: pass
                
                completed += 1
                progress = int((completed / total_tasks) * 100)
                pbar.progress(progress, text=f"📊 데이터 매핑 및 복구 중... ({progress}%)")
        
        all_results = []
        for d, df_list in raw_data_map.items():
            if not df_list: continue
            df_month_raw = pd.concat(df_list, ignore_index=True)
            
            # MTI 코드 대조 대신 HS 매핑 기반으로 품목 재정립
            for item_name, hs_prefix in HS_TO_ICT_MAPPING.items():
                mask = df_month_raw['hs_code'].str.startswith(hs_prefix)
                df_match = df_month_raw[mask].copy()
                if not df_match.empty:
                    row = df_match.iloc[0].copy()
                    row['exp_amount'] = df_match['exp_amount'].sum()
                    row['imp_amount'] = df_match['imp_amount'].sum()
                    row['item_name'] = item_name
                    row['year_month'] = d
                    row['hs_code'] = hs_prefix # 필터링에 사용된 코드로 고정
                    all_results.append(pd.DataFrame([row]))
        
        status.update(label="✅ 데이터 복구 완료", state="complete", expanded=False)
        pbar.empty()

    if not all_results: return pd.DataFrame()
    df_combined = pd.concat(all_results, ignore_index=True)
    
    # 카테고리 보정 로직 (HS 기반 재매핑)
    def fix_category(row):
        hs = str(row['hs_code'])
        if hs.startswith('8542'): return "전자부품"
        if hs.startswith('8517'): return "통신장비"
        if hs.startswith('8471'): return "컴퓨터 및 주변기기"
        if hs.startswith('852'): return "방송장비"
        if hs.startswith('90'): return "정보통신응용기반기기"
        return "기타 ICT"

    df_combined['category'] = df_combined.apply(fix_category, axis=1)
    return df_combined

@st.cache_data(ttl=3600)
def load_category_history(years=3):
    """역사 데이터 또한 HS 기반으로 고속 집계합니다."""
    cache_path = "data/history_v2_cache.csv"
    if os.path.exists(cache_path):
        try: return pd.read_csv(cache_path, dtype={'year_month': str})
        except: pass
    
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=30*i)).strftime("%Y%m") for i in range(years * 12)]
    
    def fetch_fast_hist(d):
        # 전자(85)와 전산(84)만 합산해도 ICT의 90%
        df_85, _ = client.fetch_monthly_data(d, "85")
        df_84, _ = client.fetch_monthly_data(d, "84")
        total = 0
        if df_85 is not None: total += df_85['exp_amount'].sum()
        if df_84 is not None: total += df_84['exp_amount'].sum()
        return [{'year_month': d, 'category': 'ICT합계', 'exp_amount': total}]

    all_hist = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_fast_hist, d): d for d in dates}
        for f in as_completed(futures):
            all_hist.extend(f.result())
            
    df_h = pd.DataFrame(all_hist) if all_hist else pd.DataFrame()
    if not df_h.empty: df_h.to_csv(cache_path, index=False)
    return df_h

# 헤더 섹션 (CI 로고 포함)
logo_path = "assets/metrix_logo.png"
logo_html = ""
import os
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{data}" style="height:35px; margin-left:15px;">'

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; background:linear-gradient(90deg, #f8fafc 0%, #ffffff 100%); padding:15px 25px; border-bottom:2px solid #3b82f6; margin-bottom:25px; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
<div style="display:flex; align-items:center;">
<h1 style="margin:0; font-size:1.6rem; color:#1e3a8a; font-weight:800; letter-spacing:-0.5px;">2026년 ICT통계조사 실사 용역</h1>
{logo_html}
</div>
<div style="text-align:right;">
<span style="font-size:0.9rem; font-weight:700; color:#64748b;">ICT 수출입 실적 모니터링 시스템</span><br>
<span style="font-size:0.75rem; color:#94a3b8;">Data Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
</div>
</div>
""", unsafe_allow_html=True)

# 사이드바 및 데이터 로드
st.sidebar.title("📊 ICT Dashboard")
period = st.sidebar.selectbox("조회 기간", ["최근 12개월", "최근 6개월", "최근 3개월"], index=0)
months_map = {"최근 12개월": 12, "최근 6개월": 6, "최근 3개월": 3}
n_months = months_map[period]

st.sidebar.markdown("---")
st.sidebar.subheader("📡 데이터 출처")
st.sidebar.info("""
**품목별 수출입 통계**
- 관세청 (Korea Customs Service)
- 품목별 수출입실적(GW) 실시간 API

**서비스 무역 통계**
- 한국은행 (Bank of Korea)
- 경제통계시스템(ECOS) API
""")

with st.spinner('실시간 데이터를 분석 중입니다...'):
    df = load_data(13) # 품목용 13개월
    df_history = load_category_history(10) # 역사용 10년
    
    if not df.empty and 'year_month' in df.columns:
        all_months = sorted(df['year_month'].unique())
    else:
        all_months = []
    
    df_service = processor.get_service_trade_data(all_months)

display_months = all_months[-n_months:] if all_months else []
df_display = df.copy() if not df.empty else pd.DataFrame()
if not df.empty and 'year_month' in df.columns:
    df_curr_display = df[df['year_month'].isin(display_months)]
else:
    df_curr_display = pd.DataFrame()

# 탭 구성
tabs = st.tabs(["📌 품목군별 분석", "📈 품목별 상세", "📊 10개년 성장률", "☁️ 서비스 무역"])

# --- Tab 1: 품목군별 분석 ---
with tabs[0]:
    if not df.empty:
        cat_df = df[df['year_month'] == all_months[-1]].groupby('category').agg({'exp_amount':'sum', 'imp_amount':'sum'}).reset_index()
        # 이전월/전년월 합계 계산을 위한 수동 처리
        def get_cat_total(m):
            return df[df['year_month'] == m].groupby('category')['exp_amount'].sum()
        
        last_m = all_months[-1]
        prev_m = all_months[-2] if len(all_months) > 1 else last_m
        yoy_m = (datetime.strptime(last_m, "%Y%m") - timedelta(days=365)).strftime("%Y%m")
        
        curr_totals = get_cat_total(last_m)
        prev_totals = get_cat_total(prev_m)
        yoy_totals = get_cat_total(yoy_m)

        cat_items = list(cat_df.iterrows())
        COLS = 3
        for row_start in range(0, len(cat_items), COLS):
            cols = st.columns(COLS)
            for i in range(COLS):
                if row_start + i < len(cat_items):
                    idx, row = cat_items[row_start+i]
                    cat_name = row['category']
                    curr_val = curr_totals.get(cat_name, 0)
                    prev_val = prev_totals.get(cat_name, 0)
                    yoy_val = yoy_totals.get(cat_name, 0)
                    
                    mom_rate = ((curr_val - prev_val) / prev_val * 100) if prev_val > 0 else 0
                    yoy_rate = ((curr_val - yoy_val) / yoy_val * 100) if yoy_val > 0 else 0
                    
                    with cols[i]:
                        st.markdown(f"""
<div class="metric-card">
<div class="metric-label">{cat_name}</div>
<div class="metric-value">${curr_val:,.0f}M</div>
<div class="delta-row">
<div class="delta-box">
<div class="delta-tag">전월비(MoM)</div>
<div class="delta-val {'up' if mom_rate >=0 else 'down'}">{'▲' if mom_rate >=0 else '▼'} {abs(mom_rate):.1f}%</div>
</div>
<div class="delta-box">
<div class="delta-tag">전년비(YoY)</div>
<div class="delta-val {'yoy-up' if yoy_rate >=0 else 'yoy-down'}">{'▲' if yoy_rate >=0 else '▼'} {abs(yoy_rate):.1f}%</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
                        # 미니 차트 (최근 트렌드)
                        c_df = df[df['category'] == cat_name].groupby('year_month')['exp_amount'].sum().reset_index()
                        fig = px.line(c_df, x='year_month', y='exp_amount', height=100)
                        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), xaxis_visible=False, yaxis_visible=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"cat_spark_{idx}")

# --- Tab 2: 품목별 상세 ---
with tabs[1]:
    if not df.empty:
        df_latest = df[df['year_month'] == all_months[-1]].sort_values('exp_amount', ascending=False)
        st.dataframe(df_latest[['category', 'item_name', 'hs_code', 'exp_amount', 'imp_amount']], use_container_width=True)

# --- Tab 3: 10개년 성장률 (최적화 데이터 사용) ---
with tabs[2]:
    st.subheader("최근 10년 연간 수출액 및 성장률 추이")
    if not df_history.empty:
        # 연간 데이터로 집계
        df_history['year'] = df_history['year_month'].str[:4]
        annual_df = df_history.groupby('year')['exp_amount'].sum().reset_index()
        annual_df = annual_df.sort_values('year')
        annual_df['growth'] = annual_df['exp_amount'].pct_change() * 100
        
        fig_annual = go.Figure()
        fig_annual.add_trace(go.Bar(x=annual_df['year'], y=annual_df['exp_amount'], name="수출액($M)", marker_color='#3b82f6'))
        fig_annual.add_trace(go.Scatter(x=annual_df['year'], y=annual_df['growth'], name="성장률(%)", yaxis="y2", line=dict(color='#ef4444', width=3)))
        
        fig_annual.update_layout(
            yaxis=dict(title="수출액 ($M)"),
            yaxis2=dict(title="성장률 (%)", overlaying='y', side='right'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        st.plotly_chart(fig_annual, use_container_width=True)

# --- Tab 4: 서비스 무역 ---
with tabs[3]:
    if not df_service.empty:
        s_growth = processor.calculate_growth(df_service)
        cols_s = st.columns(len(s_growth))
        for i, (idx, s_row) in enumerate(s_growth.iterrows()):
            with cols_s[i]:
                st.markdown(f"""
<div class="metric-card">
<div class="metric-label">{s_row['service_name']}</div>
<div class="metric-value">${s_row['exp_amount']:,.1f}M</div>
<div class="delta-box">
<div class="delta-tag">전년비(YoY)</div>
<div class="delta-val up">{s_row['yoy_rate']:.1f}%</div>
</div>
</div>
""", unsafe_allow_html=True)
