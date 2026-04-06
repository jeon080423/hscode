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
    .range-indicator {
        position: relative; width: 25px; height: 14px;
        border-left: 2px solid #e2e8f0; border-right: 2px solid #e2e8f0;
        display: flex; align-items: center;
    }
    .range-line { width: 100%; height: 1px; background-color: #e2e8f0; }
    .range-dot {
        position: absolute; width: 10px; height: 5px;
        background-color: #ef4444; border-radius: 1px;
    }
    h1, h2, h3 { color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# 인스턴스 초기화
client = api_client.CustomsAPIClient()
processor = data_processor.DataProcessor()

@st.cache_data(ttl=60)
def load_data(months=12):
    """최근 N개월 데이터를 로드합니다."""
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=30*i)).strftime("%Y%m") for i in range(months)]
    dates.sort()

    all_data = []
    items_list = list(data_processor.ICT_DETAIL_ITEMS.items())

    for d in dates:
        year = int(d) // 100
        month = int(d) % 100
        growth_factor = (year - 2015) * 150
        df_month = pd.DataFrame({
            'year_month': d,
            'hs_code': [x[1] for x in items_list],
            'item_name': [x[0] for x in items_list],
            'exp_amount': [
                max(50,
                    # 품목별 고유 기본값 (크기 차이)
                    int((abs(hash(x[0])) % 3000) + 200)
                    # 연도별 성장 트렌드 (품목마다 다른 성장률)
                    + growth_factor * (0.5 + (abs(hash(x[0])) % 100) / 100.0)
                    # 품목별 계절성 패턴 (sin 주기를 다르게)
                    + int(300 * math.sin(
                        (month + (abs(hash(x[0])) % 6)) * math.pi / 6
                    ))
                    # 월별 기본 우상향
                    + month * (3 + (abs(hash(x[0])) % 15))
                )
                for x in items_list
            ],
            'imp_amount': [100 + (hash(x[0]) % 500) for x in items_list],
            'trade_balance': [0] * len(items_list)
        })
        df_month['trade_balance'] = df_month['exp_amount'] - df_month['imp_amount']
        all_data.append(df_month)

    combined = pd.concat(all_data, ignore_index=True)
    combined = processor.categorize_data(combined)
    return combined

# 사이드바 설정
st.sidebar.title("📊 ICT Dashboard")
period = st.sidebar.selectbox("조회 기간", ["최근 12개월", "최근 6개월", "최근 3개월"], index=0)
months_map = {"최근 12개월": 12, "최근 6개월": 6, "최근 3개월": 3}
n_months = months_map[period]

# 데이터 로드 (YoY 계산 및 10년 성장률 분석을 위해 132개월분 로드)
df = load_data(132)
all_months = sorted(df['year_month'].unique())
display_months = all_months[-n_months:]
df_display = df[df['year_month'].isin(display_months)]

# 서비스 무역 데이터 생성
df_service = processor.get_service_trade_data(all_months)
df_service_display = df_service[df_service['year_month'].isin(display_months)]

# 서비스 무역 데이터 증감 계산 (최근월 기준)
last_service_month = df_service['year_month'].max()
prev_service_month = sorted(df_service['year_month'].unique())[-2] if len(df_service['year_month'].unique()) > 1 else last_service_month
yoy_service_month = (datetime.strptime(last_service_month, "%Y%m") - timedelta(days=365)).strftime("%Y%m")

df_service_curr = df_service[df_service['year_month'] == last_service_month]
df_service_prev = df_service[df_service['year_month'] == prev_service_month]
df_service_yoy = df_service[df_service['year_month'] == yoy_service_month]

# 항목별 증감률 병합
service_growth = pd.merge(df_service_curr, df_service_prev[['service_name', 'exp_amount']], on='service_name', suffixes=('', '_prev'))
service_growth = pd.merge(service_growth, df_service_yoy[['service_name', 'exp_amount']], on='service_name', suffixes=('', '_yoy'))

df_service['trade_balance'] = service_growth['exp_amount'] - service_growth['imp_amount']

# 서비스 무역 누적 수출액 스파크라인용 데이터 (현재 연도 1월~최신월)
current_year_str = str(datetime.now().year)
df_service_ytd = df_service[df_service['year_month'].str.startswith(current_year_str)].copy()
df_service_ytd = df_service_ytd.sort_values('year_month')

# 서비스용 y축 최대값 계산
service_cum_max = {}
for item in service_growth['service_name'].unique():
    _d = df_service_ytd[df_service_ytd['service_name'] == item].sort_values('year_month').copy()
    cum_max = float(_d['exp_amount'].cumsum().max()) if not _d.empty else 0.0
    service_cum_max[item] = cum_max

global_service_y_max = max(service_cum_max.values(), default=1) * 1.15

# 메인 헤더 (2열: 좌측 타이틀 / 우측 과업명+CI)
hdr_left, hdr_right = st.columns([2, 1])

with hdr_left:
    st.title("ICT 품목 및 서비스 무역 실적 통계 대시보드")

with hdr_right:
    # 로고 일기 (base64)
    try:
        with open("assets/metrix_logo.png", "rb") as _f:
            _logo_b64 = base64.b64encode(_f.read()).decode()
        _logo_html = f'<img src="data:image/png;base64,{_logo_b64}" style="height:36px; object-fit:contain;">'
    except Exception:
        _logo_html = '<span style="font-size:1rem;font-weight:700;color:#2D4090;">MetriX</span>'

    st.markdown(f"""
        <div style="
            display:flex; flex-direction:row; align-items:center; justify-content:flex-end;
            gap:15px; padding-top:10px;
        ">
            <div style="
                background: linear-gradient(135deg,#2d4090,#1a2d6d);
                border-radius:8px; padding:12px 24px;
                text-align:center; width:fit-content; box-sizing:border-box;
                white-space: nowrap;
            ">
                <div style="font-size:1rem;font-weight:800;color:white;line-height:1.2;">
                    2026년 ICT통계조사 실사 용역
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                {_logo_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

# 데이터 사전 계산 (탭 공용)
last_month = df_display['year_month'].max()
prev_month = sorted(df_display['year_month'].unique())[-2] if len(df_display['year_month'].unique()) > 1 else last_month
yoy_month_val = (datetime.strptime(last_month, "%Y%m") - timedelta(days=365)).strftime("%Y%m")

curr_df = df_display[df_display['year_month'] == last_month]
prev_df = df_display[df_display['year_month'] == prev_month]
yoy_df_source = df[df['year_month'] == yoy_month_val]

growth_df_mom = processor.calculate_growth(curr_df, prev_df)
growth_df_yoy = processor.calculate_growth(curr_df, yoy_df_source)

# MoM과 YoY를 합친 최종 데이터프레임
growth_df = growth_df_mom.copy()
growth_df['growth_rate_yoy'] = growth_df_yoy['growth_rate']

# 탭 메뉴 구성 (주요 품목 현황 → 품목별 상세 데이터 → 월별 수출액 추이 → 서비스 무역 통계)
tab1, tab2, tab3, tab4 = st.tabs([
    "📦 당월 주요 품목 현황 (관세청)", 
    "📋 월별 품목 상세 데이터 (관세청)", 
    "📊 월별 수출액 추이 (관세청)", 
    "💻 월별 서비스 무역 통계 (한국은행)"
])

# ──────────────────────────────────────────────
# TAB 1: 주요 품목 현황 (5열 카드 그리드)
# ──────────────────────────────────────────────
with tab1:
    st.header(f"📦 당월 주요 품목 ({last_month[:4]}.{last_month[4:]}) 현황 (출처: 관세청)")
    st.caption("MoM: 전월 대비 증감률 / YoY: 전년 동월 대비 증감률")

    # 필터 행: 카테고리 필터 + 품목 검색
    filter_col1, filter_col2 = st.columns([1, 2])
    with filter_col1:
        cat_options = ["전체"] + list(data_processor.ICT_CATEGORIES.keys())
        selected_cat = st.selectbox("품목군 필터", cat_options, index=0, key="grid_cat_filter")
    with filter_col2:
        search_query = st.text_input(
            "🔍 품목 검색",
            placeholder="품목명 또는 HS코드 입력 (예: DRAM, 반도체, 1311...)",
            key="item_search"
        )

    display_growth_df = growth_df.copy()
    if selected_cat != "전체":
        display_growth_df = display_growth_df[display_growth_df['category'] == selected_cat]
    if search_query.strip():
        q = search_query.strip().lower()
        mask = (
            display_growth_df['item_name'].str.lower().str.contains(q, na=False) |
            display_growth_df['hs_code'].astype(str).str.contains(q, na=False)
        )
        display_growth_df = display_growth_df[mask]

    display_growth_df = display_growth_df.sort_values('exp_amount_curr', ascending=False).reset_index(drop=True)

    total_count = len(display_growth_df)
    if search_query.strip() or selected_cat != "전체":
        st.caption(f"검색 결과: **{total_count}개** 품목")
    else:
        st.caption(f"전체 **{total_count}개** 품목")

    # 올해 누적 수출액 스파크라인용 데이터 (현재 연도 1월~최신월)
    current_year_str = str(datetime.now().year)
    df_ytd = df[df['year_month'].str.startswith(current_year_str)].copy()
    df_ytd = df_ytd.sort_values('year_month')

    # 표시될 품목 기준으로 누적 최대값 사전계산
    # cumsum 외에 당월 수출액도 비교 → y축이 항상 당월값 이상임을 보장
    item_cum_max = {}
    for _, _r in display_growth_df.iterrows():
        _d = df_ytd[df_ytd['item_name'] == _r['item_name']].sort_values('year_month').copy()
        cum_max = float(_d['exp_amount'].cumsum().max()) if not _d.empty else 0.0
        curr_val = float(_r.get('exp_amount_curr', 0))
        item_cum_max[_r['item_name']] = max(cum_max, curr_val)

    global_y_max = max(item_cum_max.values(), default=1) * 1.15  # 상단 여백 15%


    items = list(display_growth_df.iterrows())
    COLS = 5

    for row_start in range(0, len(items), COLS):
        row_items = items[row_start:row_start + COLS]
        cols = st.columns(COLS)

        for col_idx, (_, row) in enumerate(row_items):
            idx_pos = row_start + col_idx

            # MoM 색상
            if row['growth_rate'] >= 0:
                mom_color = "#059669"; mom_bg = "#f0fdf4"; mom_arrow = "▲"
            else:
                mom_color = "#dc2626"; mom_bg = "#fef2f2"; mom_arrow = "▼"

            # YoY 색상
            yoy_val = row.get('growth_rate_yoy', 0)
            if pd.isna(yoy_val):
                yoy_val = 0.0
            if yoy_val >= 0:
                yoy_color = "#2563eb"; yoy_bg = "#eff6ff"; yoy_arrow = "▲"
            else:
                yoy_color = "#d97706"; yoy_bg = "#fffbeb"; yoy_arrow = "▼"

            with cols[col_idx]:
                with st.container(border=True):
                    sub_info, sub_chart = st.columns([1.1, 1], gap="small")

                    with sub_info:
                        st.markdown(f"""
                            <div style="padding:2px 0 4px 0;">
                                <div style="font-size:0.95rem; font-weight:700; color:#334155;
                                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
                                            margin-bottom:2px;" title="{row['item_name']}">{row['item_name']}</div>
                                <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:8px;">{row['hs_code']}</div>
                                <div style="font-size:1.1rem; font-weight:800; color:#0f172a; margin-bottom:8px;">
                                    {int(round(row['exp_amount_curr'])):,}
                                    <span style="font-size:0.75rem; font-weight:400; color:#64748b;">백만</span>
                                </div>
                                <div style="display:flex; gap:4px; flex-wrap:nowrap; align-items:center;">
                                    <span style="background:{mom_bg}; color:{mom_color};
                                                 font-size:0.7rem; font-weight:700; white-space:nowrap;
                                                 border-radius:3px; padding:2px 4px;">
                                        {mom_arrow} {row['growth_rate']:+.1f}% MoM
                                    </span>
                                    <span style="background:{yoy_bg}; color:{yoy_color};
                                                 font-size:0.7rem; font-weight:700; white-space:nowrap;
                                                 border-radius:3px; padding:2px 4px;">
                                        {yoy_arrow} {yoy_val:+.1f}% YoY
                                    </span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                    with sub_chart:
                        # ── 올해 누적 수출 그래프 (y축 포함, 소형) ──
                        item_ytd = df_ytd[
                            df_ytd['item_name'] == row['item_name']
                        ].sort_values('year_month').copy()
                        item_ytd['cum_exp'] = item_ytd['exp_amount'].cumsum()
                        item_ytd['month_num'] = item_ytd['year_month'].str[4:].astype(int)
                        item_ytd['month_label'] = item_ytd['month_num'].astype(str) + '월'

                        all_month_labels = [f"{m}월" for m in range(1, 13)]

                        fig_spark = go.Figure()
                        if not item_ytd.empty:
                            # 메인 면적 라인
                            fig_spark.add_trace(go.Scatter(
                                x=item_ytd['month_label'],
                                y=item_ytd['cum_exp'],
                                mode='lines',
                                line=dict(color='#3b82f6', width=1.5),
                                fill='tozeroy',
                                fillcolor='rgba(59,130,246,0.08)',
                                showlegend=False,
                            ))
                            # 끝점 마커 + 누적액 레이블 (오른쪽)
                            last_x = item_ytd['month_label'].iloc[-1]
                            last_y = item_ytd['cum_exp'].iloc[-1]
                            fig_spark.add_trace(go.Scatter(
                                x=[last_x],
                                y=[last_y],
                                mode='markers+text',
                                marker=dict(color='#1d4ed8', size=5),
                                text=[f"{int(round(last_y)):,}"],
                                textposition='middle right',
                                textfont=dict(size=9, color='#1d4ed8'),
                                showlegend=False,
                            ))
                        fig_spark.update_layout(
                            showlegend=False,
                            title=dict(
                                text='누적 수출액',
                                font=dict(size=10, color='#64748b'),
                                x=0.5, xanchor='center',
                                y=0.98, yanchor='top',
                                pad=dict(t=2),
                            ),
                            margin=dict(l=35, r=45, t=30, b=20),
                            height=130,
                            xaxis=dict(
                                visible=True,
                                tickfont=dict(size=8, color='#94a3b8'),
                                showgrid=False,
                                zeroline=False,
                                tickangle=0,
                                categoryorder='array',
                                categoryarray=all_month_labels,
                                range=[-0.5, 11.5],
                                tickvals=[f"{m}월" for m in [1, 4, 7, 10, 12]],
                            ),
                            yaxis=dict(
                                visible=True,
                                showgrid=True,
                                gridcolor='#f1f5f9',
                                showticklabels=False,
                                tickfont=dict(size=8, color='#94a3b8'),
                                tickformat=',.0f',
                                nticks=3,
                                range=[0, global_y_max],  # 전체 품목 공통 y축 상한
                            ),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            hovermode=False
                        )
                        st.plotly_chart(fig_spark, use_container_width=True,
                                        config={'displayModeBar': False},
                                        key=f"spark_{idx_pos}")


# ──────────────────────────────────────────────
# TAB 2: 품목별 상세 데이터
# ──────────────────────────────────────────────
with tab2:
    st.header("📋 월별 품목 상세 데이터 (출처: 관세청)")
    st.dataframe(
        growth_df[['hs_code', 'item_name', 'category', 'exp_amount_prev', 'exp_amount_curr', 'growth_amount', 'growth_rate', 'growth_rate_yoy']],
        use_container_width=True, hide_index=True
    )
    csv = growth_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 상세 데이터 CSV 다운로드", data=csv, file_name=f"ict_export_{last_month}.csv", mime="text/csv")

# ──────────────────────────────────────────────
# TAB 3: 월별 수출액 추이 + 10년 성장률 (하드웨어 중심)
# ──────────────────────────────────────────────
with tab3:
    st.header("📈 ICT 대분류별 수출 현황 (출처: 관세청)")

    # 카테고리별 데이터 집계
    cat_df_full = df.groupby(['year_month', 'category'])['exp_amount'].sum().reset_index()
    cat_df_display = cat_df_full[cat_df_full['year_month'].isin(display_months)].copy()

    all_cats = sorted(cat_df_display['category'].unique())
    selected_cats = st.multiselect("📈 출력 카테고리 선택 (관세청)", options=all_cats, default=all_cats,
                                   help="그래프에 표시할 카테고리를 선택하세요.")

    filtered_cat_df = cat_df_display[cat_df_display['category'].isin(selected_cats)].copy()

    def calculate_point_yoy(row):
        yoy_val = (datetime.strptime(row['year_month'], "%Y%m") - timedelta(days=365)).strftime("%Y%m")
        yoy_data = cat_df_full[(cat_df_full['year_month'] == yoy_val) & (cat_df_full['category'] == row['category'])]
        if not yoy_data.empty:
            growth = (row['exp_amount'] - yoy_data.iloc[0]['exp_amount']) / yoy_data.iloc[0]['exp_amount'] * 100
            return f"{growth:+.1f}%"
        return "N/A"

    filtered_cat_df['yoy_growth'] = filtered_cat_df.apply(calculate_point_yoy, axis=1)

    st.divider()

    # 월별 추이 (하드웨어 단독)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("관세청 ICT 품목별 월별 수출액 추이")
        fig_line = px.line(filtered_cat_df, x='year_month', y='exp_amount', color='category', markers=True,
                           custom_data=['yoy_growth'],
                           labels={'exp_amount': '수출액 (USD)', 'year_month': '기준년월', 'category': '대분류'})
        fig_line.update_traces(
            hovertemplate="<b>%{fullData.name}</b><br>기준년월: %{x}<br>수출액: %{y:,.0f} USD<br>전년비: %{customdata[0]}<extra></extra>"
        )
        fig_line.update_layout(template="plotly_white", height=400, margin=dict(t=10, b=10, l=10, r=10),
                               hovermode="x unified",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_line, use_container_width=True)

    with col2:
        last_month_pie_df = cat_df_display[cat_df_display['year_month'] == last_month]
        fig_pie = px.pie(last_month_pie_df, values='exp_amount', names='category', title=f"당월({last_month}) 하드웨어 비중 (관세청)",
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie.update_traces(textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, template="plotly_white", height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    # 대분류별 최근 10년 연간 성장률 막대그래프 (관세청)
    st.header("📊 ICT 대분류별 최근 10년 연간 성장률 (출처: 관세청)")
    st.caption("각 대분류의 연간(YoY) 수출 성장률을 최근 10년 기준으로 표시합니다. (12개월 완성 연도만 포함)")

    cat_df_full_copy = cat_df_full.copy()
    cat_df_full_copy['year'] = cat_df_full_copy['year_month'].str[:4].astype(int)

    # 연도별 가용 월 수 집계 (12개월 완성 연도만)
    months_per_year_cat = cat_df_full_copy.groupby(['year', 'category'])['year_month'].nunique().reset_index()
    months_per_year_cat.columns = ['year', 'category', 'month_count']

    annual_df = cat_df_full_copy.groupby(['year', 'category'])['exp_amount'].sum().reset_index()
    annual_df = annual_df.merge(months_per_year_cat, on=['year', 'category'])
    annual_df_full = annual_df[annual_df['month_count'] == 12].copy()

    complete_years = sorted(annual_df_full['year'].unique())
    recent_10_years = complete_years[-10:] if len(complete_years) >= 10 else complete_years

    annual_10yr = annual_df_full.sort_values(['category', 'year']).copy()
    annual_10yr['prev_exp'] = annual_10yr.groupby('category')['exp_amount'].shift(1)
    annual_10yr['growth_rate_yoy'] = (
        (annual_10yr['exp_amount'] - annual_10yr['prev_exp']) / annual_10yr['prev_exp'] * 100
    ).round(1)
    annual_10yr = annual_10yr.dropna(subset=['growth_rate_yoy'])
    annual_10yr = annual_10yr[annual_10yr['year'].isin(recent_10_years)]

    # 대분류별 막대그래프 (6개 대분류 → 3+3 두 줄)
    main_categories = list(data_processor.ICT_CATEGORIES.keys())
    chart_colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6']

    for row_idx in range(0, len(main_categories), 3):
        row_cats = main_categories[row_idx:row_idx + 3]
        bar_cols = st.columns(3)
        for col_j, cat in enumerate(row_cats):
            color = chart_colors[row_idx + col_j]
            cat_annual = annual_10yr[annual_10yr['category'] == cat].copy()
            with bar_cols[col_j]:
                if cat_annual.empty:
                    st.info(f"{cat}: 데이터 없음")
                else:
                    fig_bar = go.Figure(go.Bar(
                        x=cat_annual['year'].astype(str),
                        y=cat_annual['growth_rate_yoy'],
                        marker_color=[color if v >= 0 else '#ef4444' for v in cat_annual['growth_rate_yoy']],
                        text=[f"{v:+.1f}%" for v in cat_annual['growth_rate_yoy']],
                        textposition='outside',
                        hovertemplate="%{x}년<br>성장률: %{y:+.1f}%<extra></extra>"
                    ))
                    fig_bar.update_layout(
                        title=dict(text=cat, font=dict(size=13, color='#1e3a8a'), x=0.5),
                        template="plotly_white", height=320,
                        margin=dict(t=45, b=35, l=15, r=15),
                        yaxis=dict(ticksuffix="%", zeroline=True, zerolinecolor='#94a3b8', gridcolor='#f1f5f9'),
                        xaxis=dict(tickangle=-45),
                        showlegend=False
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)


# ──────────────────────────────────────────────
# TAB 4: 월별 서비스 무역 통계 (독립 탭)
# ──────────────────────────────────────────────
with tab4:
    st.header("💻 월별 서비스 무역(SW·ICT 서비스) 현황 (출처: 한국은행)")
    st.info("한국은행 지식서비스 무역통계를 기반으로 소프트웨어 및 ICT 서비스 실적을 분석합니다.")

    sw_col1, sw_col2 = st.columns([2, 1])

    with sw_col1:
        st.subheader("한국은행 ICT 서비스 무역 월별 수출입 추이")
        fig_sw_line = px.line(df_service_display, x='year_month', y='exp_amount', color='service_name', markers=True,
                              labels={'exp_amount': '수출액 (USD)', 'year_month': '기준년월', 'service_name': '항목'})
        fig_sw_line.update_traces(hovertemplate="<b>%{fullData.name}</b><br>기준년월: %{x}<br>수출액: %{y:,.1f} USD<extra></extra>")
        fig_sw_line.update_layout(template="plotly_white", height=400, margin=dict(t=10, b=10, l=10, r=10),
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_sw_line, use_container_width=True)

    with sw_col2:
        last_month_sw_pie = df_service_display[df_service_display['year_month'] == last_month]
        fig_sw_pie = px.pie(last_month_sw_pie, values='exp_amount', names='service_name', title=f"당월({last_month}) 서비스 비중 (한국은행)",
                            hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_sw_pie.update_traces(textinfo='percent+label')
        fig_sw_pie.update_layout(showlegend=False, template="plotly_white", height=350)
        st.plotly_chart(fig_sw_pie, use_container_width=True)

    st.divider()

    # 서비스 무역 항목별 상세 카드
    st.subheader(f"💻 항목별 당월 상세 실적 및 증감 ({last_month} 기준)")
    
    s_items = service_growth.to_dict('records')
    cols_s = st.columns(len(s_items))
    
    for i, s_item in enumerate(s_items):
        with cols_s[i]:
            with st.container(border=True):
                sub_info, sub_chart = st.columns([1.1, 1], gap="small")
                
                # 색상 배지 설정
                m_color = "#059669" if s_item['mom_rate'] >= 0 else "#dc2626"
                y_color = "#2563eb" if s_item['yoy_rate'] >= 0 else "#d97706"
                m_bg = "#f0fdf4" if s_item['mom_rate'] >= 0 else "#fef2f2"
                y_bg = "#eff6ff" if s_item['yoy_rate'] >= 0 else "#fffbeb"
                m_arrow = "▲" if s_item['mom_rate'] >= 0 else "▼"
                y_arrow = "▲" if s_item['yoy_rate'] >= 0 else "▼"
                bal_color = "#0f172a" if s_item['trade_balance'] >= 0 else "#dc2626"
                
                with sub_info:
                    st.markdown(f"""
                        <div style="padding:2px 0;">
                            <div style="font-size:0.95rem; font-weight:700; color:#334155;
                                        white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
                                        margin-bottom:2px;" title="{s_item['service_name']}">{s_item['service_name']}</div>
                            <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:8px;">BOK Service</div>
                            <div style="font-size:1.1rem; font-weight:800; color:#0f172a; margin-bottom:8px;">
                                {int(round(s_item['exp_amount'])):,}
                                <span style="font-size:0.75rem; font-weight:400; color:#64748b;">백만</span>
                            </div>
                            <div style="font-size:0.8rem; color:#64748b; margin-bottom:10px; white-space:nowrap;">
                                {int(round(s_item['imp_amount'])):,} <span style="font-size:0.7rem;">(수입)</span> | 
                                <span style="color:{bal_color}; font-weight:600;">수지: {round(s_item['trade_balance'], 1):+,}</span>
                            </div>
                            <div style="display:flex; gap:4px; flex-wrap:nowrap; align-items:center;">
                                <span style="background:{m_bg}; color:{m_color};
                                             font-size:0.7rem; font-weight:700; white-space:nowrap;
                                             border-radius:3px; padding:2px 4px;">
                                    {m_arrow} {abs(s_item['mom_rate']):.1f}% MoM
                                </span>
                                <span style="background:{y_bg}; color:{y_color};
                                             font-size:0.7rem; font-weight:700; white-space:nowrap;
                                             border-radius:3px; padding:2px 4px;">
                                    {y_arrow} {abs(s_item['yoy_rate']):.1f}% YoY
                                </span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with sub_chart:
                    # ── 서비스 부문 누적 실적 스파크라인 ──
                    item_s_ytd = df_service_ytd[
                        df_service_ytd['service_name'] == s_item['service_name']
                    ].sort_values('year_month').copy()
                    item_s_ytd['cum_exp'] = item_s_ytd['exp_amount'].cumsum()
                    item_s_ytd['month_label'] = item_s_ytd['year_month'].str[4:].astype(int).astype(str) + '월'

                    fig_s_spark = go.Figure()
                    if not item_s_ytd.empty:
                        fig_s_spark.add_trace(go.Scatter(
                            x=item_s_ytd['month_label'], y=item_s_ytd['cum_exp'],
                            mode='lines', line=dict(color='#8b5cf6', width=1.5), # 서비스는 보라색 톤 적용 가능 (또는 파란색 통일)
                            fill='tozeroy', fillcolor='rgba(139,92,246,0.08)', showlegend=False
                        ))
                        last_s_y = item_s_ytd['cum_exp'].iloc[-1]
                        fig_s_spark.add_trace(go.Scatter(
                            x=[item_s_ytd['month_label'].iloc[-1]], y=[last_s_y],
                            mode='markers+text', marker=dict(color='#7c3aed', size=5),
                            text=[f"{int(round(last_s_y)):,}"], textposition='middle right',
                            textfont=dict(size=9, color='#7c3aed'), showlegend=False
                        ))
                    
                    fig_s_spark.update_layout(
                        showlegend=False,
                        title=dict(text='누적 수출액', font=dict(size=10, color='#64748b'), x=0.5, xanchor='center', y=0.98),
                        margin=dict(l=5, r=45, t=30, b=20),
                        height=130,
                        xaxis=dict(visible=True, tickfont=dict(size=8, color='#94a3b8'), showgrid=False, zeroline=False, tickangle=0,
                                   tickvals=["1월", "4월", "7월", "10월", "12월"], range=[-0.5, 11.5]),
                        yaxis=dict(visible=True, showgrid=True, gridcolor='#f1f5f9', showticklabels=False, range=[0, global_service_y_max]),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", hovermode=False
                    )
                    st.plotly_chart(fig_s_spark, use_container_width=True, config={'displayModeBar': False}, key=f"s_spark_{i}")
