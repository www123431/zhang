import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime

# ==========================================
# 1. 核心认证 (直接把 JSON 内容写进字典，避开文件上传和 Secrets 格式坑)
# ==========================================
def init_connection():
    creds_dict = {
        "type": "service_account",
        "project_id": "mom-english-bot",
        "private_key_id": "a382217610ed812f73cc6d6c2d9c49981f8c3d00",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDTi7w+YNRB6m4r\nlY6rWCtOaweykWi4YRg17cMYh0gk8EwXIORJQzPQugSYJcu9+pAlEBm2RdzECjcV\njZ4xnleSi7KsoR87cBgz06PO9qL2Zx+GKaYLgtpF8iicJTganRbRlaGRp1EQUcxN\nwKgm+gPYV/KhYEmk3d1SAph7+21KlBHz1/h/LrXtGTEhlkiZrqUmB6I8f47LX4ek\nxtJY/hWRu1vVS/Q134m+uQpXQAfbIQg9MimiZgFPxVuTqwgjdphcygI5665r/o5x\njE9VSzWZgCgdZ9AyOfR5qaTc+T82IpDqjnnBl88ouVzQZ2TOlgY5nDO8d8Ojh7ky\nVVt/+5ApAgMBAAECggEAANs/izo04PuJtkucFa5zeW7Gci2AYMIeErM4WQHZZv97\nWi4eYnulfggDKZltX4+zWot1kTB4XimDUzpJxhfNV4Kd7SQKjNqHGVs3Ku9PPFbK\n4/RvKS8enCeIpmfIeDCDeMLlpS6jjdpI7Mko6erh9Fo+mUyBa9ItBm5ltX3KEahx\nkZPhFlOGoH6NuGHdZuIoKJEwg0/apQnN1oDMbzE5lr8m7/XHbTsurA3P1ejTNieP\nHrFGuLhPg+JZEay2lf4uZ5HkkppfeW0qM8pKOFXGqPMZ2V+YFrWjzzfCvtfSKrqE\nZLuSevlVacJIznOPwlwl+4vP1bwtcqJWponSAI99cQKBgQD1oT1tL1gFMvj2gZ/K\nZIlY9qFN25xP/eItwRunm/3yCuY5/oEYJrGVn06lkT3qJsrMds02L4qxl/nX7dgv\nxcS5HhXkvRSJVKOASqa85OxmSpKtj6ODNKkljLytBUX8ByacFC9XObaR23HO4sZ2\vcgFVwTWHYWH9cJeDXNcRkY1UQKBgQDceh3SiXOxdI33lMLEmGu3NmvGsC6qm8Cs\nNWejpLOMKxuU+4/MlnGDrqO9ftDdMxMg4M+aIYM13WlirRnrrmmVMPT16JIVStdT\nLrIJ9dZus5+wRcuS3de08Hnle4pwggymtVvE972+yuG/V6xBuM1630STSzus0iKT\nZLATKwzXWQKBgQDznvXW2lM57OGDVPOQgQC87Pj1yPCTYiM38EUmi5BmxaqtMKEH\nvDD8TqJpktHO8KTKALbunF66YBrcsLlwQH4qgQ2D7ol04C6+asxPo9yZZnRukn3B\n/7QYWyszjHxqSQlhWp/Nqp9KsVWCtefUE81Uhod0eplbTUR3lm2pwsWV0QKBgQCe\nEYcUDKu/jDrESAkjfcusPP4kIugyNRx72oYFUu3PDpDlzT2Zhjq4GBsYnrUMAbQz\nHDp63I//rFAECOrOh+r2pXTaYPVrAo9B+fZ3IaOtFmbksAV1tEsUVFxwZJQqeXKs\nitXSb3PAOCCFWEwNinr3Ht9BYuzTyIw1dDiwZWr9cQKBgCQ633Y6RLRNzZJjJEOJ\nRUA4x/rfCKi4aYQebHSXVvEzpeEKnXUyxF/pHeH0VOxW7kJUuM9DpFaP4q6AOnXN\nwNxQkrHH+PBES5EQzG2EUeovYlvLLxuic380ZoSbgSWSrP1d+eOZGvLLTXyeSOvn\nJARBJCgKNIPGN8YJcdINsAWH\n-----END PRIVATE KEY-----\n",
        "client_email": "mom-helper-41@mom-english-bot.iam.gserviceaccount.com",
        "client_id": "112440344508636174830",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mom-helper-41%40mom-english-bot.iam.gserviceaccount.com"
    }
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证失败: {e}")
        st.stop()

gc = init_connection()

# ==========================================
# 2. 基础配置 (从 Secrets 读取)
# ==========================================
AI_API_KEY = st.secrets["AI_API_KEY"]
WX_APPID = st.secrets["WX_APPID"]
WX_SECRET = st.secrets["WX_SECRET"]
WX_TOUSER = st.secrets["WX_TOUSER"]
WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]

# ==========================================
# 3. 核心功能
# ==========================================
st.set_page_config(page_title="Mom's English Helper", layout="centered")
st.title("👵 妈妈英语全自动助手")

def get_data():
    try:
        sh = gc.open("Mom_English_Study") # 确保你的表格叫这个名字
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        return pd.DataFrame(data), worksheet
    except Exception as e:
        st.error(f"📊 找不到表格: {e}。请确认表格已共享给服务账号邮箱。")
        return pd.DataFrame(), None

df, worksheet = get_data()

# 示例词库 (你可以后期改为读取 Excel)
WORDS_POOL = ["Morning", "Water", "Health", "Happy", "Family", "Delicious", "Beautiful"]

if st.button("🚀 生成课件并推送微信", use_container_width=True):
    with st.spinner("AI 老师正在备课中..."):
        try:
            # 1. 随机选 3 个词
            today_words = random.sample(WORDS_POOL, 3)
            
            # 2. AI 生成内容 (DeepSeek)
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"请为一位正在学英语的妈妈编写课件。单词是：{', '.join(today_words)}。要求：亲切自然，包含中文含义、简单的音标和一句生活化的中文例句。"
            res = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}]
            )
            content = res.choices[0].message.content

            # 3. 微信推送
            token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
            token = requests.get(token_url).json().get("access_token")
            
            wx_payload = {
                "touser": WX_TOUSER,
                "template_id": WX_TEMPLATE_ID,
                "data": {
                    "content": {"value": content}
                }
            }
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}", json=wx_payload).json()

            if wx_res.get("errcode") == 0:
                # 4. 写入 Google Sheet 记录
                worksheet.append_row([datetime.now().strftime("%Y-%m-%d"), ",".join(today_words)])
                st.balloons()
                st.success("✅ 推送成功！妈妈已经收到消息啦。")
                st.info("学习内容展示：")
                st.write(content)
            else:
                st.error(f"微信接口报错：{wx_res}")

        except Exception as e:
            st.error(f"运行出错：{e}")

# 显示最近的学习记录
if not df.empty:
    st.divider()
    st.subheader("📝 最近学习记录")
    st.dataframe(df.tail(5), use_container_width=True)
