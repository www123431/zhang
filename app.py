import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime, timedelta

# ==========================================
# 1. 核心认证配置 (解决 InvalidByte 报错)
# ==========================================
def init_connection():
    # 纯净的私钥主体，不带任何 \n 或反斜杠
    KEY_BODY = (
        "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDTi7w+YNRB6m4r"
        "lY6rWCtOaweykWi4YRg17cMYh0gk8EwXIORJQzPQugSYJcu9+pAlEBm2RdzECjcV"
        "jZ4xnleSi7KsoR87cBgz06PO9qL2Zx+GKaYLgtpF8iicJTganRbRlaGRp1EQUcxN"
        "wKgm+gPYV/KhYEmk3d1SAph7+21KlBHz1/h/LrXtGTEhlkiZrqUmB6I8f47LX4ek"
        "xtJY/hWRu1vVS/Q134m+uQpXQAfbIQg9MimiZgFPxVuTqwgjdphcygI5665r/o5x"
        "jE9VSzWZgCgdZ9AyOfR5qaTc+T82IpDqjnnBl88ouVzQZ2TOlgY5nDO8d8Ojh7ky"
        "VVt/+5ApAgMBAAECggEAANs/izo04PuJtkucFa5zeW7Gci2AYMIeErM4WQHZZv97"
        "Wi4eYnulfggDKZltX4+zWot1kTB4XimDUzpJxhfNV4Kd7SQKjNqHGVs3Ku9PPFbK"
        "4/RvKS8enCeIpmfIeDCDeMLlpS6jjdpI7Mko6erh9Fo+mUyBa9ItBm5ltX3KEahx"
        "kZPhFlOGoH6NuGHdZuIoKJEwg0/apQnN1oDMbzE5lr8m7/XHbTsurA3P1ejTNieP"
        "HrFGuLhPg+JZEay2lf4uZ5HkkppfeW0qM8pKOFXGqPMZ2V+YFrWjzzfCvtfSKrqE"
        "ZLuSevlVacJIznOPwlwl+4vP1bwtcqJWponSAI99cQKBgQD1oT1tL1gFMvj2gZ/K"
        "ZIlY9qFN25~省略~" # 这里请补全你 JSON 文件中 private_key 的主体部分
        "JARBJCgKNIPGN8YJcdINsAWH"
    )

    # 强制重建 PEM 格式：每 64 个字符换一行
    lines = [KEY_BODY[i:i+64] for i in range(0, len(KEY_BODY), 64)]
    FIXED_KEY = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(lines) + "\n-----END PRIVATE KEY-----\n"

    creds_info = {
        "type": "service_account",
        "project_id": "mom-english-bot",
        "private_key": FIXED_KEY,
        "client_email": "mom-helper-41@mom-english-bot.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    try:
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证最终尝试失败: {e}")
        st.stop()

# 初始化全局连接
gc = init_connection()

# ==========================================
# 2. 业务参数 (来自 Streamlit Secrets)
# ==========================================
SHEET_NAME = "Mom_English_Study"
AI_API_KEY = st.secrets["AI_API_KEY"]
WX_APPID = st.secrets["WX_APPID"]
WX_SECRET = st.secrets["WX_SECRET"]
WX_TOUSER = st.secrets["WX_TOUSER"]
WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]

# ==========================================
# 3. 数据与 UI 逻辑 (保持不变)
# ==========================================
def get_data():
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.get_worksheet(0)
        return pd.DataFrame(worksheet.get_all_records()), worksheet
    except Exception as e:
        st.error(f"📊 表格读取失败: {e}")
        return pd.DataFrame(), None

st.title("👵 妈妈英语学习助手")
df, worksheet = get_data()

# 示例词库
WORDS_POOL = ["Water", "Food", "Family", "Apple", "Banana", "Park", "Money"]

if st.button("🚀 生成课件并推送"):
    with st.spinner("AI 正在备课..."):
        try:
            today_words = random.sample(WORDS_POOL, 3)
            # 1. AI 文案 (DeepSeek)
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": f"帮妈妈写英语单词推送：{today_words}"}]
            )
            push_content = res.choices[0].message.content

            # 2. 微信推送
            token = requests.get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}").json().get("access_token")
            payload = {"touser": WX_TOUSER, "template_id": WX_TEMPLATE_ID, "data": {"content": {"value": push_content}}}
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}", json=payload).json()

            if wx_res.get("errcode") == 0:
                worksheet.append_row([datetime.now().strftime("%Y-%m-%d"), ",".join(today_words)])
                st.success("✅ 发送成功！内容已同步至 Google Sheets。")
                st.write(push_content)
        except Exception as e:
            st.error(f"推送过程出错: {e}")
