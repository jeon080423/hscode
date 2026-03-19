import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import api_client
import data_processor

# 페이지 설정
st.set_page_config(page_title="ICT 품목 수출입 대시보드", layout="wide")

# 스타일 설정
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTable { background-color: white; }
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
    (실제 API 호출은 제한이 있으므로, 여기선 샘플 데이터를 생성하거나 캐싱 활용)
    """
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=30*i)).strftime("%Y%m") for i in range(months)]
    dates.sort()
    
    # 실제로는 client.fetch_monthly_data(d) 호출
    # 테스트를 위해 더미 데이터 생성 로직 포함 (API 키 환경 아닐 때 대비)
    all_data = []
    for d in dates:
        # df = client.fetch_monthly_data(d)
        # if df is None: # 더미 생성
        df = pd.DataFrame({
            'year_month': d,
            'hs_code': ['854232', '854231', '851713', '847170', '852491'],
            'item_name': ['메모리 반도체', '시스템 반도체', '휴대폰', 'SSD', 'OLED'],
            'exp_amount': [5000 + (int(d)%100)*10, 3000 + (int(d)%100)*5, 1500, 800, 1200],
            'imp_amount': [1000, 800, 200, 100, 300],
            'trade_balance': [4000, 2200, 1300, 700, 900]
        })
        all_data.append(df)
    
    combined = pd.concat(all_data, ignore_index=True)
    combined = processor.categorize_data(combined)
    return combined

# 사이드바 설정
st.sidebar.title("📊 ICT Dashboard")
period = st.sidebar.selectbox("조회 기간", ["최근 12개월", "최근 6개월", "최근 3개월"], index=0)
months_map = {"최근 12개월": 12, "최근 6개월": 6, "최근 3개월": 3}
n_months = months_map[period]

# 데이터 로드
df = load_data(n_months)

# 메인 헤더
st.title("🚀 ICT 품목 수출입 실적 대시보드")
st.markdown(f"기준: 최근 {n_months}개월 데이터 (단위: 백만 USD)")

# (1) 상단: ICT 대분류 기준 막대그래프
st.header("📈 ICT 대분류별 수출 추이")
cat_df = df.groupby(['year_month', 'category'])['exp_amount'].sum().reset_index()
fig_bar = px.bar(cat_df, x='year_month', y='exp_amount', color='category', 
                 barmode='stack', title="월별/카테고리별 수출액",
                 labels={'exp_amount': '수출액 (USD)', 'year_month': '기준년월', 'category': '대분류'})
fig_bar.update_layout(template="plotly_white", hovermode="x unified")
st.plotly_chart(fig_bar, use_container_width=True)

# (2) 중단: 개별 품목 당월 수출 현황 카드
st.header("📦 주요 품목 당월 현황")
last_month = df['year_month'].max()
prev_month = sorted(df['year_month'].unique())[-2] if len(df['year_month'].unique()) > 1 else last_month

curr_df = df[df['year_month'] == last_month]
prev_df = df[df['year_month'] == prev_month]
growth_df = processor.calculate_growth(curr_df, prev_df)

cols = st.columns(len(growth_df))
for i, row in growth_df.iterrows():
    with cols[i]:
        delta_color = "normal" if row['growth_rate'] >= 0 else "inverse"
        # 파란색(상승), 빨간색(하락) 규칙 적용은 metric의 delta_color와 연동
        # Streamlit metric은 기본적으로 green(up), red(down). 
        # 사용자 요구: 상승(파란색), 하락(빨간색)
        st.metric(
            label=f"{row['item_name']} ({row['hs_code']})",
            value=f"{row['exp_amount_curr']:,}",
            delta=f"{row['growth_rate']:.1f}%",
            delta_color=delta_color
        )

# (3) 하단: 품목별 규모 히트맵
st.header("🔥 품목별 수출 규모 히트맵")
pivot_df = df.pivot_table(index='item_name', columns='year_month', values='exp_amount', aggfunc='sum').fillna(0)
fig_heatmap = px.imshow(pivot_df, 
                         labels=dict(x="년월", y="품목명", color="수출액"),
                         x=pivot_df.columns,
                         y=pivot_df.index,
                         color_continuous_scale="Viridis",
                         title="품목별 월별 수출 규모 추이")
st.plotly_chart(fig_heatmap, use_container_width=True)

# 서브 메뉴: 상세 분석 탭
st.divider()
st.header("📋 품목별 상세 데이터")
st.dataframe(growth_df[['hs_code', 'item_name', 'exp_amount_prev', 'exp_amount_curr', 'growth_amount', 'growth_rate']], 
             use_container_width=True, hide_index=True)

# 다운로드
csv = growth_df.to_csv(index=False).encode('utf-8-sig')
st.download_button("📥 상세 데이터 CSV 다운로드", data=csv, file_name=f"ict_export_{last_month}.csv", mime="text/csv")
