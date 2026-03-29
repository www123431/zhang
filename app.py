import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime, timedelta

# ==========================================
# 1. 核心认证配置 (精简唯一逻辑版)
# ==========================================
def init_connection():
    # 采用显式拼接，确保 Base64 每一行都完美对齐，不受系统换行符干扰
    PRIVATE_KEY_FIXED = (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDTi7w+YNRB6m4r\n"
        "lY6rWCtOaweykWi4YRg17cMYh0gk8EwXIORJQzPQugSYJcu9+pAlEBm2RdzECjcV\n"
        "jZ4xnleSi7KsoR87cBgz06PO9qL2Zx+GKaYLgtpF8iicJTganRbRlaGRp1EQUcxN\n"
        "wKgm+gPYV/KhYEmk3d1SAph7+21KlBHz1/h/LrXtGTEhlkiZrqUmB6I8f47LX4ek\n"
        "xtJY/hWRu1vVS/Q134m+uQpXQAfbIQg9MimiZgFPxVuTqwgjdphcygI5665r/o5x\n"
        "jE9VSzWZgCgdZ9AyOfR5qaTc+T82IpDqjnnBl88ouVzQZ2TOlgY5nDO8d8Ojh7ky\n"
        "VVt/+5ApAgMBAAECggEAANs/izo04PuJtkucFa5zeW7Gci2AYMIeErM4WQHZZv97\n"
        "Wi4eYnulfggDKZltX4+zWot1kTB4XimDUzpJxhfNV4Kd7SQKjNqHGVs3Ku9PPFbK\n"
        "4/RvKS8enCeIpmfIeDCDeMLlpS6jjdpI7Mko6erh9Fo+mUyBa9ItBm5ltX3KEahx\n"
        "kZPhFlOGoH6NuGHdZuIoKJEwg0/apQnN1oDMbzE5lr8m7/XHbTsurA3P1ejTNieP\n"
        "HrFGuLhPg+JZEay2lf4uZ5HkkppfeW0qM8pKOFXGqPMZ2V+YFrWjzzfCvtfSKrqE\n"
        "ZLuSevlVacJIznOPwlwl+4vP1bwtcqJWponSAI99cQKBgQD1oT1tL1gFMvj2gZ/K\n"
        "ZIlY9qFN25xP/eItwRunm/3yCuY5/oEYJrGVn06lkT3qJsrMds02L4qxl/nX7dgv\n"
        "xcS5HhXkvRSJVKOASqa85OxmSpKtj6ODNKkljLytBUX8ByacFC9XObaR23HO4sZ2\n"
        "vcgFVwTWHYWH9cJeDXNcRkY1UQKBgQDceh3SiXOxdI33lMLEmGu3NmvGsC6qm8Cs\n"
        "NWejpLOMKxuU+4/MlnGDrqO9ftDdMxMg4M+aIYM13WlirRnrrmmVMPT16JIVStdT\n"
        "LrIJ9dZus5+wRcuS3de08Hnle4pwggymtVvE972+yuG/V6xBuM1630STSzus0iKT\n"
        "ZLATKwzXWQKBgQDznvXW2lM57OGDVPOQgQC87Pj1yPCTYiM38EUmi5BmxaqtMKEH\n"
        "vDD8TqJpktHO8KTKALbunF66YBrcsLlwQH4qgQ2D7ol04C6+asxPo9yZZnRukn3B\n"
        "/7QYWyszjHxqSQlhWp/Nqp9KsVWCtefUE81Uhod0eplbTUR3lm2pwsWV0QKBgQCe\n"
        "EYcUDKu/jDrESAkjfcusPP4kIugyNRx72oYFUu3PDpDlzT2Zhjq4GBsYnrUMAbQz\n"
        "HDp63I//rFAECOrOh+r2pXTaYPVrAo9B+fZ3IaOtFmbksAV1tEsUVFxwZJQqeXKs\n"
        "itXSb3PAOCCFWEwNinr3Ht9BYuzTyIw1dDiwZWr9cQKBgCQ633Y6RLRNzZJjJEOJ\n"
        "RUA4x/rfCKi4aYQebHSXVvEzpeEKnXUyxF/pHeH0VOxW7kJUuM9DpFaP4q6AOnXN\n"
        "wNxQkrHH+PBES5EQzG2EUeovYlvLLxuic380ZoSbgSWSrP1d+eOZGvLLTXyeSOvn\n"
        "JARBJCgKNIPGN8YJcdINsAWH\n"
        "-----END PRIVATE KEY-----"
    )

    creds_dict = {
        "type": "service_account",
        "project_id": "mom-english-bot",
        "private_key": PRIVATE_KEY_FIXED,
        "client_email": "mom-helper-41@mom-english-bot.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证初始化失败: {e}")
        st.stop()

# 初始化客户端
gc = init_connection()

# --- 业务逻辑 ---
SHEET_NAME = "Mom_English_Study"
AI_API_KEY = st.secrets["AI_API_KEY"]
WX_APPID = st.secrets["WX_APPID"]
WX_SECRET = st.secrets["WX_SECRET"]
WX_TOUSER = st.secrets["WX_TOUSER"]
WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]

# 词库
WORDS_POOL = {
    "入门级": ["Water", "Food", "Family", "Son", "Daughter", "Help", "Walk", "Park", "Friend", "Money"],
    "进阶级": ["Market", "Supermarket", "Vegetable", "Fruit", "Kitchen", "Cook", "Drink", "Breakfast"],
    "挑战级": ["Medicine", "Hospital", "Doctor", "Price", "Cheap", "Expensive", "Telephone"]
}

def get_data():
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        return pd.DataFrame(data), worksheet
    except Exception as e:
        st.error(f"📊 表格读取失败: {e}")
        return pd.DataFrame(columns=["date", "words"]), None

def get_review_words(df):
    if df.empty: return []
    today = datetime.now().date()
    df['date_dt'] = pd.to_datetime(df['date']).dt.date
    targets = [today - timedelta(days=1), today - timedelta(days=4)]
    review_list = df[df['date_dt'].isin(targets)]['words'].tolist()
    all_words = []
    for s in review_list:
        all_words.extend([w.strip() for w in str(s).split(",")])
    return list(set(all_words))

# UI 渲染
st.set_page_config(page_title="Mom's English Helper", page_icon="👵")
st.title("👵 妈妈英语全自动助手")

df, worksheet = get_data()

with st.sidebar:
    st.header("📈 学习看板")
    st.metric("坚持天数", len(df))
    level = st.radio("难度选择", list(WORDS_POOL.keys()))

today_new = random.sample(WORDS_POOL[level], 3)
today_review = get_review_words(df)

col1, col2 = st.columns(2)
with col1:
    st.subheader("🆕 今日新词")
    for w in today_new: st.write(f"- **{w}**")
with col2:
    st.subheader("🔄 记忆复习")
    if today_review:
        for w in today_review[:3]: st.write(f"- {w}")
    else:
        st.write("暂无任务")

if st.button("🚀 生成并推送给妈妈"):
    with st.spinner("AI 老师正在备课..."):
        try:
            # 1. AI 文案
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"今日单词：{today_new}，复习单词：{today_review}。为老人家写微信推送，含音标、中文、简单例句。200字内。"
            ai_res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
            push_content = ai_res.choices[0].message.content

            # 2. 微信推送
            token = requests.get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}").json().get("access_token")
            payload = {
                "touser": WX_TOUSER,
                "template_id": WX_TEMPLATE_ID,
                "data": {"content": {"value": push_content}}
            }
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}", json=payload).json()

            if wx_res.get("errcode") == 0:
                worksheet.append_row([datetime.now().strftime("%Y-%m-%d"), ",".join(today_new)])
                st.success("✅ 已同步至云端并推送成功！")
                st.balloons()
                st.info(push_content)
            else:
                st.error(f"微信接口反馈: {wx_res}")
        except Exception as e:
            st.error(f"流程执行失败: {e}")

st.divider()
st.caption("Postgraduate Business Analytics Project ❤️")
