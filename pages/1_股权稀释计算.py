"""
股权稀释计算 — 多轮融资下创始人股权稀释模拟
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

st.set_page_config(
    page_title="股权稀释计算 — 融资工具箱",
    page_icon="1️⃣",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
# 颜色方案
# ═══════════════════════════════════════════════════════════════
FOUNDER_HUES = ["#e34948", "#eb6834", "#e87ba4", "#eda100"]
ESOP_HUE     = "#eda100"
INVESTOR_HUES = ["#2a78d6", "#1baf7a", "#4a3aa7", "#008300",
                 "#3987e5", "#199e70", "#9085e9", "#0ca30c"]


def build_color_map(entity_names: list[str], founder_names: list[str]) -> dict[str, str]:
    cmap: dict[str, str] = {}
    fi, ii = 0, 0
    for name in entity_names:
        if name in founder_names:
            cmap[name] = FOUNDER_HUES[fi % len(FOUNDER_HUES)]
            fi += 1
        elif "ESOP" in name or "期权" in name:
            cmap[name] = ESOP_HUE
        else:
            cmap[name] = INVESTOR_HUES[ii % len(INVESTOR_HUES)]
            ii += 1
    return cmap


# ═══════════════════════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("📋 融资参数设置")

    with st.expander("👤 创始人设置", expanded=True):
        founder_input = st.text_area(
            "姓名（每行一位）", "创始人A\n创始人B", height=70,
            help="支持 1~5 位创始人，每行输入一位姓名",
        )
        founder_names = [f.strip() for f in founder_input.split("\n") if f.strip()]
        nf = len(founder_names)

        if nf == 1:
            _def_splits = "100"
        elif nf == 2:
            _def_splits = "60\n40"
        elif nf == 3:
            _def_splits = "51\n30\n19"
        else:
            _def_splits = "\n".join(str(round(100 / nf, 1)) for _ in range(nf))

        split_input = st.text_area(
            "初始持股比例（%，每行对应上方）", _def_splits, height=70,
            help="百分比，不要求合计 100，系统会自动归一化",
        )
        try:
            initial_splits = [float(s.strip()) for s in split_input.split("\n") if s.strip()]
        except ValueError:
            initial_splits = []

    st.divider()

    st.subheader("💰 融资轮次")
    num_rounds = st.slider("轮次数", 1, 8, 3, step=1)

    _ROUND_DEFAULTS = [
        {"name": "天使轮",   "inv": 500,   "pm": 2500,    "esop": 10},
        {"name": "A 轮",    "inv": 3000,  "pm": 12000,   "esop": 5},
        {"name": "B 轮",    "inv": 10000, "pm": 50000,   "esop": 0},
        {"name": "C 轮",    "inv": 30000, "pm": 150000,  "esop": 0},
        {"name": "D 轮",    "inv": 80000, "pm": 400000,  "esop": 0},
        {"name": "E 轮",    "inv": 2e5,   "pm": 1e6,     "esop": 0},
        {"name": "F 轮",    "inv": 5e5,   "pm": 2.5e6,   "esop": 0},
        {"name": "Pre-IPO", "inv": 1e6,   "pm": 5e6,     "esop": 0},
    ]

    rounds_data: list[dict] = []
    for i in range(num_rounds):
        d = _ROUND_DEFAULTS[i] if i < len(_ROUND_DEFAULTS) else {
            "name": f"轮 {i+1}", "inv": 1000, "pm": 5000, "esop": 0
        }
        with st.expander(f"第 {i+1} 轮：{d['name']}", expanded=(i < 2)):
            r_name = st.text_input("轮次名称", d["name"], key=f"rn_{i}")
            c1, c2 = st.columns(2)
            with c1:
                inv = st.number_input(
                    "融资金额（万元）", 0.0,
                    value=float(d["inv"]), key=f"iv_{i}", format="%.0f",
                )
            with c2:
                pm = st.number_input(
                    "Pre-money 估值（万元）", 0.0,
                    value=float(d["pm"]), key=f"pm_{i}", format="%.0f",
                )
            esop = st.number_input(
                "ESOP 预留比例（%）", 0.0, 49.0,
                value=float(d["esop"]), key=f"eo_{i}", format="%.1f",
                help="本轮投资前，将 ESOP 池扩容至该比例（仅当当前池不足时扩容）",
            )

            if pm + inv > 0:
                inv_pct = inv / (pm + inv) * 100
                st.caption(
                    f"Post-money **{pm + inv:,.0f}** 万  ·  "
                    f"投资人占比 **{inv_pct:.2f}%**"
                )

            rounds_data.append({
                "name": r_name,
                "investment": inv,
                "pre_money": pm,
                "esop": esop,
            })


# ═══════════════════════════════════════════════════════════════
# 股权计算引擎
# ═══════════════════════════════════════════════════════════════
if len(initial_splits) != len(founder_names):
    st.error("⚠️ 创始人数量与持股比例行数不匹配，请检查输入！")
    st.stop()
if sum(initial_splits) <= 0:
    st.error("⚠️ 初始持股比例之和须大于 0！")
    st.stop()

ownership: dict[str, float] = {}
total_split = sum(initial_splits)
for name, share in zip(founder_names, initial_splits):
    ownership[name] = share / total_split * 100

history: list[dict] = [{
    "round": "初始",
    "ownership": dict(ownership),
    "post_money": 0.0,
}]

for r in rounds_data:
    if r["esop"] > 0:
        esop_key = "ESOP 员工期权"
        current_esop = ownership.get(esop_key, 0.0)
        target = r["esop"]
        if current_esop < target:
            e = target / 100
            c = current_esop / 100
            dilution = (1 - e) / (1 - c) if c < 1 else 0.0
            for key in list(ownership.keys()):
                ownership[key] *= dilution
            ownership[esop_key] = target

    if r["investment"] > 0 and r["pre_money"] > 0:
        inv_pct = r["investment"] / (r["pre_money"] + r["investment"]) * 100
        dilution = 1 - inv_pct / 100
        for key in list(ownership.keys()):
            ownership[key] *= dilution
        ownership[f"{r['name']} 投资人"] = inv_pct
    elif r["investment"] > 0 and r["pre_money"] == 0:
        for key in list(ownership.keys()):
            ownership[key] = 0.0
        ownership[f"{r['name']} 投资人"] = 100.0

    history.append({
        "round": r["name"],
        "ownership": dict(ownership),
        "post_money": r["pre_money"] + r["investment"],
    })

all_entity_names: list[str] = []
for h in history:
    for name in h["ownership"]:
        if name not in all_entity_names:
            all_entity_names.append(name)
cmap = build_color_map(all_entity_names, founder_names)


# ═══════════════════════════════════════════════════════════════
# 主区域
# ═══════════════════════════════════════════════════════════════
st.title("📊 融资股权稀释分析")
st.markdown("左侧调整融资参数，右侧实时更新股权结构、稀释曲线与持股价值。")

# 1. 各轮投资后股权结构 — 甜甜圈饼图
st.subheader("🔄 各轮投资后股权结构")

n_stages = len(history)
per_row = min(4, n_stages)

for row_start in range(0, n_stages, per_row):
    row_items = history[row_start : row_start + per_row]
    cols = st.columns(len(row_items))
    for idx, h in enumerate(row_items):
        with cols[idx]:
            labels = list(h["ownership"].keys())
            values = list(h["ownership"].values())
            colors = [cmap.get(l, "#999999") for l in labels]

            fig = go.Figure(go.Pie(
                labels=labels, values=values, hole=0.38, sort=False,
                marker_colors=colors, marker_line_width=1, marker_line_color="#ffffff",
                textinfo="label+percent", textposition="inside",
                textfont_size=11, insidetextorientation="radial",
                hovertemplate="%{label}<br>%{value:.2f}%<extra></extra>",
            ))
            prefix = "🔹" if h["round"] != "初始" else "🔸"
            fig.update_layout(
                title=dict(text=f"{prefix} {h['round']}后", font_size=14),
                showlegend=False, margin=dict(t=42, b=4, l=4, r=4), height=340,
            )
            st.plotly_chart(fig, use_container_width=True)

# 2. 股权演变 — 堆叠条形图
st.subheader("📊 股权结构演变")

stage_labels = [h["round"] for h in history]
fig_stack = go.Figure()
for name in all_entity_names:
    values = [h["ownership"].get(name, 0) for h in history]
    fig_stack.add_trace(go.Bar(
        name=name, x=stage_labels, y=values,
        marker_color=cmap.get(name, "#999999"), marker_line_width=0,
        hovertemplate=f"{name}<br>%{{x}}后: %{{y:.2f}}%<extra></extra>",
    ))
fig_stack.update_layout(
    barmode="stack",
    yaxis=dict(title="持股比例 (%)", ticksuffix="%", range=[0, 100]),
    xaxis=dict(title="融资阶段"),
    legend=dict(orientation="h", yanchor="bottom", y=1.08, font_size=11),
    margin=dict(t=30, b=40), height=380, bargap=0.25,
)
st.plotly_chart(fig_stack, use_container_width=True)

# 3. 创始人稀释轨迹 & 持股价值
st.subheader("📈 创始人：持股比例 vs 持股价值")

fig_dual = make_subplots(
    rows=1, cols=2,
    subplot_titles=("持股比例（%）", "持股价值（万元）"),
    horizontal_spacing=0.14,
)

for founder in founder_names:
    pcts = [h["ownership"].get(founder, 0) for h in history]
    vals = [h["ownership"].get(founder, 0) / 100 * h["post_money"] for h in history]
    color = cmap.get(founder, "#999999")

    fig_dual.add_trace(go.Scatter(
        x=stage_labels, y=pcts, name=founder,
        mode="lines+markers+text",
        text=[f"{v:.1f}%" for v in pcts], textposition="top center",
        line_width=2.5, marker_size=8, line_color=color, marker_color=color,
        hovertemplate=f"{founder}<br>%{{x}}后: %{{y:.2f}}%<extra></extra>",
    ), row=1, col=1)

    fig_dual.add_trace(go.Scatter(
        x=stage_labels, y=vals, name=founder,
        mode="lines+markers+text",
        text=[f"{v:,.0f}" for v in vals], textposition="top center",
        line_width=2.5, marker_size=8, line_color=color, marker_color=color,
        showlegend=False,
        hovertemplate=f"{founder}<br>%{{x}}后: %{{y:,.0f}} 万元<extra></extra>",
    ), row=1, col=2)

fig_dual.update_yaxes(title_text="%", rangemode="tozero", row=1, col=1)
fig_dual.update_yaxes(title_text="万元", rangemode="tozero", row=1, col=2)
fig_dual.update_xaxes(title_text="融资阶段", row=1, col=1)
fig_dual.update_xaxes(title_text="融资阶段", row=1, col=2)
fig_dual.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=1.12, font_size=11),
    margin=dict(t=55, b=40), height=380,
)
st.plotly_chart(fig_dual, use_container_width=True)

# 稀释洞察
if len(founder_names) > 0 and len(history) > 1:
    initial_total = sum(history[0]["ownership"].get(f, 0) for f in founder_names)
    final_total = sum(history[-1]["ownership"].get(f, 0) for f in founder_names)
    final_val = sum(
        history[-1]["ownership"].get(f, 0) / 100 * history[-1]["post_money"]
        for f in founder_names
    )
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("创始人初始合计", f"{initial_total:.1f}%")
    col_b.metric("创始人最终合计", f"{final_total:.1f}%", delta=f"{final_total - initial_total:.1f}%")
    col_c.metric("创始人持股价值", f"{final_val:,.0f} 万元")

# 4. 最终持股明细表
st.subheader("📋 最终持股明细")

final_h = history[-1]
pm_final = final_h["post_money"]

rows = []
for name, pct in final_h["ownership"].items():
    val = pct / 100 * pm_final
    category = "创始人" if name in founder_names else ("ESOP" if "ESOP" in name or "期权" in name else "投资人")
    rows.append({
        "类别": category, "股东": name, "持股比例": pct,
        "持股价值（万元）": val if pm_final > 0 else 0,
    })

df_final = pd.DataFrame(rows)
df_final = df_final.sort_values("持股比例", ascending=False).reset_index(drop=True)
df_final["持股比例"] = df_final["持股比例"].apply(lambda x: f"{x:.2f}%")
df_final["持股价值（万元）"] = df_final["持股价值（万元）"].apply(
    lambda x: f"{x:,.2f}" if x > 0 else "—"
)
st.dataframe(df_final, use_container_width=True, hide_index=True)

# 5. 各轮融资摘要
st.subheader("📑 各轮融资摘要")

summary_rows = []
for i, h in enumerate(history):
    if h["round"] == "初始":
        continue
    prev = history[i - 1]
    f_before = sum(prev["ownership"].get(f, 0) for f in founder_names)
    f_after  = sum(h["ownership"].get(f, 0) for f in founder_names)
    esop_before = prev["ownership"].get("ESOP 员工期权", 0)
    esop_after  = h["ownership"].get("ESOP 员工期权", 0)
    inv_name = f"{h['round']} 投资人"
    inv_pct  = h["ownership"].get(inv_name, 0)
    summary_rows.append({
        "轮次": h["round"],
        "Post-money（万元）": h["post_money"],
        "投资人占比": inv_pct,
        "ESOP（轮前）": esop_before,
        "ESOP（轮后）": esop_after,
        "创始人合计（轮前）": f_before,
        "创始人合计（轮后）": f_after,
        "创始人本轮稀释": f_before - f_after,
    })

if summary_rows:
    df_summary = pd.DataFrame(summary_rows)
    df_display = df_summary.copy()
    df_display["Post-money（万元）"] = df_display["Post-money（万元）"].apply(lambda x: f"{x:,.0f}")
    for col in ["投资人占比", "ESOP（轮前）", "ESOP（轮后）", "创始人合计（轮前）", "创始人合计（轮后）"]:
        df_display[col] = df_display[col].apply(lambda x: f"{x:.2f}%")
    df_display["创始人本轮稀释"] = df_display["创始人本轮稀释"].apply(lambda x: f"−{x:.2f}%")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

# 6. 持股价值追踪
st.subheader("💰 持股价值变化追踪")

value_rows = []
for h in history:
    row: dict[str, str] = {"融资阶段": h["round"]}
    row["Post-money（万元）"] = f"{h['post_money']:,.0f}" if h["post_money"] > 0 else "—"
    for name in all_entity_names:
        pct = h["ownership"].get(name, 0)
        val = pct / 100 * h["post_money"]
        row[f"{name}（%）"] = f"{pct:.2f}"
        row[f"{name}（万元）"] = f"{val:,.0f}" if h["post_money"] > 0 else "—"
    value_rows.append(row)

df_value = pd.DataFrame(value_rows)
st.dataframe(df_value, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "💡 **计算逻辑**：每轮投资前先将 ESOP 池扩容至目标比例（仅当当前池不足时），"
    "再按 Pre-money 估值引入投资人。所有现有股东按比例稀释。"
    "  ·  🔴 创始人暖色  🔵 投资人冷色  🟡 ESOP 金色"
)
