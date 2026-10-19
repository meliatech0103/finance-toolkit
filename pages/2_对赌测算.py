"""
对赌 / 业绩承诺测算 — 模拟不同完成率下双方付出
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="对赌测算 — 融资工具箱",
    page_icon="2️⃣",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("🎯 对赌参数设置")

    # 业绩承诺
    with st.expander("📈 业绩承诺", expanded=True):
        metric = st.selectbox("业绩指标", ["净利润", "营业收入", "EBITDA", "GMV"], index=0)
        target_val = st.number_input(
            f"承诺{metric}（万元）", min_value=1.0, value=3000.0, format="%.0f",
            help="对赌协议中承诺的目标业绩",
        )
        target_years = st.slider("对赌期限（年）", 1, 5, 3)

    st.divider()

    # 投资情况
    with st.expander("💰 投资情况", expanded=True):
        inv_amount = st.number_input("投资金额（万元）", min_value=1.0, value=5000.0, format="%.0f")
        inv_pct = st.number_input("投资人持股比例（%）", 0.1, 99.0, value=20.0, format="%.1f")
        post_money = inv_amount / (inv_pct / 100) if inv_pct > 0 else 0
        st.caption(f"隐含 Post-money **{post_money:,.0f}** 万元")

    st.divider()

    # 补偿方式
    with st.expander("⚖️ 补偿条款", expanded=True):
        comp_type = st.radio(
            "补偿方式",
            ["现金补偿", "股份回购", "股份补偿"],
            index=0,
            horizontal=True,
        )

        if comp_type == "现金补偿":
            cash_multiplier = st.number_input(
                "补偿倍数", 0.1, 10.0, value=1.0, format="%.1f",
                help="现金补偿 = (1 − 完成率) × 投资金额 × 补偿倍数",
            )
            st.caption("公式：补偿金额 = (1 − 完成率) × 投资金额 × 倍数")
        elif comp_type == "股份回购":
            repo_rate = st.number_input(
                "年化回购利率（%）", 0.0, 30.0, value=8.0, format="%.1f",
                help="回购价格 = 投资金额 × (1 + 年利率 × 对赌年数)",
            )
            st.caption("公式：回购价格 = 投资金额 × (1 + 利率 × 年数)")
        else:  # 股份补偿
            share_multiplier = st.number_input(
                "补偿倍数", 0.1, 10.0, value=1.0, format="%.1f",
                help="补偿股份比例 = (1 − 完成率) × 投资人持股比例 × 倍数",
            )
            st.caption("公式：补偿比例 = (1 − 完成率) × 投资人比例 × 倍数")

    st.divider()

    # 完成率范围
    with st.expander("🔢 模拟范围", expanded=True):
        cr_min = st.slider("最低完成率（%）", 0, 100, 50)
        cr_max = st.slider("最高完成率（%）", 0, 100, 120)
        cr_step = st.slider("步长（%）", 1, 10, 5)


# ═══════════════════════════════════════════════════════════════
# 计算引擎
# ═══════════════════════════════════════════════════════════════
def calc_compensation(completion_rate: float) -> dict:
    """
    根据完成率计算各方付出。
    completion_rate: 实际业绩 / 承诺业绩 × 100
    """
    cr = completion_rate / 100  # 归一化

    result = {
        "completion_rate": completion_rate,
        "actual_perf": target_val * cr,
        "shortfall": max(0, target_val - target_val * cr),
    }

    if completion_rate >= 100:
        # 完成承诺，无需补偿
        result.update({
            "investor_gets": 0,
            "founder_pays": 0,
            "method": "✅ 无需补偿",
        })
        return result

    gap = 1 - cr  # 未完成比例

    if comp_type == "现金补偿":
        amount = gap * inv_amount * cash_multiplier
        result.update({
            "investor_gets": amount,
            "founder_pays": amount,
            "method": f"现金 {amount:,.0f} 万",
        })

    elif comp_type == "股份回购":
        repo_price = inv_amount * (1 + repo_rate / 100 * target_years)
        # 回购比例：投资人需要回购的股份 = 投资比例 × 未完成比例
        repo_share = inv_pct * gap
        result.update({
            "investor_gets": repo_price * gap,  # 按未完成比例计算回购
            "founder_pays": repo_price * gap,
            "repo_price_total": repo_price,
            "repo_share": repo_share,
            "method": f"回购 {repo_share:.2f}% 股份（总价 {repo_price * gap:,.0f} 万）",
        })

    else:  # 股份补偿
        comp_share = gap * inv_pct * share_multiplier
        # 补偿后双方持股
        new_inv_pct = inv_pct - comp_share
        new_founder_pct = (100 - inv_pct) + comp_share
        result.update({
            "investor_gets": comp_share,  # 获得的补偿股份比例
            "founder_pays": comp_share,   # 创始人给出的股份比例
            "new_inv_pct": new_inv_pct,
            "new_founder_pct": new_founder_pct,
            "method": f"补偿 {comp_share:.2f}% 股份",
        })

    return result


# 生成全部完成率的结果
completion_rates = list(range(cr_min, cr_max + 1, cr_step))
if 100 not in completion_rates:
    completion_rates.append(100)
    completion_rates.sort()

results = [calc_compensation(cr) for cr in completion_rates]

# ═══════════════════════════════════════════════════════════════
# 主区域
# ═══════════════════════════════════════════════════════════════
st.title("🎯 对赌 / 业绩承诺测算")
st.markdown(
    f"承诺{metric} **{target_val:,.0f}** 万元，对赌 **{target_years}** 年，"
    f"投资人投入 **{inv_amount:,.0f}** 万元占 **{inv_pct:.1f}%**。"
)

# ── 1. 补偿金额 vs 完成率曲线 ─────────────────────────────
st.subheader("📈 补偿金额 vs 完成率")

fig_line = go.Figure()

crs = [r["completion_rate"] for r in results]
pays = [r["founder_pays"] for r in results]

fig_line.add_trace(go.Scatter(
    x=crs, y=pays,
    mode="lines+markers+text",
    text=[f"{v:,.0f}" if v > 0 else "" for v in pays],
    textposition="top center",
    line_color="#e34948", line_width=3, marker_size=8,
    name="创始人付出",
    hovertemplate="完成率: %{x}%<br>补偿: %{y:,.0f} 万元<extra></extra>",
))

# 标记 100% 完成线
fig_line.add_vline(x=100, line_dash="dash", line_color="#1baf7a", line_width=2,
                   annotation_text="达标线", annotation_position="top right")

fig_line.update_layout(
    xaxis=dict(title="业绩完成率（%）", range=[cr_min - 2, cr_max + 2]),
    yaxis=dict(title="创始人补偿金额（万元）", rangemode="tozero"),
    height=420, margin=dict(t=30, b=50),
    legend=dict(orientation="h", yanchor="bottom", y=1.08),
)
st.plotly_chart(fig_line, use_container_width=True)

# ── 2. 关键场景速查 ────────────────────────────────────────
st.subheader("🔢 关键场景速查")

key_rates = [50, 60, 70, 80, 90, 100, 110, 120]
key_rates = [r for r in key_rates if cr_min <= r <= cr_max]
if 100 not in key_rates:
    key_rates.append(100)
key_rates.sort()

kcols = st.columns(len(key_rates))
for i, kr in enumerate(key_rates):
    r = calc_compensation(kr)
    with kcols[i]:
        if kr >= 100:
            st.metric(f"{kr}%", "✅ 达标", delta="无需补偿")
        else:
            if comp_type == "股份补偿":
                st.metric(f"{kr}%", f"−{r['founder_pays']:.2f}%", delta="股份补偿")
            else:
                st.metric(f"{kr}%", f"−{r['founder_pays']:,.0f}万", delta="补偿")

# ── 3. 完整数据表 ──────────────────────────────────────────
st.subheader("📋 完成率 — 补偿明细表")

table_rows = []
for r in results:
    row = {
        "完成率": f"{r['completion_rate']}%",
        f"实际{metric}（万）": f"{r['actual_perf']:,.0f}",
        f"缺口（万）": f"{r['shortfall']:,.0f}",
        "补偿方式": r["method"],
    }

    if comp_type == "现金补偿":
        row["创始人支付（万）"] = f"{r['founder_pays']:,.0f}"
        row["投资人获得（万）"] = f"{r['investor_gets']:,.0f}"
    elif comp_type == "股份回购":
        row["回购总价（万）"] = f"{r.get('repo_price_total', 0):,.0f}"
        row["创始人支付（万）"] = f"{r['founder_pays']:,.0f}"
        row["回购股份比例"] = f"{r.get('repo_share', 0):.2f}%"
    else:
        row["补偿股份比例"] = f"{r['founder_pays']:.2f}%"
        row["投资人新持股"] = f"{r.get('new_inv_pct', inv_pct):.2f}%"
        row["创始人新持股"] = f"{r.get('new_founder_pct', 100 - inv_pct):.2f}%"

    table_rows.append(row)

df_table = pd.DataFrame(table_rows)
st.dataframe(df_table, use_container_width=True, hide_index=True)

# ── 4. 股份补偿模式：持股变化图 ────────────────────────────
if comp_type == "股份补偿":
    st.subheader("🔄 完成率 — 持股结构变化")

    fig_share = go.Figure()

    inv_pcts = []
    founder_pcts = []
    for r in results:
        if r["completion_rate"] >= 100:
            inv_pcts.append(inv_pct)
            founder_pcts.append(100 - inv_pct)
        else:
            inv_pcts.append(r.get("new_inv_pct", inv_pct))
            founder_pcts.append(r.get("new_founder_pct", 100 - inv_pct))

    fig_share.add_trace(go.Scatter(
        x=crs, y=inv_pcts, name="投资人",
        mode="lines+markers", line_color="#2a78d6", line_width=2.5, marker_size=7,
        hovertemplate="完成率: %{x}%<br>投资人: %{y:.2f}%<extra></extra>",
    ))
    fig_share.add_trace(go.Scatter(
        x=crs, y=founder_pcts, name="创始人团队",
        mode="lines+markers", line_color="#e34948", line_width=2.5, marker_size=7,
        hovertemplate="完成率: %{x}%<br>创始人: %{y:.2f}%<extra></extra>",
    ))
    fig_share.add_vline(x=100, line_dash="dash", line_color="#1baf7a", line_width=1.5)

    fig_share.update_layout(
        xaxis=dict(title="业绩完成率（%）"),
        yaxis=dict(title="持股比例（%）", range=[0, 100]),
        height=380, margin=dict(t=30, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.08),
    )
    st.plotly_chart(fig_share, use_container_width=True)

# ── 5. 现金流对比 ──────────────────────────────────────────
st.subheader("💵 创始人净现金流分析")

cash_rows = []
for r in results:
    cr = r["completion_rate"]
    if cr >= 100:
        # 达标：创始人按持股比例享有估值
        net = 0  # 无补偿支出
        cash_rows.append({
            "完成率": f"{cr}%",
            "补偿支出": "0",
            "创始人净支出": "0",
            "状态": "✅ 达标",
        })
    else:
        if comp_type == "股份补偿":
            cash_rows.append({
                "完成率": f"{cr}%",
                "补偿支出": f"−{r['founder_pays']:.2f}% 股份",
                "创始人净支出": f"−{r['founder_pays']:.2f}% 股份",
                "状态": "⚠️ 触发补偿",
            })
        else:
            cash_rows.append({
                "完成率": f"{cr}%",
                "补偿支出": f"−{r['founder_pays']:,.0f} 万",
                "创始人净支出": f"−{r['founder_pays']:,.0f} 万",
                "状态": "⚠️ 触发补偿",
            })

df_cash = pd.DataFrame(cash_rows)
st.dataframe(df_cash, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "💡 **对赌常识**：现金补偿对创始人现金流压力最大；"
    "股份回购可协商分期；股份补偿影响控制权但不动现金。"
    "建议在签约前用本工具模拟各完成率场景，评估自身承受能力。"
)
