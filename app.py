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
    .main { background-color: #f8f9fa; }
    /* 메트릭 박스 조밀하게 설정 */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 5px 10px;
        border-radius: 5px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
    }
    div[data-testid="stMetricLabel"] > div {
        font-size: 0.8rem !important;
        color: #4b5563 !important;
    }
    div[data-testid="stMetricValue"] > div {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricDelta"] > div {
        font-size: 0.8rem !important;
    }
    h1, h2, h3 { color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# 인스턴스 초기화
client = api_client.CustomsAPIClient()
processor = data_processor.DataProcessor()

@st.cache_data(ttl=3600)
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
        # 데모를 위한 고도화된 더미 데이터 생성
        df_month = pd.DataFrame({
            'year_month': d,
            'hs_code': [x[1] for x in items_list],
            'item_name': [x[0] for x in items_list],
            'exp_amount': [
                # 연도별 성장성을 부여하기 위해 연도(d//100) 반영
                (5000 if '반도체' in x[0] else 500) + (int(d)//100 - 2024)*200 + (int(d)%100)*10 + (hash(x[0])%1000)
                for x in items_list
            ],
            'imp_amount': [100 + (hash(x[0])%500) for x in items_list],
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

# 데이터 로드 (YoY 계산을 위해 상시 24개월분 로드 시도)
df = load_data(24)
# 시각화용 데이터는 사용자가 선택한 개월수만큼 슬라이싱
all_months = sorted(df['year_month'].unique())
display_months = all_months[-n_months:]
df_display = df[df['year_month'].isin(display_months)]

# 메인 헤더 (제목 수정: 관세청 ICT 품목 당월 수출 실적)
st.title("관세청 ICT 품목 당월 수출 실적")
st.caption("관세청(Korea Customs Service) 수출입 통계 데이터를 기반으로 ICT 주요 품목의 실적을 시각화합니다.")
st.markdown(f"**기준:** 최근 {n_months}개월 데이터 (단위: 백만 USD)")

# (1) 상단: ICT 대분류 기준 선그래프 및 파이차트
st.header("📈 ICT 대분류별 수출 현황")

# 데이터 가공
cat_df_full = df.groupby(['year_month', 'category'])['exp_amount'].sum().reset_index()
cat_df_display = cat_df_full[cat_df_full['year_month'].isin(display_months)].copy()

# YoY 계산 로직
last_month_val = cat_df_display['year_month'].max()
lm_date = datetime.strptime(last_month_val, "%Y%m")
yoy_month_val = (lm_date - timedelta(days=365)).strftime("%Y%m")

def get_yoy_label(row):
    if row['year_month'] != last_month_val:
        return ""
    yoy_data = cat_df_full[(cat_df_full['year_month'] == yoy_month_val) & 
                           (cat_df_full['category'] == row['category'])]
    curr_amt = row['exp_amount']
    if not yoy_data.empty:
        yoy_amt = yoy_data.iloc[0]['exp_amount']
        growth = (curr_amt - yoy_amt) / yoy_amt * 100
        return f"{curr_amt:,}\n({growth:+.1f}%)" 
    return f"{curr_amt:,}"

cat_df_display['text_label'] = cat_df_display.apply(get_yoy_label, axis=1)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("월별 수출액 추이")
    st.caption("( ) 내 비율은 전년 동월 대비 증감률(YoY)입니다.")
    fig_line = px.line(cat_df_display, x='year_month', y='exp_amount', color='category', 
                       markers=True, text='text_label',
                       labels={'exp_amount': '수출액 (USD)', 'year_month': '기준년월', 'category': '대분류'})
    fig_line.update_traces(textposition="top center")
    fig_line.update_layout(template="plotly_white", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_line, use_container_width=True)

with col2:
    # 당월 기준 파이차트 생성
    last_month_pie_df = cat_df_display[cat_df_display['year_month'] == last_month_val]
    fig_pie = px.pie(last_month_pie_df, values='exp_amount', names='category',
                     title=f"당월({last_month_val}) 비중",
                     hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_traces(textinfo='percent+label')
    fig_pie.update_layout(showlegend=False, template="plotly_white")
    st.plotly_chart(fig_pie, use_container_width=True)

# (2) 중단: 개별 품목 당월 현황 (수출 상위 100개)
st.header("📦 주요 품목 당월 현황")
st.caption("비율은 전월 대비 증감률(MoM)입니다.")
last_month = df_display['year_month'].max()
prev_month = sorted(df_display['year_month'].unique())[-2] if len(df_display['year_month'].unique()) > 1 else last_month

curr_df = df_display[df_display['year_month'] == last_month]
prev_df = df_display[df_display['year_month'] == prev_month]
growth_df = processor.calculate_growth(curr_df, prev_df)

# 수출액 기준 내림차순 정렬 및 상위 100개 선택
growth_df = growth_df.sort_values('exp_amount_curr', ascending=False).head(100)

cols_per_row = 5
cols = st.columns(cols_per_row)
for i, (index, row) in enumerate(growth_df.iterrows()):
    with cols[i % cols_per_row]:
        st.metric(
            label=f"{row['item_name']}",
            value=f"{row['exp_amount_curr']:,}",
            delta=f"{row['growth_rate']:.1f}%",
        )

# (3) 하단: 품목별 누적 수출 그래프
st.header("2026년 기준 품목별 누적 수출 추이")
# 2026년 데이터 필터링
df_2026 = df_display[df_display['year_month'].str.startswith('2026')]
if df_2026.empty:
    df_2026 = df_display

# 품목별 누적합 계산
df_2026 = df_2026.sort_values(['item_name', 'year_month'])
df_2026['cumulative_exp'] = df_2026.groupby('item_name')['exp_amount'].cumsum()

fig_cum = px.area(df_2026, x='year_month', y='cumulative_exp', color='item_name',
                  title="2026년 품목별 누적 수출 실적 (Stacked Area)",
                  labels={'cumulative_exp': '누적 수출액 (USD)', 'year_month': '기준년월', 'item_name': '품목명'})
fig_cum.update_layout(template="plotly_white")
st.plotly_chart(fig_cum, use_container_width=True)

# 서브 메뉴: 상세 분석 탭
st.divider()
st.header("📋 품목별 상세 데이터")
st.dataframe(growth_df[['hs_code', 'item_name', 'exp_amount_prev', 'exp_amount_curr', 'growth_amount', 'growth_rate']], 
             use_container_width=True, hide_index=True)

# 다운로드
csv = growth_df.to_csv(index=False).encode('utf-8-sig')
st.download_button("📥 상세 데이터 CSV 다운로드", data=csv, file_name=f"ict_export_{last_month}.csv", mime="text/csv")
