import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math
import numpy as np
import base64
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
def load_data(months=13):
    """최근 N개월 데이터를 관세청 API로부터 실측 로드합니다 (품목 레벨)."""
    cache_path = "data/customs_cache.csv"
    import os
    if not os.path.exists("data"): os.makedirs("data")
    if os.path.exists(cache_path):
        try: cache_df = pd.read_csv(cache_path, dtype={'hs_code': str, 'year_month': str})
        except Exception: cache_df = pd.DataFrame()
    else: cache_df = pd.DataFrame()

    end_date = datetime.now()
    base_date = end_date - timedelta(days=20) 
    dates = [(base_date - timedelta(days=30*i)).strftime("%Y%m") for i in range(months)]
    dates.sort()

    ict_items = data_processor.ICT_DETAIL_ITEMS
    all_data = []
    
    for d in dates:
        if not cache_df.empty and d in cache_df['year_month'].unique():
            all_data.append(cache_df[cache_df['year_month'] == d])
            continue
            
        month_items = []
        for name, code in ict_items.items():
            df_item, err = client.fetch_monthly_data(d, code[:4])
            if df_item is not None and not df_item.empty:
                df_match = df_item[df_item['hs_code'].str.startswith(code[:6])]
                if df_match.empty: df_match = df_item.head(1)
                df_match = df_match.copy(); df_match['item_name'] = name; df_match['hs_code'] = code
                month_items.append(df_match)
        if month_items:
            month_df = pd.concat(month_items, ignore_index=True)
            all_data.append(month_df); cache_df = pd.concat([cache_df, month_df], ignore_index=True)

    if not all_data: return pd.DataFrame()
    combined = pd.concat(all_data, ignore_index=True)
    cache_df.drop_duplicates(subset=['year_month', 'item_name'], keep='last').to_csv(cache_path, index=False)
    combined = processor.categorize_data(combined)
    return combined

@st.cache_data(ttl=3600)
def load_category_history(years=10):
    """최근 10년 대분류별 데이터를 고속 로드합니다 (6개 대표 코드만 조회)."""
    cache_path = "data/category_history_cache.csv"
    import os
    if os.path.exists(cache_path):
        try: cache_df = pd.read_csv(cache_path, dtype={'year_month': str})
        except Exception: cache_df = pd.DataFrame()
    else: cache_df = pd.DataFrame()

    months = years * 12
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=30*i)).strftime("%Y%m") for i in range(months)]
    dates.sort()

    cat_prefixes = {
        "전자부품": "111", "컴퓨터 및 주변기기": "121", 
        "정보통신응용기반기기": "151", "방송장비": "131", 
        "통신장비": "141", "음향 및 영상기기": "161"
    }
    all_cat_data = []
    
    for d in dates:
        if not cache_df.empty and d in cache_df['year_month'].unique():
            all_cat_data.append(cache_df[cache_df['year_month'] == d])
            continue
            
        month_results = []
        for cat_name, prefix in cat_prefixes.items():
            df_cat, _ = client.fetch_monthly_data(d, prefix)
            if df_cat is not None and not df_cat.empty:
                total_exp = df_cat['exp_amount'].sum()
                month_results.append({'year_month': d, 'category': cat_name, 'exp_amount': total_exp})
        if month_results:
            m_df = pd.DataFrame(month_results)
            all_cat_data.append(m_df); cache_df = pd.concat([cache_df, m_df], ignore_index=True)

    if not all_cat_data: return pd.DataFrame()
    combined = pd.concat(all_cat_data, ignore_index=True)
    cache_df.to_csv(cache_path, index=False)
    return combined

# 헤더 섹션 (CI 로고 포함)
logo_path = "resources/ci_logo.png"
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

with st.spinner('실시간 데이터를 분석 중입니다...'):
    df = load_data(13) # 품목용 13개월
    df_history = load_category_history(10) # 역사용 10년
    all_months = sorted(df['year_month'].unique())
    df_service = processor.get_service_trade_data(all_months)

display_months = all_months[-n_months:] if all_months else []
df_display = df[df['year_status'] == 'current'] if not df.empty else df # categorize_data에서 처리됨
df_curr_display = df[df['year_month'].isin(display_months)]

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
