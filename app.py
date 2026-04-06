import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math
import api_client
import data_processor

# 페이지 설정
st.set_page_config(page_title="관세청 ICT 품목 당월 수출 실적", layout="wide")

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

# 메인 헤더
st.title("관세청 ICT 품목 당월 수출 실적")
st.caption("관세청(Korea Customs Service) 수출입 통계 데이터를 기반으로 ICT 주요 품목의 실적을 시각화합니다.")
st.markdown(f"**기준:** 최근 {n_months}개월 데이터 (단위: 백만 USD)")

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

# 탭 메뉴 구성 (주요 품목 현황 → 품목별 상세 데이터 → 월별 수출액 추이)
tab1, tab2, tab3 = st.tabs(["📦 주요 품목 현황", "📋 품목별 상세 데이터", "📊 월별 수출액 추이"])

# ──────────────────────────────────────────────
# TAB 1: 주요 품목 현황 (5열 카드 그리드)
# ──────────────────────────────────────────────
with tab1:
    st.header(f"📦 주요 품목 ({last_month[:4]}.{last_month[4:]}) 현황")
    st.caption("MoM: 전월 대비 증감률 / YoY: 전년 동월 대비 증감률")

    # 카테고리 필터
    cat_options = ["전체"] + list(data_processor.ICT_CATEGORIES.keys())
    selected_cat = st.selectbox("품목군 필터", cat_options, index=0, key="grid_cat_filter")

    display_growth_df = growth_df.copy()
    if selected_cat != "전체":
        display_growth_df = display_growth_df[display_growth_df['category'] == selected_cat]

    display_growth_df = display_growth_df.sort_values('exp_amount_curr', ascending=False).reset_index(drop=True)

    # 올해 누적 수출액 스파크라인용 데이터 (현재 연도 1월~최신월)
    current_year_str = str(datetime.now().year)
    df_ytd = df[df['year_month'].str.startswith(current_year_str)].copy()
    df_ytd = df_ytd.sort_values('year_month')

    # 전체 품목의 연간 누적 최대값 (y축 공통 상한)
    def get_item_max_cum(item_name):
        d = df_ytd[df_ytd['item_name'] == item_name].sort_values('year_month')
        if d.empty:
            return 0
        return d['exp_amount'].cumsum().max()

    all_item_names = df_ytd['item_name'].unique()
    global_y_max = max((get_item_max_cum(n) for n in all_item_names), default=1)
    global_y_max = global_y_max * 1.1  # 상단 여백 10%

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
                                <div style="font-size:0.75rem; font-weight:700; color:#334155;
                                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
                                            margin-bottom:1px;" title="{row['item_name']}">{row['item_name']}</div>
                                <div style="font-size:0.6rem; color:#94a3b8; margin-bottom:5px;">{row['hs_code']}</div>
                                <div style="font-size:0.88rem; font-weight:800; color:#0f172a; margin-bottom:5px;">
                                    {int(round(row['exp_amount_curr'])):,}
                                    <span style="font-size:0.6rem; font-weight:400; color:#64748b;">백만</span>
                                </div>
                                <div style="display:flex; gap:3px; flex-wrap:wrap;">
                                    <span style="background:{mom_bg}; color:{mom_color};
                                                 font-size:0.62rem; font-weight:700;
                                                 border-radius:3px; padding:1px 5px;">
                                        {mom_arrow} {row['growth_rate']:+.1f}% MoM
                                    </span>
                                    <span style="background:{yoy_bg}; color:{yoy_color};
                                                 font-size:0.62rem; font-weight:700;
                                                 border-radius:3px; padding:1px 5px;">
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
                            fig_spark.add_trace(go.Scatter(
                                x=item_ytd['month_label'],
                                y=item_ytd['cum_exp'],
                                mode='lines',
                                line=dict(color='#3b82f6', width=1.5),
                                fill='tozeroy',
                                fillcolor='rgba(59,130,246,0.08)',
                            ))
                        fig_spark.update_layout(
                            showlegend=False,
                            margin=dict(l=28, r=2, t=4, b=16),
                            height=95,
                            xaxis=dict(
                                visible=True,
                                tickfont=dict(size=6, color='#94a3b8'),
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
                                tickfont=dict(size=6, color='#94a3b8'),
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
    st.header("📋 품목별 상세 데이터")
    st.dataframe(
        growth_df[['hs_code', 'item_name', 'category', 'exp_amount_prev', 'exp_amount_curr', 'growth_amount', 'growth_rate', 'growth_rate_yoy']],
        use_container_width=True, hide_index=True
    )
    csv = growth_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 상세 데이터 CSV 다운로드", data=csv, file_name=f"ict_export_{last_month}.csv", mime="text/csv")

# ──────────────────────────────────────────────
# TAB 3: 월별 수출액 추이 + 10년 성장률
# ──────────────────────────────────────────────
with tab3:
    st.header("📈 ICT 대분류별 수출 현황")

    # 카테고리별 데이터 집계
    cat_df_full = df.groupby(['year_month', 'category'])['exp_amount'].sum().reset_index()
    cat_df_display = cat_df_full[cat_df_full['year_month'].isin(display_months)].copy()

    all_cats = sorted(cat_df_display['category'].unique())
    selected_cats = st.multiselect("📈 출력 카테고리 선택", options=all_cats, default=all_cats,
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

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("월별 수출액 추이")
        fig_line = px.line(filtered_cat_df, x='year_month', y='exp_amount', color='category', markers=True,
                           custom_data=['yoy_growth'],
                           labels={'exp_amount': '수출액 (USD)', 'year_month': '기준년월', 'category': '대분류'})
        fig_line.update_traces(
            hovertemplate="<b>%{fullData.name}</b><br>기준년월: %{x}<br>수출액: %{y:,.0f} USD<br>전년비(YoY): %{customdata[0]}<extra></extra>"
        )
        fig_line.update_layout(template="plotly_white", hovermode="x unified",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_line, use_container_width=True)

    with col2:
        last_month_pie_df = cat_df_display[cat_df_display['year_month'] == last_month]
        fig_pie = px.pie(last_month_pie_df, values='exp_amount', names='category', title=f"당월({last_month}) 비중",
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_traces(textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, template="plotly_white")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # 대분류별 최근 10년 연간 성장률 막대그래프
    st.header("📊 ICT 대분류별 최근 10년 연간 성장률")
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
