"""
期权池 & ESOP 计算器 — 期权池扩大对估值与稀释的影响
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
    page_title="期权池计算 — 融资工具箱",
    page_icon="3️⃣",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
# 颜色
# ═══════════════════════════════════════════════════════════════
COLOR_FOUNDER = "#e34948"
COLOR_ESOP    = "#eda100"
COLOR_INV     = "#2a78d6"
COLOR_OTHER   = "#1baf7a"

# ═══════════════════════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⭐ 期权池参数设置")

    with st.expander("🏢 当前股权结构", expanded=True):
        founder_pct = st.number_input("创始人持股（%）", 0.0, 100.0, value=70.0, format="%.1f")
        existing_esop = st.number_input("现有期权池（%）", 0.0, 100.0, value=10.0, format="%.1f")
        inv_pct = st.number_input("投资人持股（%）", 0.0, 100.0, value=20.0, format="%.1f")

        total_before = founder_pct + existing_esop + inv_pct
        if abs(total_before - 100) > 0.1:
            st.warning(f"当前合计 {total_before:.1f}%，建议调整至 100%")

    st.divider()

    with st.expander("💰 估值设定", expanded=True):
        pre_money = st.number_input("Pre-money 估值（万元）", min_value=1.0, value=10000.0, format="%.0f")
        new_investment = st.number_input("本轮融资金额（万元）", min_value=0.0, value=3000.0, format="%.0f")
        post_money = pre_money + new_investment
        st.caption(f"Post-money **{post_money:,.0f}** 万元")

    st.divider()

    with st.expander("⭐ 期权池调整", expanded=True):
        target_esop = st.number_input(
            "目标期权池比例（%）", 0.0, 50.0, value=15.0, format="%.1f",
            help="投资方要求的期权池比例（含现有+新增）",
        )
        pool_method = st.radio(
            "期权池扩容方式",
            ["投资人前扩容（创始人承担稀释）", "投资人后扩容（共同稀释）"],
            index=0,
            help="VC 通常要求投资前就扩到目标比例，稀释由创始人承担",
        )

    st.divider()

    with st.expander("🎫 期权参数", expanded=True):
        total_shares = st.number_input("总股数（万股）", min_value=1.0, value=1000.0, format="%.0f")
        exercise_price = st.number_input(
            "行权价格（元/股）", min_value=0.01, value=1.0, format="%.2f",
            help="员工期权的行权价，通常为最近一轮优先股价的 10%-40%",
        )
        fair_value = st.number_input(
            "公允价值（元/股）", min_value=0.01, value=10.0, format="%.2f",
            help="当前每股公允价值，可参考最新融资价格",
        )
        vest_years = st.slider("归属期（年）", 1, 8, 4)

# ═══════════════════════════════════════════════════════════════
# 计算引擎
# ═══════════════════════════════════════════════════════════════

# ── 方式一：投资人前扩容 ────────────────────────────────────
if "投资人前" in pool_method:
    # 先扩 ESOP 到目标比例，再引入投资人
    # 扩容后各股东等比稀释
    if existing_esop < target_esop:
        dilution_factor = (100 - target_esop) / (100 - existing_esop)
        founder_after_pool = founder_pct * dilution_factor
        inv_after_pool = inv_pct * dilution_factor
        esop_after_pool = target_esop
    else:
        founder_after_pool = founder_pct
        inv_after_pool = inv_pct
        esop_after_pool = existing_esop

    # 再引入投资人（如果有新投资）
    if new_investment > 0 and post_money > 0:
        new_inv_pct = new_investment / post_money * 100
        dilution2 = 1 - new_inv_pct / 100
        founder_final = founder_after_pool * dilution2
        inv_final = inv_after_pool * dilution2
        esop_final = esop_after_pool * dilution2
        new_inv_final = new_inv_pct
    else:
        founder_final = founder_after_pool
        inv_final = inv_after_pool
        esop_final = esop_after_pool
        new_inv_final = 0

else:
    # 方式二：投资人后扩容
    # 先引入投资人
    if new_investment > 0 and post_money > 0:
        new_inv_pct = new_investment / post_money * 100
        dilution1 = 1 - new_inv_pct / 100
        founder_after_inv = founder_pct * dilution1
        inv_after_inv = inv_pct * dilution1
        esop_after_inv = existing_esop * dilution1
        new_inv_interim = new_inv_pct
    else:
        founder_after_inv = founder_pct
        inv_after_inv = inv_pct
        esop_after_inv = existing_esop
        new_inv_interim = 0

    # 再扩 ESOP
    if esop_after_inv < target_esop:
        dilution2 = (100 - target_esop) / (100 - esop_after_inv)
        founder_final = founder_after_inv * dilution2
        inv_final = inv_after_inv * dilution2
        esop_final = target_esop
        new_inv_final = new_inv_interim * dilution2
    else:
        founder_final = founder_after_inv
        inv_final = inv_after_inv
        esop_final = esop_after_inv
        new_inv_final = new_inv_interim


# ── 期权价值计算 ──────────────────────────────────────────
esop_shares = total_shares * (esop_final if 'esop_final' in dir() else target_esop) / 100
intrinsic_value = max(0, fair_value - exercise_price)
total_option_value = esop_shares * intrinsic_value

# 归属计划：4 年均匀归属
vest_schedule = []
for yr in range(1, vest_years + 1):
    vested_pct = yr / vest_years * 100
    vested_shares = esop_shares * yr / vest_years
    vested_value = vested_shares * intrinsic_value
    vest_schedule.append({
        "年份": f"第 {yr} 年",
        "累计归属比例": f"{vested_pct:.1f}%",
        "累计归属股数（万）": f"{vested_shares:,.1f}",
        "累计归属价值（万元）": f"{vested_value:,.0f}" if intrinsic_value > 0 else "—",
    })


# ═══════════════════════════════════════════════════════════════
# 主区域
# ═══════════════════════════════════════════════════════════════
st.title("⭐ 期权池 & ESOP 计算器")
st.markdown(
    f"目标期权池 **{target_esop:.1f}%**，"
    f"扩容方式：**{'投资人前扩容' if '投资人前' in pool_method else '投资人后扩容'}**。"
)

# ── 1. 稀释前后对比 ────────────────────────────────────────
st.subheader("🔄 稀释前后对比")

fig_before = go.Figure(go.Pie(
    labels=["创始人", "现有期权池", "投资人"],
    values=[founder_pct, existing_esop, inv_pct],
    hole=0.4, sort=False,
    marker_colors=[COLOR_FOUNDER, COLOR_ESOP, COLOR_INV],
    textinfo="label+percent", textposition="inside",
    textfont_size=13,
))
fig_before.update_layout(title="调整前", height=350, margin=dict(t=50, b=10, l=10, r=10), showlegend=False)

# After
after_labels = ["创始人", "期权池", "原有投资人"]
after_values = [founder_final, esop_final, inv_final]
after_colors = [COLOR_FOUNDER, COLOR_ESOP, COLOR_INV]

if new_investment > 0:
    after_labels.append("新投资人")
    after_values.append(new_inv_final)
    after_colors.append(COLOR_OTHER)

fig_after = go.Figure(go.Pie(
    labels=after_labels, values=after_values,
    hole=0.4, sort=False,
    marker_colors=after_colors,
    textinfo="label+percent", textposition="inside",
    textfont_size=13,
))
fig_after.update_layout(title="调整后", height=350, margin=dict(t=50, b=10, l=10, r=10), showlegend=False)

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(fig_before, use_container_width=True)
with c2:
    st.plotly_chart(fig_after, use_container_width=True)

# ── 2. 核心指标 ────────────────────────────────────────────
st.subheader("📊 核心指标")

m1, m2, m3, m4 = st.columns(4)
m1.metric("创始人稀释", f"−{founder_pct - founder_final:.2f}%", delta=f"{founder_final:.1f}% 剩余")
m2.metric("期权池变化", f"+{esop_final - existing_esop:.2f}%", delta=f"→ {esop_final:.1f}%")
m3.metric("投资人稀释", f"−{inv_pct - inv_final:.2f}%", delta=f"{inv_final:.1f}% 剩余")
m4.metric("新增期权池", f"{max(0, target_esop - existing_esop):.1f}%")

# ── 3. 估值影响 ────────────────────────────────────────────
st.subheader("💰 估值影响分析")

# 稀释前估值（不含期权池扩容）vs 稀释后
pre_dilution_val = pre_money
post_dilution_val = pre_money * (founder_final / founder_pct) if founder_pct > 0 else 0

vi1, vi2, vi3 = st.columns(3)
vi1.metric("Pre-money（名义）", f"{pre_money:,.0f} 万")
vi2.metric("创始人有效估值", f"{post_dilution_val:,.0f} 万",
           delta=f"−{pre_money - post_dilution_val:,.0f} 万" if post_dilution_val < pre_money else None,
           delta_color="inverse")
vi3.metric("期权池成本", f"{(pre_money - post_dilution_val):,.0f} 万")

st.markdown(
    """
    > **💡 解读**：投资人说"Pre-money 1 亿、期权池 15%"，意思是你要在 1 亿估值里切 15% 出来做期权池，
    > 创始人的**有效估值**实际上被压低了。上表「创始人有效估值」反映的就是这个真实情况。
    """
)

# ── 4. 期权价值 ────────────────────────────────────────────
st.subheader("🎫 期权价值评估")

o1, o2, o3, o4 = st.columns(4)
o1.metric("期权池股数", f"{esop_shares:,.1f} 万股")
o2.metric("行权价", f"{exercise_price:.2f} 元/股")
o3.metric("每股内在价值", f"{intrinsic_value:.2f} 元" if intrinsic_value > 0 else "虚值期权")
o4.metric("期权池总价值", f"{total_option_value:,.0f} 万元" if intrinsic_value > 0 else "—")

# ── 5. 归属时间表 ──────────────────────────────────────────
st.subheader(f"📅 归属时间表（{vest_years} 年均匀归属）")

df_vest = pd.DataFrame(vest_schedule)
st.dataframe(df_vest, use_container_width=True, hide_index=True)

# ── 6. 归属价值曲线 ────────────────────────────────────────
if intrinsic_value > 0:
    fig_vest = go.Figure()
    years = list(range(0, vest_years + 1))
    values = [esop_shares * yr / vest_years * intrinsic_value for yr in years]

    fig_vest.add_trace(go.Scatter(
        x=years, y=values,
        mode="lines+markers+text",
        text=[f"{v:,.0f}万" for v in values],
        textposition="top center",
        line_color=COLOR_ESOP, line_width=3, marker_size=8,
        hovertemplate="第 %{x} 年<br>累计价值: %{y:,.0f} 万元<extra></extra>",
    ))
    fig_vest.update_layout(
        xaxis=dict(title="年份", dtick=1),
        yaxis=dict(title="累计归属价值（万元）", rangemode="tozero"),
        height=350, margin=dict(t=30, b=50),
    )
    st.plotly_chart(fig_vest, use_container_width=True)

# ── 7. 不同目标比例敏感性 ──────────────────────────────────
st.subheader("🔍 期权池比例敏感性分析")

target_range = [5, 8, 10, 12, 15, 18, 20, 25]
sens_rows = []
for t in target_range:
    if "投资人前" in pool_method:
        if existing_esop < t:
            df = (100 - t) / (100 - existing_esop)
        else:
            df = 1.0
    else:
        # 简化：投资人后扩容
        if existing_esop < t:
            df = (100 - t) / (100 - existing_esop)
        else:
            df = 1.0

    f_pct = founder_pct * df
    i_pct = inv_pct * df
    effective_val = pre_money * (f_pct / founder_pct) if founder_pct > 0 else 0
    pool_cost = pre_money - effective_val

    sens_rows.append({
        "目标池比例": f"{t}%",
        "创始人持股": f"{f_pct:.1f}%",
        "投资人持股": f"{i_pct:.1f}%",
        "创始人有效估值（万）": f"{effective_val:,.0f}",
        "期权池估值成本（万）": f"{pool_cost:,.0f}",
    })

df_sens = pd.DataFrame(sens_rows)
st.dataframe(df_sens, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "💡 **谈判要点**：投资人要求 15% 期权池投前扩容 = 创始人独自承担稀释。"
    "可谈判：① 期权池投后扩容（共同稀释）；② 降低目标比例；③ 用已发期权充抵池子。"
)
