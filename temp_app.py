import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math
import base64
import api_client
import data_processor

# ?섏씠吏 ?ㅼ젙
st.set_page_config(page_title="愿?몄껌 ICT ?덈ぉ ?뱀썡 ?섏텧 ?ㅼ쟻", layout="wide")

# ?ㅽ????ㅼ젙
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

# ?몄뒪?댁뒪 珥덇린??client = api_client.CustomsAPIClient()
processor = data_processor.DataProcessor()

@st.cache_data(ttl=60)
def load_data(months=12):
    """理쒓렐 N媛쒖썡 ?곗씠?곕? 濡쒕뱶?⑸땲??"""
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
                    # ?덈ぉ蹂?怨좎쑀 湲곕낯媛?(?ш린 李⑥씠)
                    int((abs(hash(x[0])) % 3000) + 200)
                    # ?곕룄蹂??깆옣 ?몃젋??(?덈ぉ留덈떎 ?ㅻⅨ ?깆옣瑜?
                    + growth_factor * (0.5 + (abs(hash(x[0])) % 100) / 100.0)
                    # ?덈ぉ蹂?怨꾩젅???⑦꽩 (sin 二쇨린瑜??ㅻⅤ寃?
                    + int(300 * math.sin(
                        (month + (abs(hash(x[0])) % 6)) * math.pi / 6
                    ))
                    # ?붾퀎 湲곕낯 ?곗긽??                    + month * (3 + (abs(hash(x[0])) % 15))
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

# ?ъ씠?쒕컮 ?ㅼ젙
st.sidebar.title("?뱤 ICT Dashboard")
period = st.sidebar.selectbox("議고쉶 湲곌컙", ["理쒓렐 12媛쒖썡", "理쒓렐 6媛쒖썡", "理쒓렐 3媛쒖썡"], index=0)
months_map = {"理쒓렐 12媛쒖썡": 12, "理쒓렐 6媛쒖썡": 6, "理쒓렐 3媛쒖썡": 3}
n_months = months_map[period]

# ?곗씠??濡쒕뱶 (YoY 怨꾩궛 諛?10???깆옣瑜?遺꾩꽍???꾪빐 132媛쒖썡遺?濡쒕뱶)
df = load_data(132)
all_months = sorted(df['year_month'].unique())
display_months = all_months[-n_months:]
df_display = df[df['year_month'].isin(display_months)]

# ?쒕퉬??臾댁뿭 ?곗씠???앹꽦
df_service = processor.get_service_trade_data(all_months)
df_service_display = df_service[df_service['year_month'].isin(display_months)]

# 硫붿씤 ?ㅻ뜑 (2?? 醫뚯륫 ??댄? / ?곗륫 怨쇱뾽紐?CI)
hdr_left, hdr_right = st.columns([2, 1])

with hdr_left:
    st.title("愿?몄껌 ICT ?덈ぉ ?뱀썡 ?섏텧 ?ㅼ쟻")

with hdr_right:
    # 濡쒓퀬 ?쇨린 (base64)
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
                    2026??ICT?듦퀎議곗궗 ?ㅼ궗 ?⑹뿭
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                {_logo_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

# ?곗씠???ъ쟾 怨꾩궛 (??怨듭슜)
last_month = df_display['year_month'].max()
prev_month = sorted(df_display['year_month'].unique())[-2] if len(df_display['year_month'].unique()) > 1 else last_month
yoy_month_val = (datetime.strptime(last_month, "%Y%m") - timedelta(days=365)).strftime("%Y%m")

curr_df = df_display[df_display['year_month'] == last_month]
prev_df = df_display[df_display['year_month'] == prev_month]
yoy_df_source = df[df['year_month'] == yoy_month_val]

growth_df_mom = processor.calculate_growth(curr_df, prev_df)
growth_df_yoy = processor.calculate_growth(curr_df, yoy_df_source)

# MoM怨?YoY瑜??⑹튇 理쒖쥌 ?곗씠?고봽?덉엫
growth_df = growth_df_mom.copy()
growth_df['growth_rate_yoy'] = growth_df_yoy['growth_rate']

# ??硫붾돱 援ъ꽦 (二쇱슂 ?덈ぉ ?꾪솴 ???덈ぉ蹂??곸꽭 ?곗씠?????붾퀎 ?섏텧??異붿씠 ???쒕퉬??臾댁뿭 ?듦퀎)
tab1, tab2, tab3, tab4 = st.tabs([
    "?벀 二쇱슂 ?덈ぉ ?꾪솴 (愿?몄껌)", 
    "?뱥 ?덈ぉ蹂??곸꽭 ?곗씠??(愿?몄껌)", 
    "?뱤 ?붾퀎 ?섏텧??異붿씠 (愿?몄껌)", 
    "?뮲 ?쒕퉬??臾댁뿭 ?듦퀎 (?쒓뎅???"
])

# ??????????????????????????????????????????????
# TAB 1: 二쇱슂 ?덈ぉ ?꾪솴 (5??移대뱶 洹몃━??
# ??????????????????????????????????????????????
with tab1:
    st.header(f"?벀 二쇱슂 ?덈ぉ ({last_month[:4]}.{last_month[4:]}) ?꾪솴 (異쒖쿂: 愿?몄껌)")
    st.caption("MoM: ?꾩썡 ?鍮?利앷컧瑜?/ YoY: ?꾨뀈 ?숈썡 ?鍮?利앷컧瑜?)

    # ?꾪꽣 ?? 移댄뀒怨좊━ ?꾪꽣 + ?덈ぉ 寃??    filter_col1, filter_col2 = st.columns([1, 2])
    with filter_col1:
        cat_options = ["?꾩껜"] + list(data_processor.ICT_CATEGORIES.keys())
        selected_cat = st.selectbox("?덈ぉ援??꾪꽣", cat_options, index=0, key="grid_cat_filter")
    with filter_col2:
        search_query = st.text_input(
            "?뵇 ?덈ぉ 寃??,
            placeholder="?덈ぉ紐??먮뒗 HS肄붾뱶 ?낅젰 (?? DRAM, 諛섎룄泥? 1311...)",
            key="item_search"
        )

    display_growth_df = growth_df.copy()
    if selected_cat != "?꾩껜":
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
    if search_query.strip() or selected_cat != "?꾩껜":
        st.caption(f"寃??寃곌낵: **{total_count}媛?* ?덈ぉ")
    else:
        st.caption(f"?꾩껜 **{total_count}媛?* ?덈ぉ")

    # ?ы빐 ?꾩쟻 ?섏텧???ㅽ뙆?щ씪?몄슜 ?곗씠??(?꾩옱 ?곕룄 1??理쒖떊??
    current_year_str = str(datetime.now().year)
    df_ytd = df[df['year_month'].str.startswith(current_year_str)].copy()
    df_ytd = df_ytd.sort_values('year_month')

    # ?쒖떆???덈ぉ 湲곗??쇰줈 ?꾩쟻 理쒕?媛??ъ쟾怨꾩궛
    # cumsum ?몄뿉 ?뱀썡 ?섏텧?〓룄 鍮꾧탳 ??y異뺤씠 ??긽 ?뱀썡媛??댁긽?꾩쓣 蹂댁옣
    item_cum_max = {}
    for _, _r in display_growth_df.iterrows():
        _d = df_ytd[df_ytd['item_name'] == _r['item_name']].sort_values('year_month').copy()
        cum_max = float(_d['exp_amount'].cumsum().max()) if not _d.empty else 0.0
        curr_val = float(_r.get('exp_amount_curr', 0))
        item_cum_max[_r['item_name']] = max(cum_max, curr_val)

    global_y_max = max(item_cum_max.values(), default=1) * 1.15  # ?곷떒 ?щ갚 15%


    items = list(display_growth_df.iterrows())
    COLS = 5

    for row_start in range(0, len(items), COLS):
        row_items = items[row_start:row_start + COLS]
        cols = st.columns(COLS)

        for col_idx, (_, row) in enumerate(row_items):
            idx_pos = row_start + col_idx

            # MoM ?됱긽
            if row['growth_rate'] >= 0:
                mom_color = "#059669"; mom_bg = "#f0fdf4"; mom_arrow = "??
            else:
                mom_color = "#dc2626"; mom_bg = "#fef2f2"; mom_arrow = "??

            # YoY ?됱긽
            yoy_val = row.get('growth_rate_yoy', 0)
            if pd.isna(yoy_val):
                yoy_val = 0.0
            if yoy_val >= 0:
                yoy_color = "#2563eb"; yoy_bg = "#eff6ff"; yoy_arrow = "??
            else:
                yoy_color = "#d97706"; yoy_bg = "#fffbeb"; yoy_arrow = "??

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
                                    <span style="font-size:0.75rem; font-weight:400; color:#64748b;">諛깅쭔</span>
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
                        # ?? ?ы빐 ?꾩쟻 ?섏텧 洹몃옒??(y異??ы븿, ?뚰삎) ??
                        item_ytd = df_ytd[
                            df_ytd['item_name'] == row['item_name']
                        ].sort_values('year_month').copy()
                        item_ytd['cum_exp'] = item_ytd['exp_amount'].cumsum()
                        item_ytd['month_num'] = item_ytd['year_month'].str[4:].astype(int)
                        item_ytd['month_label'] = item_ytd['month_num'].astype(str) + '??

                        all_month_labels = [f"{m}?? for m in range(1, 13)]

                        fig_spark = go.Figure()
                        if not item_ytd.empty:
                            # 硫붿씤 硫댁쟻 ?쇱씤
                            fig_spark.add_trace(go.Scatter(
                                x=item_ytd['month_label'],
                                y=item_ytd['cum_exp'],
                                mode='lines',
                                line=dict(color='#3b82f6', width=1.5),
                                fill='tozeroy',
                                fillcolor='rgba(59,130,246,0.08)',
                                showlegend=False,
                            ))
                            # ?앹젏 留덉빱 + ?꾩쟻???덉씠釉?(?ㅻⅨ履?
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
                                text='?꾩쟻 ?섏텧??,
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
                                tickvals=[f"{m}?? for m in [1, 4, 7, 10, 12]],
                            ),
                            yaxis=dict(
                                visible=True,
                                showgrid=True,
                                gridcolor='#f1f5f9',
                                showticklabels=False,
                                tickfont=dict(size=8, color='#94a3b8'),
                                tickformat=',.0f',
                                nticks=3,
                                range=[0, global_y_max],  # ?꾩껜 ?덈ぉ 怨듯넻 y異??곹븳
                            ),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            hovermode=False
                        )
                        st.plotly_chart(fig_spark, use_container_width=True,
                                        config={'displayModeBar': False},
                                        key=f"spark_{idx_pos}")


# ??????????????????????????????????????????????
# TAB 2: ?덈ぉ蹂??곸꽭 ?곗씠??# ??????????????????????????????????????????????
with tab2:
    st.header("?뱥 ?덈ぉ蹂??곸꽭 ?곗씠??(異쒖쿂: 愿?몄껌)")
    st.dataframe(
        growth_df[['hs_code', 'item_name', 'category', 'exp_amount_prev', 'exp_amount_curr', 'growth_amount', 'growth_rate', 'growth_rate_yoy']],
        use_container_width=True, hide_index=True
    )
    csv = growth_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("?뱿 ?곸꽭 ?곗씠??CSV ?ㅼ슫濡쒕뱶", data=csv, file_name=f"ict_export_{last_month}.csv", mime="text/csv")

# ??????????????????????????????????????????????
# TAB 3: ?붾퀎 ?섏텧??異붿씠 + 10???깆옣瑜?(?섎뱶?⑥뼱 以묒떖)
# ??????????????????????????????????????????????
with tab3:
    st.header("?뱢 ICT ?遺꾨쪟蹂??섏텧 ?꾪솴 (異쒖쿂: 愿?몄껌)")

    # 移댄뀒怨좊━蹂??곗씠??吏묎퀎
    cat_df_full = df.groupby(['year_month', 'category'])['exp_amount'].sum().reset_index()
    cat_df_display = cat_df_full[cat_df_full['year_month'].isin(display_months)].copy()

    all_cats = sorted(cat_df_display['category'].unique())
    selected_cats = st.multiselect("?뱢 異쒕젰 移댄뀒怨좊━ ?좏깮 (愿?몄껌)", options=all_cats, default=all_cats,
                                   help="洹몃옒?꾩뿉 ?쒖떆??移댄뀒怨좊━瑜??좏깮?섏꽭??")

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

    # ?붾퀎 異붿씠 (?섎뱶?⑥뼱 ?⑤룆)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("愿?몄껌 ICT ?덈ぉ蹂??붾퀎 ?섏텧??異붿씠")
        fig_line = px.line(filtered_cat_df, x='year_month', y='exp_amount', color='category', markers=True,
                           custom_data=['yoy_growth'],
                           labels={'exp_amount': '?섏텧??(USD)', 'year_month': '湲곗??꾩썡', 'category': '?遺꾨쪟'})
        fig_line.update_traces(
            hovertemplate="<b>%{fullData.name}</b><br>湲곗??꾩썡: %{x}<br>?섏텧?? %{y:,.0f} USD<br>?꾨뀈鍮? %{customdata[0]}<extra></extra>"
        )
        fig_line.update_layout(template="plotly_white", height=400, margin=dict(t=10, b=10, l=10, r=10),
                               hovermode="x unified",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_line, use_container_width=True)

    with col2:
        last_month_pie_df = cat_df_display[cat_df_display['year_month'] == last_month]
        fig_pie = px.pie(last_month_pie_df, values='exp_amount', names='category', title=f"?뱀썡({last_month}) ?섎뱶?⑥뼱 鍮꾩쨷 (愿?몄껌)",
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie.update_traces(textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, template="plotly_white", height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    # ?遺꾨쪟蹂?理쒓렐 10???곌컙 ?깆옣瑜?留됰?洹몃옒??(愿?몄껌)
    st.header("?뱤 ICT ?遺꾨쪟蹂?理쒓렐 10???곌컙 ?깆옣瑜?(異쒖쿂: 愿?몄껌)")
    st.caption("媛??遺꾨쪟???곌컙(YoY) ?섏텧 ?깆옣瑜좎쓣 理쒓렐 10??湲곗??쇰줈 ?쒖떆?⑸땲?? (12媛쒖썡 ?꾩꽦 ?곕룄留??ы븿)")

    cat_df_full_copy = cat_df_full.copy()
    cat_df_full_copy['year'] = cat_df_full_copy['year_month'].str[:4].astype(int)

    # ?곕룄蹂?媛??????吏묎퀎 (12媛쒖썡 ?꾩꽦 ?곕룄留?
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

    # ?遺꾨쪟蹂?留됰?洹몃옒??(6媛??遺꾨쪟 ??3+3 ??以?
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
                    st.info(f"{cat}: ?곗씠???놁쓬")
                else:
                    fig_bar = go.Figure(go.Bar(
                        x=cat_annual['year'].astype(str),
                        y=cat_annual['growth_rate_yoy'],
                        marker_color=[color if v >= 0 else '#ef4444' for v in cat_annual['growth_rate_yoy']],
                        text=[f"{v:+.1f}%" for v in cat_annual['growth_rate_yoy']],
                        textposition='outside',
                        hovertemplate="%{x}??br>?깆옣瑜? %{y:+.1f}%<extra></extra>"
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


# ??????????????????????????????????????????????
# TAB 4: ?쒕퉬??臾댁뿭 ?듦퀎 (?낅┰ ??
# ??????????????????????????????????????????????
with tab4:
    st.header("?뮲 ?쒕퉬??臾댁뿭(SW쨌ICT ?쒕퉬?? ?꾪솴 (異쒖쿂: ?쒓뎅???")
    st.info("?쒓뎅???吏?앹꽌鍮꾩뒪 臾댁뿭?듦퀎瑜?湲곕컲?쇰줈 ?뚰봽?몄썾??諛?ICT ?쒕퉬???ㅼ쟻??遺꾩꽍?⑸땲??")

    sw_col1, sw_col2 = st.columns([2, 1])

    with sw_col1:
        st.subheader("?쒓뎅???ICT ?쒕퉬??臾댁뿭 ?붾퀎 ?섏텧??異붿씠")
        fig_sw_line = px.line(df_service_display, x='year_month', y='exp_amount', color='service_name', markers=True,
                              labels={'exp_amount': '?섏텧??(USD)', 'year_month': '湲곗??꾩썡', 'service_name': '??ぉ'})
        fig_sw_line.update_traces(hovertemplate="<b>%{fullData.name}</b><br>湲곗??꾩썡: %{x}<br>?섏텧?? %{y:,.1f} USD<extra></extra>")
        fig_sw_line.update_layout(template="plotly_white", height=400, margin=dict(t=10, b=10, l=10, r=10),
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_sw_line, use_container_width=True)

    with sw_col2:
        last_month_sw_pie = df_service_display[df_service_display['year_month'] == last_month]
        fig_sw_pie = px.pie(last_month_sw_pie, values='exp_amount', names='service_name', title=f"?뱀썡({last_month}) ?쒕퉬??鍮꾩쨷 (?쒓뎅???",
                            hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_sw_pie.update_traces(textinfo='percent+label')
        fig_sw_pie.update_layout(showlegend=False, template="plotly_white", height=350)
        st.plotly_chart(fig_sw_pie, use_container_width=True)

    st.divider()

    # ?쒕퉬??臾댁뿭 ???뺥깭???곸꽭 ?곗씠???쒓났
    st.subheader(f"?쒕퉬??臾댁뿭 二쇱슂 ??ぉ蹂??뱀썡 ?곸꽭 ?ㅼ쟻 ({last_month} 湲곗?)")
    st.dataframe(
        last_month_sw_pie[['service_name', 'exp_amount', 'imp_amount']].rename(
            columns={'service_name': '??ぉ紐?, 'exp_amount': '?섏텧??USD)', 'imp_amount': '?섏엯??USD)'}
        ),
        use_container_width=True, hide_index=True
    )
