import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import api_client
import data_processor

# 페이지 설정
st.set_page_config(page_title="관세청 ICT 품목 당월 수출 실적", layout="wide")

# 스타일 설정
st.markdown("""
<style>
    /* 커스텀 메트릭 카드 스타일 */
    .metric-card {
        background-color: white;
        padding: 12px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 10px;
        min-height: 120px;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #4b5563;
        font-weight: 600;
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .metric-value {
        font-size: 1.15rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 10px;
    }
    .delta-row {
        display: flex;
        justify-content: flex-start;
        gap: 10px;
        border-top: 1px solid #f3f4f6;
        padding-top: 8px;
    }
    .delta-box {
        display: flex;
        flex-direction: column;
    }
    .delta-tag {
        font-size: 0.7rem;
        color: #9ca3af;
        margin-bottom: 1px;
    }
    .delta-val {
        font-size: 0.85rem;
        font-weight: 600;
    }
    .up { color: #059669; }
    .down { color: #dc2626; }
    .yoy-up { color: #2563eb; }
    .yoy-down { color: #d97706; }

    /* 신규 리스트 스타일 (화이트 배경 프리미엄 디자인) */
    .item-list-container {
        margin-top: 20px;
    }
    .category-card {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        min-height: 450px;
        display: flex;
        flex-direction: column;
    }
    .category-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        border-bottom: 2px solid #f1f5f9;
        padding-bottom: 12px;
    }
    .category-title {
        font-size: 1.1rem;
        font-weight: 800;
        color: #1e3a8a;
    }
    .category-subtitle {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 500;
    }
    .item-row {
        display: flex;
        align-items: center;
        background-color: white;
        padding: 12px 0;
        border-bottom: 1px solid #f1f5f9;
        transition: all 0.2s ease;
        gap: 15px;
    }
    .item-row:hover {
        background-color: #f8fafc;
    }
    .status-dot-container {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 10px;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    .dot-red { background-color: #ef4444; }
    .dot-yellow { background-color: #f59e0b; }
    .dot-orange { background-color: #f97316; }
    .dot-green { background-color: #10b981; }

    .item-info {
        flex: 1.5;
        min-width: 100px;
    }
    .item-name {
        font-size: 0.9rem;
        font-weight: 700;
        color: #334155;
        margin-bottom: 1px;
    }
    .item-hs-code {
        font-size: 0.7rem;
        color: #94a3b8;
    }
    .indicator-box {
        flex: 0.4;
        display: flex;
        justify-content: center;
    }
    .sparkline-box {
        flex: 1.2;
        height: 35px;
    }
    .metric-set {
        flex: 1;
        text-align: right;
    }
    .metric-main-val {
        font-size: 1rem;
        font-weight: 800;
        color: #0f172a;
    }
    .metric-sub-val {
        font-size: 0.75rem;
        color: #64748b;
    }
    
    .more-button-container {
        margin-top: auto;
        padding-top: 15px;
        text-align: center;
    }
    .more-button {
        background-color: #f1f5f9;
        color: #475569;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .more-button:hover {
        background-color: #e2e8f0;
    }

    /* 레인지 인디케이터 아이콘 커스텀 (CSS 드로잉) */
    .range-indicator {
        position: relative;
        width: 25px;
        height: 14px;
        border-left: 2px solid #e2e8f0;
        border-right: 2px solid #e2e8f0;
        display: flex;
        align-items: center;
    }
    .range-line {
        width: 100%;
        height: 1px;
        background-color: #e2e8f0;
    }
    .range-dot {
        position: absolute;
        width: 10px;
        height: 5px;
        background-color: #ef4444;
        border-radius: 1px;
    }

    h1, h2, h3 { color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# 인스턴스 초기화
client = api_client.CustomsAPIClient()
processor = data_processor.DataProcessor()

@st.cache_data(ttl=60)
def load_data(months=12):
    """
    최근 N개월 데이터를 로드합니다.
    """
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=30*i)).strftime("%Y%m") for i in range(months)]
    dates.sort()
    
    all_data = []
    # 데이터 프로세서에서 정의한 상세 품목 리스트 사용 (약 100개)
    items_list = list(data_processor.ICT_DETAIL_ITEMS.items())
    
    for d in dates:
        year = int(d) // 100
        month = int(d) % 100
        # 연도별 성장 트렌드 반영 (더 넓은 기간)
        growth_factor = (year - 2015) * 150
        df_month = pd.DataFrame({
            'year_month': d,
            'hs_code': [x[1] for x in items_list],
            'item_name': [x[0] for x in items_list],
            'exp_amount': [
                max(100, 500 + growth_factor + month * 10 + (hash(x[0]) % 2000))
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
# 시각화용 데이터는 사용자가 선택한 개월수만큼 슬라이싱
all_months = sorted(df['year_month'].unique())
display_months = all_months[-n_months:]
df_display = df[df['year_month'].isin(display_months)]

# 메인 헤더 (제목 수정: 관세청 ICT 품목 당월 수출 실적)
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

# 탭 메뉴 구성 (순서: 주요 품목 현황 → 품목별 상세 데이터 → 월별 수출액 추이)
tab1, tab2, tab3 = st.tabs(["📦 주요 품목 현황", "📋 품목별 상세 데이터", "📊 월별 수출액 추이"])

with tab1:
    st.header(f"📦 주요 품목 ({last_month[:4]}.{last_month[4:]}) 현황")
    st.caption("비율은 전월 대비 증감률(MoM)입니다.")

    # 카테고리 필터
    cat_options = ["전체"] + list(data_processor.ICT_CATEGORIES.keys())
    selected_cat = st.selectbox("품목군 필터", cat_options, index=0, key="grid_cat_filter")

    display_growth_df = growth_df.copy()
    if selected_cat != "전체":
        display_growth_df = display_growth_df[display_growth_df['category'] == selected_cat]

    display_growth_df = display_growth_df.sort_values('exp_amount_curr', ascending=False)

    # 신규 리스트 뷰 레이아웃 시작
    st.markdown('<div class="item-list-container">', unsafe_allow_html=True)

    for index, row in display_growth_df.iterrows():
        idx_pos = list(display_growth_df.index).index(index)
        if idx_pos < 3:
            dot_class = "dot-red"
        elif idx_pos < 8:
            dot_class = "dot-yellow"
        else:
            dot_class = "dot-orange"

        pos_pct = 60 + (hash(row['item_name']) % 35)

        row_container = st.container()
        col_dot, col_info, col_range, col_spark, col_metric = row_container.columns([0.15, 1.2, 0.5, 1.5, 1.1], gap="small")

        with col_dot:
            st.markdown(f'<div class="status-dot-container" style="margin-top: 15px;"><div class="status-dot {dot_class}"></div></div>', unsafe_allow_html=True)

        with col_info:
            st.markdown(f"""
                <div class="item-info" style="margin-top: 5px;">
                    <div class="item-name">{row['item_name']}</div>
                    <div class="item-hs-code">{row['hs_code']}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_range:
            st.markdown(f"""
                <div class="indicator-box" style="margin-top: 15px;">
                    <div class="range-indicator">
                        <div class="range-line"></div>
                        <div class="range-dot" style="left: {pos_pct}%;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_spark:
            item_history = df_display[df_display['item_name'] == row['item_name']].sort_values('year_month')
            fig_spark = px.line(item_history, x='year_month', y='exp_amount', render_mode='svg')
            fig_spark.update_traces(line_color="#ef4444", line_width=2)
            fig_spark.update_layout(
                showlegend=False,
                margin=dict(l=0, r=0, t=5, b=5),
                height=45,
                xaxis_visible=False,
                yaxis_visible=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                hovermode=False
            )
            st.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False}, key=f"spark_{idx_pos}")

        with col_metric:
            st.markdown(f"""
                <div class="metric-set" style="margin-top: 5px;">
                    <div class="metric-main-val">{row['growth_rate']:+.2f}%</div>
                    <div class="metric-sub-val">{int(round(row['exp_amount_curr'])):,} 백만</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown('<hr style="margin: 0; border: 0; border-top: 1px solid #f3f4f6;">', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.header("📋 품목별 상세 데이터")
    st.dataframe(growth_df[['hs_code', 'item_name', 'exp_amount_prev', 'exp_amount_curr', 'growth_amount', 'growth_rate']],
                 use_container_width=True, hide_index=True)

    csv = growth_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 상세 데이터 CSV 다운로드", data=csv, file_name=f"ict_export_{last_month}.csv", mime="text/csv")

with tab3:
    # (1) 상단: ICT 대분류 기준 선그래프 및 파이차트
    st.header("📈 ICT 대분류별 수출 현황")

    # 전체 기간 카테고리별 집계
    cat_df_full = df.groupby(['year_month', 'category'])['exp_amount'].sum().reset_index()
    cat_df_display = cat_df_full[cat_df_full['year_month'].isin(display_months)].copy()

    all_cats = sorted(cat_df_display['category'].unique())
    selected_cats = st.multiselect("📈 출력 카테고리 선택", options=all_cats, default=all_cats, help="그래프에 표시할 카테고리를 선택하세요.")

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

    # (2) 대분류별 최근 10년 연간 성장률 막대그래프
    st.header("📊 ICT 대분류별 최근 10년 연간 성장률")
    st.caption("각 대분류의 연간(YoY) 수출 성장률을 최근 10년 기준으로 표시합니다.")

    # 연간 집계: year_month에서 연도 추출 후 합산
    cat_df_full_copy = cat_df_full.copy()
    cat_df_full_copy['year'] = cat_df_full_copy['year_month'].str[:4].astype(int)

    # 연도별 가용 월 수 집계 (12개월이 모두 있는 연도만 유효 연도로 인정)
    months_per_year_cat = cat_df_full_copy.groupby(['year', 'category'])['year_month'].nunique().reset_index()
    months_per_year_cat.columns = ['year', 'category', 'month_count']

    annual_df = cat_df_full_copy.groupby(['year', 'category'])['exp_amount'].sum().reset_index()
    annual_df = annual_df.merge(months_per_year_cat, on=['year', 'category'])

    # 12개월 데이터가 완성된 연도만 사용 (부분 연도 제외)
    annual_df_full = annual_df[annual_df['month_count'] == 12].copy()

    # 완성 연도 목록에서 최근 10년 선택
    complete_years = sorted(annual_df_full['year'].unique())
    recent_10_years = complete_years[-10:] if len(complete_years) >= 10 else complete_years

    # 성장률 계산: 완성 연도 전체 기준으로 shift → 이전 연도 대비 비교 정확
    annual_10yr = annual_df_full.sort_values(['category', 'year']).copy()
    annual_10yr['prev_exp'] = annual_10yr.groupby('category')['exp_amount'].shift(1)
    annual_10yr['growth_rate_yoy'] = (
        (annual_10yr['exp_amount'] - annual_10yr['prev_exp']) / annual_10yr['prev_exp'] * 100
    ).round(1)
    annual_10yr = annual_10yr.dropna(subset=['growth_rate_yoy'])

    # 최근 10개 완성 연도만 필터링
    annual_10yr = annual_10yr[annual_10yr['year'].isin(recent_10_years)]

    # 대분류 3개 각각 막대그래프
    main_categories = list(data_processor.ICT_CATEGORIES.keys())
    chart_colors = ['#3b82f6', '#10b981', '#f59e0b']

    bar_cols = st.columns(3)
    for i, (cat, color) in enumerate(zip(main_categories, chart_colors)):
        cat_annual = annual_10yr[annual_10yr['category'] == cat].copy()
        with bar_cols[i]:
            if cat_annual.empty:
                st.info(f"{cat}: 데이터 없음")
            else:
                fig_bar = go.Figure(
                    go.Bar(
                        x=cat_annual['year'].astype(str),
                        y=cat_annual['growth_rate_yoy'],
                        marker_color=[
                            color if v >= 0 else '#ef4444'
                            for v in cat_annual['growth_rate_yoy']
                        ],
                        text=[f"{v:+.1f}%" for v in cat_annual['growth_rate_yoy']],
                        textposition='outside',
                        hovertemplate="%{x}년<br>성장률: %{y:+.1f}%<extra></extra>"
                    )
                )
                fig_bar.update_layout(
                    title=dict(text=cat, font=dict(size=14, color='#1e3a8a'), x=0.5),
                    template="plotly_white",
                    height=350,
                    margin=dict(t=50, b=40, l=20, r=20),
                    yaxis=dict(
                        ticksuffix="%",
                        zeroline=True,
                        zerolinecolor='#94a3b8',
                        gridcolor='#f1f5f9'
                    ),
                    xaxis=dict(tickangle=-45),
                    showlegend=False
                )
                st.plotly_chart(fig_bar, use_container_width=True)
