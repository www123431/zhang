import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import requests
import json
import time

# ==========================================
# 1. 核心认证逻辑 (使用 r"" 原始字符串解决 Unicode 报错)
# ==========================================
def init_connection():
    # 注意：下面的 private_key 前面加了字母 r，这是解决 SyntaxError 的关键
    creds_dict = {
        "type": "service_account",
        "project_id": "mom-english-bot",
        "private_key_id": "a382217610ed812f73cc6d6c2d9c49981f8c3d00",
        "private_key": r"-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDTi7w+YNRB6m4r\nlY6rWCtOaweykWi4YRg17cMYh0gk8EwXIORJQzPQugSYJcu9+pAlEBm2RdzECjcV\njZ4xnleSi7KsoR87cBgz06PO9qL2Zx+GKaYLgtpF8iicJTganRbRlaGRp1EQUcxN\nwKgm+gPYV/KhYEmk3d1SAph7+21KlBHz1/h/LrXtGTEhlkiZrqUmB6I8f47LX4ek\nxtJY/hWRu1vVS/Q134m+uQpXQAfbIQg9MimiZgFPxVuTqwgjdphcygI5665r/o5x\njE9VSzWZgCgdZ9AyOfR5qaTc+T82IpDqjnnBl88ouVzQZ2TOlgY5nDO8d8Ojh7ky\nVVt/+5ApAgMBAAECggEAANs/izo04PuJtkucFa5zeW7Gci2AYMIeErM4WQHZZv97\nWi4eYnulfggDKZltX4+zWot1kTB4XimDUzpJxhfNV4Kd7SQKjNqHGVs3Ku9PPFbK\n4/RvKS8enCeIpmfIeDCDeMLlpS6jjdpI7Mko6erh9Fo+mUyBa9ItBm5ltX3KEahx\nkZPhFlOGoH6NuGHdZuIoKJEwg0/apQnN1oDMbzE5lr8m7/XHbTsurA3P1ejTNieP\nHrFGuLhPg+JZEay2lf4uZ5HkkppfeW0qM8pKOFXGqPMZ2V+YFrWjzzfCvtfSKrqE\nZLuSevlVacJIznOPwlwl+4vP1bwtcqJWponSAI99cQKBgQD1oT1tL1gFMvj2gZ/K\nZIlY9qFN25xP/eItwRunm/3yCuY5/oEYJrGVn06lkT3qJsrMds02L4qxl/nX7dgv\xcS5HhXkvRSJVKOASqa85OxmSpKtj6ODNKkljLytBUX8ByacFC9XObaR23HO4sZ2\vcgFVwTWHYWH9cJeDXNcRkY1UQKBgQDceh3SiXOxdI33lMLEmGu3NmvGsC6qm8Cs\nNWejpLOMKxuU+4/MlnGDrqO9ftDdMxMg4M+aIYM13WlirRnrrmmVMPT16JIVStdT\nLrIJ9dZus5+wRcuS3de08Hnle4pwggymtVvE972+yuG/V6xBuM1630STSzus0iKT\nZLATKwzXWQKBgQDznvXW2lM57OGDVPOQgQC87Pj1yPCTYiM38EUmi5BmxaqtMKEH\nvDD8TqJpktHO8KTKALbunF66YBrcsLlwQH4qgQ2D7ol04C6+asxPo9yZZnRukn3B\n/7QYWyszjHxqSQlhWp/Nqp9KsVWCtefUE81Uhod0eplbTUR3lm2pwsWV0QKBgQCe\nEYcUDKu/jDrESAkjfcusPP4kIugyNRx72oYFUu3PDpDlzT2Zhjq4GBsYnrUMAbQz\nHDp63I//rFAECOrOh+r2pXTaYPVrAo9B+fZ3IaOtFmbksAV1tEsUVFxwZJQqeXKs\nitXSb3PAOCCFWEwNinr3Ht9BYuzTyIw1dDiwZWr9cQKBgCQ633Y6RLRNzZJjJEOJ\nRUA4x/rfCKi4aYQebHSXVvEzpeEKnXUyxF/pHeH0VOxW7kJUuM9DpFaP4q6AOnXN\nwNxQkrHH+PBES5EQzG2EUeovYlvLLxuic380ZoSbgSWSrP1d+eOZGvLLTXyeSOvn\nJARBJCgKNIPGN8YJcdINsAWH\n-----END PRIVATE KEY-----\n",
        "client_email": "mom-helper-41@mom-english-bot.iam.gserviceaccount.com",
        "client_id": "112440344508636174830",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mom-helper-41%40mom-english-bot.iam.gserviceaccount.com"
    }
    
    # 将 raw string 里的 \n 替换回真正的换行符
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace(r"\n", "\n")
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证连接失败: {e}")
        st.stop()

# ==========================================
# 2. 基础配置 (从 Streamlit Secrets 读取)
# ==========================================
# 请确保在 Streamlit Cloud 的 Settings -> Secrets 里填好了这些 Key
AI_API_KEY = st.secrets.get("AI_API_KEY", "")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "123456")
WX_APPID = st.secrets.get("WX_APPID", "")
WX_SECRET = st.secrets.get("WX_SECRET", "")
WX_TOUSER = st.secrets.get("WX_TOUSER", "")
WX_TEMPLATE_ID = st.secrets.get("WX_TEMPLATE_ID", "")

# ==========================================
# 3. 页面逻辑与展示
# ==========================================
st.set_page_config(page_title="妈妈英语助手", layout="centered")
st.title("👵 妈妈英语全自动助手")

# 初始化 Google 表格连接
gc = init_connection()

try:
    # 请确保你的 Google Sheet 名字叫 Mom_English_Study
    sh = gc.open("Mom_English_Study")
    worksheet = sh.get_worksheet(0)
    st.success("✅ 认证成功！已成功连接到 Google 表格。")

    # 显示表格内容
    st.subheader("📊 学习计划概览")
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("💡 目前表格中还没有数据，准备好开始今天的学习了吗？")

except Exception as e:
    st.error(f"📊 无法打开表格: {e}")
    st.markdown(f"**请检查**：是否已将表格共享给 `{creds_dict['client_email']}`？")

# 测试推送按钮
if st.button("🚀 测试 AI 生成并推送"):
    with st.spinner("正在连接 DeepSeek 并模拟推送..."):
        time.sleep(2)
        st.write("今日单词预选：'Resilience' (韧性)")
        st.success("推送逻辑已就绪。")
