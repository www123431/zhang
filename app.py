import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime

# ==========================================
# 1. 自动化认证 (使用官方 Secrets 结构)
# ==========================================
def init_connection():
    # 直接从 Secrets 加载完整的字典结构
    creds_info = st.secrets["gcp_service_account"]
    
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    try:
        # 这种方式会自动识别并处理 private_key 里的换行符
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证连接失败: {e}")
        st.info("提示：请检查 Streamlit Secrets 中的格式是否正确。")
        st.stop()

# 执行连接
gc = init_connection()

# ==========================================
# 2. 基础配置
# ==========================================
SHEET_NAME = "Mom_English_Study"
AI_API_KEY = st.secrets["AI_API_KEY"]
WX_APPID = st.secrets["WX_APPID"]
WX_SECRET = st.secrets["WX_SECRET"]
WX_TOUSER = st.secrets["WX_TOUSER"]
WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]

# ==========================================
# 3. 业务逻辑
# ==========================================
def get_data():
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.get_worksheet(0)
        return pd.DataFrame(worksheet.get_all_records()), worksheet
    except Exception as e:
        st.error(f"📊 无法访问 Google 表格: {e}")
        return pd.DataFrame(), None

st.set_page_config(page_title="Mom's English Bot", layout="centered")
st.title("👵 妈妈英语全自动助手")

df, worksheet = get_data()

# 示例词库
WORDS_POOL = ["Water", "Family", "Food", "Apple", "Park", "Help", "Money", "Doctor"]

if st.button("🚀 生成课件并推送到微信", use_container_width=True):
    with st.spinner("AI 老师正在备课..."):
        try:
            today_words = random.sample(WORDS_POOL, 3)
            
            # 1. AI 文案
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": f"帮妈妈写英语课件：{today_words}。包含中文、音标和生活化短句。"}]
            )
            content = res.choices[0].message.content

            # 2. 微信推送
            token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
            token = requests.get(token_url).json().get("access_token")
            payload = {"touser": WX_TOUSER, "template_id": WX_TEMPLATE_ID, "data": {"content": {"value": content}}}
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}", json=payload).json()

            if wx_res.get("errcode") == 0:
                worksheet.append_row([datetime.now().strftime("%Y-%m-%d"), ",".join(today_words)])
                st.balloons()
                st.success("✅ 推送成功！妈妈收到啦。")
                st.write(content)
            else:
                st.error(f"微信报错: {wx_res}")
        except Exception as e:
            st.error(f"运行失败: {e}")
