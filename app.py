import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math
import base64
import api_client
import data_processor

# 페이지 설정
st.set_page_config(page_title="관세청 ICT 품목별 수출 실적", layout="wide")

# 스타일 설정
st.markdown("""
<style>
    :root {
        color-scheme: light !important;
    }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #ffffff !important;
        color: #1e293b !important;
    }
    .main {
        background-color: #ffffff;
    }
    .metric-card {
        background-color: white;
        padding: 12px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 15px;
        min-height: 140px;
    }
    .metric-label { font-size: 0.95rem; color: #334155; font-weight: 700; margin-bottom: 2px;
                   overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .metric-value { font-size: 1.15rem; font-weight: 800; color: #0f172a; margin-bottom: 8px; }
    .delta-row { display: flex; gap: 6px; flex-wrap: nowrap; align-items: center; }
    .delta-badge { font-size: 0.72rem; font-weight: 700; padding: 2px 5px; border-radius: 4px; white-space: nowrap; }
    .up { color: #059669; background-color: #f0fdf4; }
    .down { color: #dc2626; background-color: #fef2f2; }
    .yoy-up { color: #2563eb; background-color: #eff6ff; }
    .yoy-down { color: #d97706; background-color: #fffbeb; }
    h1, h2, h3 { color: #1e3a8a; }
    .section-header { border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; margin-bottom: 20px; color: #1e3a8a; font-size: 1.5rem; font-weight: 700; }
    /* Streamlit 컨테이너 보더 및 여백 강력 제어 */
    [data-testid="stVerticalBlockBordered"] {
        background-color: white !important;
        padding: 2px 8px !important;
        min-height: 80px !important;
        height: 80px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        margin-bottom: 0px !important;
    }
    /* 컬럼 간격 최소화 */
    [data-testid="column"] {
        padding-left: 0px !important;
        padding-right: 0px !important;
    }
</style>
""", unsafe_allow_html=True)

# 인스턴스 초기화
client = api_client.CustomsAPIClient()
ecos_client = api_client.ECOSAPIClient()
processor = data_processor.DataProcessor()

import concurrent.futures

@st.cache_data(ttl=3600)
def load_data(months=13):
    """병렬 처리를 통해 데이터를 고속으로 로드합니다."""
    end_date = datetime.now()
    start_date = (end_date - timedelta(days=30 * (months - 1)))
    
    start_month = start_date.strftime("%Y%m")
    end_month = end_date.strftime("%Y%m")
    
    items_list = list(data_processor.ICT_DETAIL_ITEMS.items())
    total_items = len(items_list)
    
    all_rows = []
    
    # 병렬 호출 함수 정의
    def fetch_item_data(item_info):
        name, code = item_info
        df_part, _ = client.fetch_monthly_data(start_month, end_month, code)
        
        if df_part is not None and not df_part.empty:
            df_part['item_name'] = name
            df_part['is_error'] = False
            return df_part
        else:
            # 실측 데이터 로드 실패 시 가상 데이터 생성 대신 안내를 위한 빈 데이터프레임 반환
            # (UI에서 '데이터 로드 실패' 메시지를 출력하도록 유도)
            return pd.DataFrame([{
                'year_month': end_month,
                'hs_code': code,
                'item_name': name,
                'exp_amount': 0.0,
                'imp_amount': 0.0,
                'is_error': True
            }])

    # 병렬 실행 (최대 32개 스레드)
    with st.status("📊 ICT 품목별 데이터 병렬 동기화 중...", expanded=True) as status:
        progress_bar = st.progress(0)
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            future_to_item = {executor.submit(fetch_item_data, item): item for item in items_list}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_item):
                res_df = future.result()
                if res_df is not None:
                    all_rows.append(res_df)
                completed += 1
                progress_bar.progress(completed / total_items)
        
        status.update(label="✅ 고속 데이터 로드 완료", state="complete")
        progress_bar.empty()

    if not all_rows:
        return pd.DataFrame()
        
    combined = pd.concat(all_rows, ignore_index=True)
    combined = processor.categorize_data(combined)
    return combined

# 데이터 준비
df = load_data(24) # 2년치
all_months = sorted(df['year_month'].unique())
display_months = all_months[-12:] # 최근 12개월
df_display = df[df['year_month'].isin(display_months)]

# 서비스 무역 데이터 생성 (기존 방식 유지하되 데이터 부족 시 대응)
df_service = processor.get_service_trade_data(all_months, ecos_client)
df_service_display = df_service[df_service['year_month'].isin(display_months)]

# 헤더 (Reorganized Structure: Logo on Right, Title on One Line)
hdr_left, hdr_right = st.columns([3, 1])
with hdr_left:
    st.title("관세청 ICT 품목별 수출 실적")
with hdr_right:
    try:
        with open("assets/metrix_logo.png", "rb") as _f:
            _logo_b64 = base64.b64encode(_f.read()).decode()
        _logo_html = f'<img src="data:image/png;base64,{_logo_b64}" style="height:36px; object-fit:contain;">'
    except Exception:
        _logo_html = '<span style="font-size:1.2rem;font-weight:700;color:#2D4090;">MetriX</span>'

    st.markdown(f"""
        <div style="display:flex; flex-direction:row; align-items:center; justify-content:flex-end; gap:15px; padding-top:10px;">
            <div style="background: linear-gradient(135deg,#2d4090,#1a2d6d); border-radius:8px; padding:8px 20px; text-align:center;">
                <div style="font-size:0.9rem;font-weight:800;color:white;line-height:1.2;">2026년 ICT통계조사 실사 용역</div>
            </div>
            <div style="display:flex;align-items:center;">{_logo_html}</div>
        </div>
    """, unsafe_allow_html=True)

# 통계 계산 및 유틸리티
def get_item_font_size(name):
    """품목명 길이에 따라 적절한 폰트 사이즈를 반환합니다."""
    length = len(name)
    if length <= 10:
        return "0.9rem"
    elif length <= 14:
        return "0.82rem"
    else:
        return "0.74rem"

last_month = df_display['year_month'].max()
prev_month = sorted(df_display['year_month'].unique())[-2] if len(df_display['year_month'].unique()) > 1 else last_month
yoy_month = (datetime.strptime(last_month, "%Y%m") - timedelta(days=365)).strftime("%Y%m")

curr_df = df_display[df_display['year_month'] == last_month]
prev_df = df_display[df_display['year_month'] == prev_month]
yoy_df = df[df['year_month'] == yoy_month]

growth_mom = processor.calculate_growth(curr_df, prev_df)
growth_yoy = processor.calculate_growth(curr_df, yoy_df)

final_df = growth_mom.copy()
# is_error 정보 병합
if 'is_error' in curr_df.columns:
    final_df = pd.merge(final_df, curr_df[['hs_code', 'is_error']], on='hs_code', how='left')
else:
    final_df['is_error'] = False

final_df['growth_rate_yoy'] = growth_yoy['growth_rate'].values if not growth_yoy.empty else 0

# 탭 구성
tab1, tab2, tab3, tab4 = st.tabs([
    "📌 주요 품목 현황 (관세청)", 
    "📊 품목별 상세 데이터", 
    "📈 월별 수출 추이", 
    "☁️ 서비스 무역 통계 (한국은행)"
])

with tab1:
    st.markdown(f'<div class="section-header">📌 산업군별 주요 품목 현황 ({last_month[:4]}.{last_month[4:]})</div>', unsafe_allow_html=True)
    
    # 필터 영역 (검색창 + 대분류 필터)
    f_col1, f_col2 = st.columns([1, 1])
    with f_col1:
        search_query = st.text_input("🔍 품목 검색 (품목명 또는 HS코드)", placeholder="검색어를 입력하세요.")
    with f_col2:
        categories = list(data_processor.ICT_CATEGORIES.keys())
        selected_categories = st.multiselect("📂 대분류 필터", options=categories, default=categories)
    
    # 필터링 적용
    filtered_df = final_df[final_df['category'].isin(selected_categories)]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered_df = filtered_df[filtered_df['item_name'].str.lower().str.contains(q) | filtered_df['hs_code'].str.contains(q)]
    
    # 총 품목수 표시
    st.markdown(f'<div style="font-size:0.9rem; color:#64748b; margin-bottom:15px; font-weight:600;">✅ 총 {len(filtered_df)}개 품목이 검색되었습니다.</div>', unsafe_allow_html=True)
    
    # 선택된 산업군(카테고리)별로 섹션 생성
    for cat in selected_categories:
        cat_df = filtered_df[filtered_df['category'] == cat]
        
        if cat_df.empty:
            continue
            
        # 헤더 텍스트 사이즈 축소 및 개수 표시
        st.markdown(f"""
            <div style="font-size: 0.85rem; font-weight: 700; color: #1e3a8a; margin-top:20px; margin-bottom:10px; display:flex; align-items:center; gap:8px;">
                <span>📂 {cat}</span>
                <span style="font-size: 0.75rem; font-weight: 400; color: #64748b; background: #f1f5f9; padding: 2px 8px; border-radius: 10px;">{len(cat_df)}개 품목</span>
            </div>
        """, unsafe_allow_html=True)
        
        # 5열 그리드
        COLS = 5
        items = cat_df.sort_values('exp_amount_curr', ascending=False).reset_index(drop=True)
        
        for row_idx in range(0, len(items), COLS):
            row_items = items.iloc[row_idx:row_idx+COLS]
            cols = st.columns(COLS)
            
            for i, (idx, row) in enumerate(row_items.iterrows()):
                mom = row['growth_rate']
                yoy = row['growth_rate_yoy']
                
                with cols[i]:
                    with st.container(border=True):
                        # 내부 컬럼으로 정보와 차트 배치
                        inner_info, inner_chart = st.columns([1.3, 1], gap="small")
                        
                        f_size = "0.8rem" if len(row['item_name']) <= 12 else "0.7rem"
                        is_error = row.get('is_error', False) or row['exp_amount_curr'] == 0
                        
                        with inner_info:
                            st.markdown(f"""
                                <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:2px; margin-top:2px;">
                                    <div style="font-size:{f_size}; font-weight:700; color:#334155; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{row['item_name']}">{row['item_name']}</div>
                                    <div style="font-size:0.6rem; color:#94a3b8;">{row['hs_code'][4:]}</div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if is_error:
                                st.markdown('<div style="font-size:0.75rem; color:#ef4444; font-weight:600; margin-top:5px;">⚠️ 로드 실패</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                    <div style="font-size:1.0rem; font-weight:800; color:#0f172a; margin-bottom:3px;">
                                        {int(row['exp_amount_curr']):,} <span style="font-size:0.65rem; font-weight:400; color:#64748b;">M USD</span>
                                    </div>
                                    <div class="delta-row" style="display:flex; flex-wrap:nowrap; align-items:center; gap:3px;">
                                        <span class="delta-badge {'up' if mom >=0 else 'down'}" style="font-size:0.56rem; padding:0px 2px;">{"▲" if mom >=0 else "▼"}{abs(mom):.1f}%</span>
                                        <span class="delta-badge {'yoy-up' if yoy >=0 else 'yoy-down'}" style="font-size:0.56rem; padding:0px 2px;">{"▲" if yoy >=0 else "▼"}{abs(yoy):.1f}%</span>
                                    </div>
                                """, unsafe_allow_html=True)
                            
                        with inner_chart:
                            if is_error:
                                st.markdown('<div style="height:55px; display:flex; align-items:center; justify-content:center; font-size:0.6rem; color:#94a3b8;">No Data</div>', unsafe_allow_html=True)
                            else:
                                # 2026년 1월부터의 누적 데이터 계산
                                item_history = df[(df['item_name'] == row['item_name']) & (df['year_month'] >= '202601')].sort_values('year_month')
                                # (기존 그래프 로직 생략 없이 그대로 유지)
                                fig = go.Figure()
                                if not item_history.empty and not item_history['exp_amount'].sum() == 0:
                                    item_history['cum_exp'] = item_history['exp_amount'].cumsum()
                                    last_val = item_history['cum_exp'].iloc[-1]
                                    last_month = item_history['year_month'].iloc[-1]
                                    
                                    # 곡선 보강
                                    fig.add_trace(go.Scatter(
                                        x=item_history['year_month'], y=item_history['cum_exp'],
                                        fill='tozeroy', fillcolor='rgba(59,130,246,0.1)',
                                        line=dict(color='#3b82f6', width=2),
                                        mode='lines+markers',
                                        marker=dict(size=4),
                                        hoverinfo='none', showlegend=False
                                    ))
                                    
                                    # 끝점 레이블
                                    fig.add_annotation(
                                        x=last_month, y=last_val,
                                        text=f" {int(last_val):,}M USD",
                                        showarrow=False, xanchor='left', yanchor='middle',
                                        font=dict(size=8, color='#1b3a8a', family="Arial Black")
                                    )
                                
                                fig.update_layout(
                                    title=dict(text="품목 누적", x=0.5, y=0.88, font=dict(size=8, color='#64748b')),
                                    margin=dict(l=2, r=55, t=10, b=2),
                                    height=55,
                                    xaxis=dict(visible=False, categoryorder='array', categoryarray=[f"2026{m:02d}" for m in range(1, 13)]),
                                    yaxis=dict(visible=False),
                                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                                )
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"spark_{row['hs_code']}")

with tab2:
    st.header("📊 품목별 상세 데이터 (관세청)")
    st.dataframe(final_df[['hs_code', 'item_name', 'category', 'exp_amount_prev', 'exp_amount_curr', 'growth_amount', 'growth_rate', 'growth_rate_yoy']], use_container_width=True, hide_index=True)

with tab3:
    st.header("📈 ICT 수출 트렌드")
    cat_ts = df_display.groupby(['year_month', 'category'])['exp_amount'].sum().reset_index()
    fig_line = px.line(cat_ts, x='year_month', y='exp_amount', color='category', markers=True, template="plotly_white")
    st.plotly_chart(fig_line, use_container_width=True)

with tab4:
    st.header("☁️ 서비스 무역(SW·ICT 서비스) 현황 (출처: 한국은행)")
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.plotly_chart(px.line(df_service_display, x='year_month', y='exp_amount', color='service_name', markers=True, template="plotly_white"), use_container_width=True)
    with col_r:
        last_sw = df_service_display[df_service_display['year_month'] == last_month]
        st.plotly_chart(px.pie(last_sw, values='exp_amount', names='service_name', hole=0.4), use_container_width=True)
