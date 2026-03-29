import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime, timedelta

# ==========================================
# 1. 核心认证配置 (使用原始字符串 r''' 彻底隔离转义干扰)
# ==========================================
def init_connection():
    # 使用 r''' ''' 确保 Python 不会对内容做任何预处理
    # 请确保 -----BEGIN... 和 -----END... 之间没有任何多余的空格
    PRIVATE_KEY_RAW = r"""-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDDwWdaKxaAdDjr
pqBApRgFjxT74fJ8DLZI5F5SE7JtIKW3H9ox6ut/rr2hysFKQmJGYVVwRWX04YKj
0z82seeeidW4L26t1SGH9pM5no3omEJ51/dYGDj56aGswU08KuJjsFKop2M+QHMG
6rrKfIwzYhX/YCx6ZBBenD/UQq0Rus9ZDeNLn9OUcXugVhIqmt39lIbCRh/kONl5
N0HY94VOWbLSEsQgyp2UROtsQ5m8xQmB44BK6KSf3GKQV8gfazMxFRxCxbXACZ2d
qNuOPick1XeZtWi92wfe9Y0eVtr0jjYw0ypMjl9R/UUtM1DQufXDrTS1Du3dBcQB
JKxOi4pDAgMBAAECggEADYqT8S9Y26LuixKYNFCXVE8dBv2Ozhj9BRbTFX9qUNU4
0W2hJOHYz5jRYl9Jtq7X6IF0LROH5YQyCs4iqdBtstBbGeYiFGFRc/vRHGPE8kmS
E6amZBAs5NDOD8rBYn+e8IFyflsx6M0BiAF10WsDMcy/s8491WuVnE3XtoG0Qi0Y
eTABtDIyAxt+ubFP/3Ft8pVP5Jjauv8gCgrg8XmrTURwoKk94c3OxvUCRVd5m4Rq
naJ8z4wcVErxl7ZaEkfUxJG9W52Lfgojnir1SzG1SrlEjpMFcH2vq8EwyNfW7/2po
vChNjhB4YexJukFPBK1yyDfQeVJo3A3SqEDH7kh6xQKBgQDx9EdP8baHhpkjT8ZW
5//JfhLbpcCbTa+7cZE7f82Vy7Uem/1xGeEK65tgKA7uvf35u9km91Bpf+xuC7iC
Ndjn2pYmtCKyNvRpfbyCXCmbO+SxAdonCjI5mg7ntfd5dbwL+nQE9dmCBa8J9WKS
e3KD4skPTm5miDNl0FnbT2P5pwKBgQDPHo7nXWsFkHTUI7krKpUg+hXCJ9uV7qmy
ls0EYVExnDzaK4fz9a3EpZGPbOCeEHqp9XB//pVCuuN3YnY2KLd5IG2pJH0SpWDd
+U5unH0B1iWMPSr4BdGctLN0+iYuPeMugA+ZFBJ+A3Oa342WRP1jf3MHYVNaqrM2
r8PjfIxGBQKBgEfELC7TRE/Ypa2qqOr4L4+lfJR4CrRGC7zuh6R9WQ54eMWWgUs9
4NlrXw/bcepwolej11pOeyR/1DIj+dtte2PyGx1pyuzPjhmIORT1n0WzMzcplHqF
9LXPM2KZP8lgGaH37NfX0GdXpj6u8Uj/oszpxLdsjSSOe6hUb4K0frP7AoGAGMbv
EX57bw746ufbHu7ZKDjCoZdjDWyfoF2p6Pw7WlP2c6MBgI3DW+LyptW/iSkvg2V5
L9akxHbW/1EoExKL4FGgzLswuypNjEBmwZS236FenIg0u7b2fGihjzzdlGqS4t0v
AIEGNUz0Z3KW3YMjTOPSPu/FqPMCvWgJZw1fOoECgYEAsp342gT3gXITeOaeGpxS
fgCxrQgdh6rY00b6gpvFVtGRv9cx9it87Kzzh4hCyKAUTS6UP2ML7kUCviX4hvNA
RNr87qAZtv5dMJhKOradeWGY0qo+09+HnZJ5OwFwT0do8klCoBF5noChX8e046rK
zuf9PU50qEons0dOMTXaPrc=
-----END PRIVATE KEY-----"""

    # 关键点：手动强制清洗字符串
    # 1. 移除可能存在的 \r (Windows换行)
    # 2. 将字面量的 "\n" 替换为真实的换行符
    clean_key = PRIVATE_KEY_RAW.replace("\r", "").replace("\\n", "\n").strip()

    creds_dict = {
        "type": "service_account",
        "project_id": "mom-english-bot",
        "private_key": clean_key,
        "client_email": "mom-helper-41@mom-english-bot.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        # 如果还是报错，我们会看到更详细的输出
        st.error(f"❌ 认证初始化失败: {e}")
        st.stop()

# 初始化客户端
gc = init_connection()

# --- 后续业务逻辑保持不变 ---
SHEET_NAME = "Mom_English_Study"
AI_API_KEY = st.secrets["AI_API_KEY"]
WX_APPID = st.secrets["WX_APPID"]
WX_SECRET = st.secrets["WX_SECRET"]
WX_TOUSER = st.secrets["WX_TOUSER"]
WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]

# 词库
EASY_WORDS = ["Water", "Food", "Family", "Son", "Daughter", "Help", "Walk", "Park", "Friend", "Money"]
MEDIUM_WORDS = ["Market", "Supermarket", "Vegetable", "Fruit", "Kitchen", "Cook", "Drink", "Breakfast"]
HARD_WORDS = ["Medicine", "Hospital", "Doctor", "Price", "Cheap", "Expensive", "Telephone"]

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

# UI
st.set_page_config(page_title="Mom's English Helper", page_icon="👵")
st.title("👵 妈妈英语全自动助手")

df, worksheet = get_data()

with st.sidebar:
    st.header("📈 学习状态")
    st.metric("累计天数", len(df))
    level = st.radio("难度选择", ["入门级", "进阶级", "挑战级"])

pool = {"入门级": EASY_WORDS, "进阶级": MEDIUM_WORDS, "挑战级": HARD_WORDS}[level]
today_new = random.sample(pool, 3)
today_review = get_review_words(df)

col1, col2 = st.columns(2)
with col1:
    st.subheader("🆕 今日新词")
    for w in today_new: st.write(f"- **{w}**")
with col2:
    st.subheader("🔄 艾宾浩斯复习")
    if today_review:
        for w in today_review[:3]: st.write(f"- {w}")
    else:
        st.write("暂无任务")

if st.button("🚀 推送并同步云端"):
    with st.spinner("正在生成内容..."):
        try:
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"今日单词：{today_new}，复习单词：{today_review}。为老人家写微信推送，含音标、中文、简单例句。200字内。"
            ai_res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
            push_content = ai_res.choices[0].message.content

            token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
            token = requests.get(token_url).json().get("access_token")
            
            payload = {
                "touser": WX_TOUSER,
                "template_id": WX_TEMPLATE_ID,
                "data": {"content": {"value": push_content}}
            }
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}", json=payload).json()

            if wx_res.get("errcode") == 0:
                worksheet.append_row([datetime.now().strftime("%Y-%m-%d"), ",".join(today_new)])
                st.success("✅ 推送成功！")
                st.balloons()
                st.info(push_content)
            else:
                st.error(f"微信报错: {wx_res}")
        except Exception as e:
            st.error(f"运行失败: {e}")

st.divider()
st.caption("Postgraduate Business Analytics Project ❤️")
