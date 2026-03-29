import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime, timedelta

# ==========================================
# 1. 核心认证配置 (直接解析原始私钥)
# ==========================================
def init_connection():
    # 这里直接使用你上传 JSON 里的原始 private_key 字符串
    # 关键点：使用 replace 将字面量的 "\n" 替换为真正的换行符
    RAW_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDTi7w+YNRB6m4r\nlY6rWCtOaweykWi4YRg17cMYh0gk8EwXIORJQzPQugSYJcu9+pAlEBm2RdzECjcV\njZ4xnleSi7KsoR87cBgz06PO9qL2Zx+GKaYLgtpF8iicJTganRbRlaGRp1EQUcxN\nwKgm+gPYV/KhYEmk3d1SAph7+21KlBHz1/h/LrXtGTEhlkiZrqUmB6I8f47LX4ek\nxtJY/hWRu1vVS/Q134m+uQpXQAfbIQg9MimiZgFPxVuTqwgjdphcygI5665r/o5x\njE9VSzWZgCgdZ9AyOfR5qaTc+T82IpDqjnnBl88ouVzQZ2TOlgY5nDO8d8Ojh7ky\nVVt/+5ApAgMBAAECggEAANs/izo04PuJtkucFa5zeW7Gci2AYMIeErM4WQHZZv97\nWi4eYnulfggDKZltX4+zWot1kTB4XimDUzpJxhfNV4Kd7SQKjNqHGVs3Ku9PPFbK\n4/RvKS8enCeIpmfIeDCDeMLlpS6jjdpI7Mko6erh9Fo+mUyBa9ItBm5ltX3KEahx\nkZPhFlOGoH6NuGHdZuIoKJEwg0/apQnN1oDMbzE5lr8m7/XHbTsurA3P1ejTNieP\nHrFGuLhPg+JZEay2lf4uZ5HkkppfeW0qM8pKOFXGqPMZ2V+YFrWjzzfCvtfSKrqE\nZLuSevlVacJIznOPwlwl+4vP1bwtcqJWponSAI99cQKBgQD1oT1tL1gFMvj2gZ/K\nZIlY9qFN25xP/eItwRunm/3yCuY5/oEYJrGVn06lkT3qJsrMds02L4qxl/nX7dgv\nxcS5HhXkvRSJVKOASqa85OxmSpKtj6ODNKkljLytBUX8ByacFC9XObaR23HO4sZ2\nvcgFVwTWHYWH9cJeDXNcRkY1UQKBgQDceh3SiXOxdI33lMLEmGu3NmvGsC6qm8Cs\nNWejpLOMKxuU+4/MlnGDrqO9ftDdMxMg4M+aIYM13WlirRnrrmmVMPT16JIVStdT\nLrIJ9dZus5+wRcuS3de08Hnle4pwggymtVvE972+yuG/V6xBuM1630STSzus0iKT\nZLATKwzXWQKBgQDznvXW2lM57OGDVPOQgQC87Pj1yPCTYiM38EUmi5BmxaqtMKEH\nvDD8TqJpktHO8KTKALbunF66YBrcsLlwQH4qgQ2D7ol04C6+asxPo9yZZnRukn3B\n/7QYWyszjHxqSQlhWp/Nqp9KsVWCtefUE81Uhod0eplbTUR3lm2pwsWV0QKBgQCe\nEYcUDKu/jDrESAkjfcusPP4kIugyNRx72oYFUu3PDpDlzT2Zhjq4GBsYnrUMAbQz\nHDp63I//rFAECOrOh+r2pXTaYPVrAo9B+fZ3IaOtFmbksAV1tEsUVFxwZJQqeXKs\nitXSb3PAOCCFWEwNinr3Ht9BYuzTyIw1dDiwZWr9cQKBgCQ633Y6RLRNzZJjJEOJ\nRUA4x/rfCKi4aYQebHSXVvEzpeEKnXUyxF/pHeH0VOxW7kJUuM9DpFaP4q6AOnXN\nwNxQkrHH+PBES5EQzG2EUeovYlvLLxuic380ZoSbgSWSrP1d+eOZGvLLTXyeSOvn\nJARBJCgKNIPGN8YJcdINsAWH\n-----END PRIVATE KEY-----\n"

    creds_dict = {
        "type": "service_account",
        "project_id": "mom-english-bot",
        "private_key": RAW_PRIVATE_KEY.replace('\\n', '\n'),
        "client_email": "mom-helper-41@mom-english-bot.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证最终尝试失败: {e}")
        st.stop()

# 初始化全局连接
gc = init_connection()

# ==========================================
# 2. 业务配置 (DeepSeek & 微信)
# ==========================================
AI_API_KEY = st.secrets["AI_API_KEY"]
WX_APPID = st.secrets["WX_APPID"]
WX_SECRET = st.secrets["WX_SECRET"]
WX_TOUSER = st.secrets["WX_TOUSER"]
WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]
SHEET_NAME = "Mom_English_Study"

# 词库
WORDS_POOL = {
    "入门级": ["Water", "Food", "Family", "Son", "Daughter", "Help", "Walk", "Park", "Friend", "Money"],
    "进阶级": ["Market", "Supermarket", "Vegetable", "Fruit", "Kitchen", "Cook", "Drink", "Breakfast"],
    "挑战级": ["Medicine", "Hospital", "Doctor", "Price", "Cheap", "Expensive", "Telephone"]
}

# ==========================================
# 3. 功能逻辑
# ==========================================
def get_data():
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        return pd.DataFrame(data), worksheet
    except Exception as e:
        st.error(f"📊 无法打开表格，请确认表格已共享给 client_email: {e}")
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

# ==========================================
# 4. UI 渲染
# ==========================================
st.set_page_config(page_title="Mom's English Helper", page_icon="👵")
st.title("👵 妈妈英语全自动助手")

df, worksheet = get_data()

with st.sidebar:
    st.header("📈 学习看板")
    st.metric("已坚持天数", len(df))
    level = st.radio("选择难度", list(WORDS_POOL.keys()))

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

if st.button("🚀 生成课件并推送到微信"):
    with st.spinner("AI 老师正在备课..."):
        try:
            # AI 生成文案
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"为老人家写微信推送。新词：{today_new}，复习：{today_review}。含音标、中文、简单例句。200字内。"
            ai_res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
            push_content = ai_res.choices[0].message.content

            # 微信推送
            token = requests.get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}").json().get("access_token")
            payload = {
                "touser": WX_TOUSER,
                "template_id": WX_TEMPLATE_ID,
                "data": {"content": {"value": push_content}}
            }
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}", json=payload).json()

            if wx_res.get("errcode") == 0:
                worksheet.append_row([datetime.now().strftime("%Y-%m-%d"), ",".join(today_new)])
                st.success("✅ 发送成功并已记入云端！")
                st.balloons()
                st.info(push_content)
            else:
                st.error(f"微信端报错: {wx_res}")
        except Exception as e:
            st.error(f"运行失败: {e}")

st.divider()
st.caption("Postgraduate Business Analytics Project ❤️")
