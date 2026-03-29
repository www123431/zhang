import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime, timedelta

# ==========================================
# 1. 核心认证配置 (包含完整私钥主体)
# ==========================================
def init_connection():
    # 这是从你上传的 JSON 中提取的完整私钥，去掉了所有换行符
    # 确保这一串字符中间没有任何空格、波浪号或省略号
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
        "ZIlY9qFN25xP/eItwRunm/3yCuY5/oEYJrGVn06lkT3qJsrMds02L4qxl/nX7dgv"
        "xcS5HhXkvRSJVKOASqa85OxmSpKtj6ODNKkljLytBUX8ByacFC9XObaR23HO4sZ2"
        "vcgFVwTWHYWH9cJeDXNcRkY1UQKBgQDceh3SiXOxdI33lMLEmGu3NmvGsC6qm8Cs"
        "NWejpLOMKxuU+4/MlnGDrqO9ftDdMxMg4M+aIYM13WlirRnrrmmVMPT16JIVStdT"
        "LrIJ9dZus5+wRcuS3de08Hnle4pwggymtVvE972+yuG/V6xBuM1630STSzus0iKT"
        "ZLATKwzXWQKBgQDznvXW2lM57OGDVPOQgQC87Pj1yPCTYiM38EUmi5BmxaqtMKEH"
        "vDD8TqJpktHO8KTKALbunF66YBrcsLlwQH4qgQ2D7ol04C6+asxPo9yZZnRukn3B"
        "/7QYWyszjHxqSQlhWp/Nqp9KsVWCtefUE81Uhod0eplbTUR3lm2pwsWV0QKBgQCe"
        "EYcUDKu/jDrESAkjfcusPP4kIugyNRx72oYFUu3PDpDlzT2Zhjq4GBsYnrUMAbQz"
        "HDp63I//rFAECOrOh+r2pXTaYPVrAo9B+fZ3IaOtFmbksAV1tEsUVFxwZJQqeXKs"
        "itXSb3PAOCCFWEwNinr3Ht9BYuzTyIw1dDiwZWr9cQKBgCQ633Y6RLRNzZJjJEOJ"
        "RUA4x/rfCKi4aYQebHSXVvEzpeEKnXUyxF/pHeH0VOxW7kJUuM9DpFaP4q6AOnXN"
        "wNxQkrHH+PBES5EQzG2EUeovYlvLLxuic380ZoSbgSWSrP1d+eOZGvLLTXyeSOvn"
        "JARBJCgKNIPGN8YJcdINsAWH"
    )

    # 按照 PEM 标准每 64 字符换行，重建私钥
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
        st.error(f"❌ 认证初始化失败: {e}")
        st.stop()

# 初始化全局连接
gc = init_connection()

# ==========================================
# 2. 业务配置 (从 Streamlit Secrets 读取)
# ==========================================
SHEET_NAME = "Mom_English_Study"
AI_API_KEY = st.secrets["AI_API_KEY"]
WX_APPID = st.secrets["WX_APPID"]
WX_SECRET = st.secrets["WX_SECRET"]
WX_TOUSER = st.secrets["WX_TOUSER"]
WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]

# ==========================================
# 3. 核心功能函数
# ==========================================
def get_data():
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        return pd.DataFrame(data), worksheet
    except Exception as e:
        st.error(f"📊 无法打开 Google Sheet: {e}")
        return pd.DataFrame(), None

# 词库
WORDS_POOL = ["Water", "Family", "Food", "Apple", "Park", "Help", "Money", "Market"]

# ==========================================
# 4. UI 界面
# ==========================================
st.set_page_config(page_title="Mom's English Bot", page_icon="👵")
st.title("👵 妈妈英语全自动助手")

df, worksheet = get_data()

if st.button("🚀 生成课件并推送到微信", use_container_width=True):
    with st.spinner("AI 老师正在备课..."):
        try:
            today_words = random.sample(WORDS_POOL, 3)
            
            # 1. 调用 DeepSeek 生成文案
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"请为妈妈编写今日英语单词：{today_words}。包含中文翻译、音标和生活化短句。语气温柔亲切。"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
            content = res.choices[0].message.content

            # 2. 微信推送
            token = requests.get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}").json().get("access_token")
            payload = {
                "touser": WX_TOUSER,
                "template_id": WX_TEMPLATE_ID,
                "data": {"content": {"value": content}}
            }
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}", json=payload).json()

            if wx_res.get("errcode") == 0:
                # 3. 记录到表格
                worksheet.append_row([datetime.now().strftime("%Y-%m-%d"), ",".join(today_words)])
                st.balloons()
                st.success("✅ 推送成功！妈妈已经收到消息了。")
                st.info(content)
            else:
                st.error(f"微信推送失败: {wx_res}")
        except Exception as e:
            st.error(f"运行出错: {e}")

st.divider()
st.caption("Developed by Business Analytics Student for Mom ❤️")
