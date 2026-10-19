# 🧰 融资计算工具箱

面向金融从业者 & 投资人的一套融资谈判计算工具，基于 Streamlit 构建。

## 🔗 在线访问

👉 [融资计算工具箱](https://finance-toolkit.streamlit.app)

## 🛠️ 功能模块

| 模块 | 功能 |
|------|------|
| 📊 股权稀释计算 | 多轮融资下创始人股权稀释模拟，甜甜圈饼图 + 堆叠条形图 + 稀释曲线 |
| 🎯 对赌 / 业绩承诺 | 输入业绩目标与补偿条款，模拟不同完成率下双方付出 |
| ⭐ 期权池 & ESOP | 计算期权池扩大对估值与稀释的影响，评估员工期权真实价值 |
| 💎 VC 估值（倒推法） | 目标回报 + 退出估值 + 预期稀释，倒推今天可接受的投前估值 |

## 🚀 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

或使用启动脚本（Windows）：

```bash
启动融资工具箱.bat
```

## 📦 部署到 Streamlit Community Cloud

1. 将本仓库推到 GitHub
2. 前往 [share.streamlit.io](https://share.streamlit.io) 用 GitHub 登录
3. 选择仓库 → 自动部署 → 获得 `xxx.streamlit.app` 链接

## 📄 License

MIT
