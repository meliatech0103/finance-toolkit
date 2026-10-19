"""
融资计算工具箱 — 首页
Streamlit 多页面应用入口
"""

import streamlit as st

st.set_page_config(
    page_title="融资计算工具箱",
    layout="wide",
)

st.title("融资计算工具箱")
st.markdown("---")

st.markdown(
    """
    面向 **金融从业者 & 投资人** 的一套融资谈判计算工具，
    左侧切换页面，调整参数后右侧实时更新图表。

    <br>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        """
        ### 1. 股权稀释计算
        多轮融资下创始人股权稀释模拟，
        甜甜圈饼图 + 堆叠条形图 + 稀释曲线。

        *→ 点击左侧「股权稀释计算」*
        """
    )

with col2:
    st.markdown(
        """
        ### 2. 对赌 / 业绩承诺
        输入业绩目标与补偿条款，
        模拟不同完成率下双方付出。

        *→ 点击左侧「对赌测算」*
        """
    )

with col3:
    st.markdown(
        """
        ### 3. 期权池 & ESOP
        计算期权池扩大对估值与稀释的影响，
        评估员工期权的真实价值。

        *→ 点击左侧「期权池计算」*
        """
    )

with col4:
    st.markdown(
        """
        ### 4. VC 估值（倒推法）
        目标回报 + 退出估值 + 预期稀释，
        倒推今天可接受的投前估值。

        *→ 点击左侧「VC 估值工具」*
        """
    )

st.markdown("---")
st.caption(
    "💡 所有计算均在浏览器本地完成，不收集任何数据。  "
    "如有建议或 Bug 反馈，欢迎提 Issue。"
)
