"""
VC 估值工具（倒推法） — 目标回报 + 退出估值 + 稀释 → 今天可接受估值
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="VC 估值工具 — 融资工具箱",
    page_icon="4️⃣",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("💎 VC 估值参数")

    with st.expander("🎯 回报目标", expanded=True):
        target_multiple = st.number_input(
            "目标回报倍数", 1.0, 100.0, value=10.0, format="%.1f",
            help="VC 基金通常要求 10x 回报（早期），3-5x（后期）",
        )
        exit_val = st.number_input(
            "预期退出估值（万元）", min_value=100.0, value=500000.0, format="%.0f",
            help="预期 IPO/并购时的公司估值",
        )
        exit_years = st.slider("预期退出年限", 1, 10, 5)

    st.divider()

    with st.expander("📉 后续稀释预估", expanded=True):
        st.caption("估算后续融资中本轮融资会被稀释的比例")
        future_dilution = st.slider(
            "预期总稀释比例（%）", 0, 90, value=50,
            help="后续轮次融资导致持股被稀释的累计比例。\n早期项目通常 40-60%，后期 10-30%",
        )

    st.divider()

    with st.expander("📊 敏感性分析", expanded=True):
        multiple_range = st.slider(
            "回报倍数范围", 2.0, 30.0, value=(5.0, 15.0), step=1.0,
        )
        exit_range = st.slider(
            "退出估值范围（亿元）", 1.0, 50.0, value=(2.0, 10.0), step=0.5,
        )

# ═══════════════════════════════════════════════════════════════
# 计算引擎
# ═══════════════════════════════════════════════════════════════

def vc_valuation(exit_val_wan: float, target_mult: float, dilution_pct: float) -> dict:
    """
    VC 倒推估值法：
    1. 目标退出价值 = 投资金额 × 目标倍数
    2. 退出时需持有的股份 = 目标退出价值 / 退出估值
    3. 今天需持有的股份 = 退出时股份 / (1 - 稀释率)
    4. 投后估值 = 投资金额 / 今天持股比例
    5. 投前估值 = 投后估值 - 投资金额
    """
    # 以投资 1 万元为基准算持股比例
    target_exit_value = 1.0 * target_mult  # 目标退出时这 1 万要变成多少
    exit_share = target_exit_value / exit_val_wan  # 退出时需要的持股比例
    today_share = exit_share / (1 - dilution_pct / 100)  # 考虑稀释

    if today_share <= 0 or today_share >= 1:
        return None

    post_money_per_unit = 1.0 / today_share  # 投 1 万对应的 post-money
    pre_money_per_unit = post_money_per_unit - 1.0

    return {
        "exit_share_pct": exit_share * 100,
        "today_share_pct": today_share * 100,
        "post_money_ratio": post_money_per_unit,  # 投后估值 / 投资金额
        "pre_money_ratio": pre_money_per_unit,    # 投前估值 / 投资金额
    }


result = vc_valuation(exit_val, target_multiple, future_dilution)

# ═══════════════════════════════════════════════════════════════
# 主区域
# ═══════════════════════════════════════════════════════════════
st.title("💎 VC 估值工具（倒推法）")
st.markdown(
    f"目标 **{target_multiple:.1f}x** 回报，预期退出估值 **{exit_val / 10000:,.1f}** 亿元，"
    f"退出年限 **{exit_years}** 年，后续稀释 **{future_dilution}%**。"
)

if result is None:
    st.error("⚠️ 参数组合下无法计算合理估值（持股比例 ≥ 100%），请调整目标倍数或退出估值。")
    st.stop()

# ── 1. 核心结果 ────────────────────────────────────────────
st.subheader("📊 倒推结果")

r1, r2, r3, r4 = st.columns(4)
r1.metric(
    "退出时需持股",
    f"{result['exit_share_pct']:.2f}%",
    help="退出时这轮投资人需要持有的股份比例",
)
r2.metric(
    "今天需持股",
    f"{result['today_share_pct']:.2f}%",
    help="考虑后续稀释后，今天需要持有的股份比例",
)
r3.metric(
    "投后/投资额 倍数",
    f"{result['post_money_ratio']:.1f}x",
    help="投后估值 = 投资金额 × 此倍数",
)
r4.metric(
    "投前/投资额 倍数",
    f"{result['pre_money_ratio']:.1f}x",
    help="投前估值 = 投资金额 × 此倍数",
)

st.markdown("### 💰 不同投资额对应的估值")

inv_amounts = [500, 1000, 2000, 3000, 5000, 8000, 10000]
val_rows = []
for inv in inv_amounts:
    pre = inv * result["pre_money_ratio"]
    post = inv * result["post_money_ratio"]
    irr = (target_multiple ** (1 / exit_years) - 1) * 100 if exit_years > 0 else 0
    val_rows.append({
        "投资额（万元）": f"{inv:,}",
        "投前估值（万元）": f"{pre:,.0f}",
        "投后估值（万元）": f"{post:,.0f}",
        "持股比例": f"{result['today_share_pct']:.2f}%",
        "退出回报": f"{target_multiple:.1f}x",
        "隐含 IRR": f"{irr:.1f}%",
    })

df_val = pd.DataFrame(val_rows)
st.dataframe(df_val, use_container_width=True, hide_index=True)

# ── 2. 倒推逻辑图示 ────────────────────────────────────────
st.subheader("🔄 倒推逻辑")

steps = [
    ("① 目标退出价值", f"投资额 × {target_multiple:.1f}x"),
    ("② 退出时持股", f"目标退出价值 ÷ 退出估值 = {result['exit_share_pct']:.2f}%"),
    ("③ 考虑稀释", f"退出持股 ÷ (1−{future_dilution}%) = {result['today_share_pct']:.2f}%"),
    ("④ 投后估值", f"投资额 ÷ {result['today_share_pct']:.2f}% = 投资额 × {result['post_money_ratio']:.1f}"),
    ("⑤ 投前估值", f"投后 − 投资额 = 投资额 × {result['pre_money_ratio']:.1f}"),
]

for label, desc in steps:
    st.markdown(f"**{label}**  →  {desc}")

# ── 3. IRR 分析 ────────────────────────────────────────────
st.subheader("📈 IRR & 回报倍数")

irr = (target_multiple ** (1 / exit_years) - 1) * 100 if exit_years > 0 else 0

i1, i2, i3 = st.columns(3)
i1.metric("隐含 IRR", f"{irr:.1f}%")
i2.metric("回报倍数", f"{target_multiple:.1f}x")
i3.metric("退出年限", f"{exit_years} 年")

# IRR vs 年限曲线
fig_irr = go.Figure()
years_range = list(range(2, 11))
for mult in [3, 5, 10, 15, 20]:
    irrs = [(mult ** (1 / yr) - 1) * 100 for yr in years_range]
    fig_irr.add_trace(go.Scatter(
        x=years_range, y=irrs, name=f"{mult}x",
        mode="lines+markers", line_width=2.5, marker_size=6,
        hovertemplate=f"{mult}x · %{x}年 → IRR %{y:.1f}%<extra></extra>",
    ))

fig_irr.add_trace(go.Scatter(
    x=[exit_years], y=[irr], name="当前方案",
    mode="markers", marker_size=14, marker_color="#e34948", marker_symbol="star",
    hovertemplate=f"当前: {target_multiple}x · {exit_years}年 → IRR {irr:.1f}%<extra></extra>",
))

fig_irr.update_layout(
    xaxis=dict(title="退出年限（年）", dtick=1),
    yaxis=dict(title="IRR（%）", rangemode="tozero"),
    height=380, margin=dict(t=30, b=50),
    legend=dict(orientation="h", yanchor="bottom", y=1.08, font_size=11),
)
st.plotly_chart(fig_irr, use_container_width=True)

# ── 4. 敏感性热力图：退出估值 × 回报倍数 → 投前/投资额 ─────
st.subheader("🗺️ 敏感性热力图：可接受投前/投资额 倍数")

mult_range = np.arange(multiple_range[0], multiple_range[1] + 0.5, 1.0)
exit_range_wan = np.arange(exit_range[0], exit_range[1] + 0.25, 0.5) * 10000

heatmap_data = []
for m in mult_range:
    row = []
    for ev in exit_range_wan:
        r = vc_valuation(ev, m, future_dilution)
        if r and r["pre_money_ratio"] > 0:
            row.append(r["pre_money_ratio"])
        else:
            row.append(None)
    heatmap_data.append(row)

fig_heat = go.Figure(go.Heatmap(
    x=[f"{ev/10000:.1f}亿" for ev in exit_range_wan],
    y=[f"{m:.0f}x" for m in mult_range],
    z=heatmap_data,
    colorscale="RdYlGn",
    text=[[f"{v:.0f}" if v else "—" for v in row] for row in heatmap_data],
    texttemplate="%{text}",
    textfont=dict(size=10),
    hovertemplate="退出估值: %{x}<br>回报倍数: %{y}<br>投前/投资额: %{z:.0f}x<extra></extra>",
    colorbar=dict(title="倍数"),
))

fig_heat.update_layout(
    xaxis=dict(title="预期退出估值"),
    yaxis=dict(title="目标回报倍数"),
    height=max(350, len(mult_range) * 35 + 100),
    margin=dict(t=30, b=60),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown(
    """
    > **💡 读图**：数字 = 投前估值 ÷ 投资金额。例如显示 "50"，意味着投资 2000 万时投前估值可为 10 亿。
    > 绿色区域 = 估值空间大（好机会），红色区域 = 估值空间小（很难满足回报要求）。
    """
)

# ── 5. 稀释敏感性 ──────────────────────────────────────────
st.subheader("📉 后续稀释对估值的影响")

dilution_range = [10, 20, 30, 40, 50, 60, 70]
dilution_rows = []
for d in dilution_range:
    r = vc_valuation(exit_val, target_multiple, d)
    if r:
        dilution_rows.append({
            "后续稀释": f"{d}%",
            "今天需持股": f"{r['today_share_pct']:.2f}%",
            "投前/投资额": f"{r['pre_money_ratio']:.1f}x",
            "投后/投资额": f"{r['post_money_ratio']:.1f}x",
            "投前估值（投资5000万时）": f"{5000 * r['pre_money_ratio']:,.0f} 万",
        })

df_dilution = pd.DataFrame(dilution_rows)
st.dataframe(df_dilution, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "💡 **VC 估值法要点**：倒推法告诉你「在目标回报下，今天最多能接受什么估值」。"
    "实际谈判中，还需结合可比公司估值、赛道热度、团队等因素综合判断。"
    "早期项目稀释通常 40-60%，后期 10-30%，据此调整稀释参数。"
)
