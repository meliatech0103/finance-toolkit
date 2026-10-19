@echo off
chcp 65001 >nul 2>&1
cd /d "E:\cc for test\finance-toolkit"
echo 正在启动融资计算工具箱...
echo 浏览器将自动打开 http://localhost:8501
start http://localhost:8501
python -m streamlit run app.py --server.port 8501 --server.headless true
pause
