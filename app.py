import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import requests
import json
import time

# ==========================================
# 1. 核心认证逻辑 (硬编码 JSON，解决 PEM 报错)
# ==========================================
def init_connection():
    # 这里的资料直接来自你的 mom-english-bot-a382217610ed.json
    creds_dict = {
        "type": "service_account",
        "project_id": "mom-english-bot",
        "private_key_id": "a382217610ed812f73cc6d6c2d9c49981f8c3d00",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDTi7w+YNRB6m4r\nlY6rWCtOaweykWi4YRg17cMYh0gk8EwXIORJQzPQugSYJcu9+pAlEBm2RdzECjcV\njZ4xnleSi7KsoR87cBgz06PO9qL2Zx+GKaYLgtpF8iicJTganRbRlaGRp1EQUcxN\nwKgm+gPYV/KhYEmk3d1SAph7+21KlBHz1/h/LrXtGTEhlkiZrqUmB6I8f47LX4ek\nxtJY/hWRu1vVS/Q134m+uQpXQAfbIQg9MimiZgFPxVuTqwgjdphcygI5665r/o5x\njE9VSzWZgCgdZ9AyOfR5qaTc+T82IpDqjnnBl88ouVzQZ2TOlgY5nDO8d8Ojh7ky\nVVt/+5ApAgMBAAECggEAANs/izo04PuJtkucFa5zeW7Gci2AYMIeErM4WQHZZv97\nWi4eYnulfggDKZltX4+zWot1kTB4XimDUzpJxhfNV4Kd7SQKjNqHGVs3Ku9PPFbK\n4/RvKS8enCeIpmfIeDCDeMLlpS6jjdpI7Mko6erh9Fo+mUyBa9ItBm5ltX3KEahx\nkZPhFlOGoH6NuGHdZuIoKJEwg0/apQnN1oDMbzE5lr8m7/XHbTsurA3P1ejTNieP\nHrFGuLhPg+JZEay2lf4uZ5HkkppfeW0qM8pKOFXGqPMZ2V+YFrWjzzfCvtfSKrqE\nZLuSevlVacJIznOPwlwl+4vP1bwtcqJWponSAI99cQKBgQD1oT1tL1gFMvj2gZ/K\nZIlY9qFN25xP/eItwRunm/3yCuY5/oEYJrGVn06lkT3qJsrMds02L4qxl/nX7dgv\xcS5HhXkvRSJVKOASqa85OxmSpKtj6ODNKkljLytBUX8ByacFC9XObaR23HO4sZ2\vcgFVwTWHYWH9cJeDXNcRkY1UQKBgQDceh3SiXOxdI33lMLEmGu3NmvGsC6qm8Cs\nNWejpLOMKxuU+4/MlnGDrqO9ftDdMxMg4M+aIYM13WlirRnrrmmVMPT16JIVStdT\nLrIJ9dZus5+wRcuS3de08Hnle4pwggymtVvE972+yuG/V6xBuM1630STSzus0iKT\nZLATKwzXWQKBgQDznvXW2lM57OGDVPOQgQC87Pj1yPCTYiM38EUmi5BmxaqtMKEH\nvDD8TqJpktHO8KTKALbunF66YBrcsLlwQH4qgQ2D7ol04C6+asxPo9yZZnRukn3B\n/7QYWyszjHxqSQlhWp/Nqp9KsVWCtefUE81Uhod0eplbTUR3lm2pwsWV0QKBgQCe\nEYcUDKu/jDrESAkjfcusPP4kIugyNRx72oYFUu3PDpDlzT2Zhjq4GBsYnrUMAbQz\nHDp63I//rFAECOrOh+r2pXTaYPVrAo9B+fZ3IaOtFmbksAV1tEsUVFxwZJQqeXKs\nitXSb3PAOCCFWEwNinr3Ht9BYuzTyIw1dDiwZWr9cQKBgCQ633Y6RLRNzZJjJEOJ\nRUA4x/rfCKi4aYQebHSXVvEzpeEKnXUyxF/pHeH0VOxW7kJUuM9DpFaP4q6AOnXN\nwNxQkrHH+PBES5EQzG2EUeovYlvLLxuic380ZoSbgSWSrP1d+eOZGvLLTXyeSOvn\nJARBJCgKNIPGN8YJcdINsAWH\n-----END PRIVATE KEY-----\n",
        "client_email": "mom-helper-41@mom-english-bot.iam.gserviceaccount.com",
        "client_id": "112440344508636174830",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mom-helper-41%40mom-english-bot.iam.gserviceaccount.com"
    }
    
    # 关键点：强制转换 \n 字符，修复 Unable to load PEM file 报错
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证连接失败: {e}")
        st.stop()

# ==========================================
# 2. 从 Streamlit Secrets 读取简单配置
# ==========================================
# 剩下的简单字符串建议依然放在 Secrets 面板
try:
    AI_API_KEY = st.secrets.get("AI_API_KEY", "YOUR_DEFAULT_API_KEY")
    WX_APPID = st.secrets.get("WX_APPID", "")
    WX_SECRET = st.secrets.get("WX_SECRET", "")
    WX_TOUSER = st.secrets.get("WX_TOUSER", "")
    WX_TEMPLATE_ID = st.secrets.get("WX_TEMPLATE_ID", "")
except Exception:
    st.warning("⚠️ 发现部分 Secrets 未配置，请前往 Settings -> Secrets 检查。")

# ==========================================
# 3. 业务逻辑与 UI 界面
# ==========================================
st.set_page_config(page_title="妈妈英语助手", layout="centered")
st.title("👵 妈妈英语全自动助手")

# 初始化 Google 表格
gc = init_connection()

try:
    # 确保你的 Google 表格叫 "Mom_English_Study"
    # 并且已经给 mom-helper-41@mom-english-bot.iam.gserviceaccount.com 开启了共享权限
    sh = gc.open("Mom_English_Study")
    worksheet = sh.get_worksheet(0)
    st.success("✅ 认证成功！已成功连接到 Google Sheets 表格。")

    # 展示数据
    st.subheader("📊 学习计划概览")
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("💡 目前表格中还没有单词，点击下方按钮开始生成吧！")

except Exception as e:
    st.error(f"📊 无法打开表格: {e}")
    st.markdown("""
    **排查建议：**
    1. 确认 Google Sheet 的名字完全匹配 `Mom_English_Study`。
    2. 确认你已经把表格 **Share** 给了邮箱：`mom-helper-41@mom-english-bot.iam.gserviceaccount.com`。
    """)

# 功能测试按钮
if st.button("🚀 测试 AI 推送内容"):
    with st.spinner("正在通过 DeepSeek 生成并发送微信提醒..."):
        time.sleep(2) # 模拟处理
        st.write("今日内容：Apple - 苹果 🍎")
        st.success("推送指令已下发（逻辑待进一步完善）")
