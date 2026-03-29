import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime, timedelta

# --- 1. 认证与安全配置 ---
try:
    # 核心身份信息：处理私钥中的换行符
    raw_key = st.secrets["G_PRIVATE_KEY"]
    if "\\n" in raw_key:
        formatted_key = raw_key.replace("\\n", "\n")
    else:
        formatted_key = raw_key

    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["project_id"],
        "private_key": formatted_key,
        "client_email": st.secrets["G_CLIENT_EMAIL"],
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    
    # 微信与 AI 配置
    WX_APPID = st.secrets["WX_APPID"]
    WX_SECRET = st.secrets["WX_SECRET"]
    WX_TOUSER = st.secrets["WX_TOUSER"]
    WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]
    AI_API_KEY = st.secrets["AI_API_KEY"]
    
    # 你的 Google Sheet 名字（确保与你创建的一致）
    SHEET_NAME = "Mom_English_Study" 
except Exception as e:
    st.error(f"❌ 初始化失败，请检查 Secrets 配置。错误信息: {e}")
    st.stop()

# --- 2. 单词库 (内置 1000 词简化分类) ---
EASY_WORDS = ["the", "be", "to", "and", "a", "in", "I", "it", "for", "on", "Water", "Food", "Family", "Son", "Daughter", "Help", "Walk", "Park", "Friend", "Money", "Shop"]
MEDIUM_WORDS = ["have", "that", "not", "this", "but", "his", "by", "from", "they", "say", "will", "one", "all", "there", "what", "so", "up", "out", "if", "about", "who", "get", "go", "when", "make", "can", "like", "time", "just", "know", "take", "people", "year", "your", "some", "see", "now", "look", "come", "back", "after", "use", "how", "our", "work", "first", "well", "way", "want", "give", "most", "Market", "Supermarket", "Vegetable", "Fruit", "Kitchen", "Cook", "Drink", "Breakfast", "Lunch", "Dinner", "Doctor", "Hospital"]
HARD_WORDS = ["would", "their", "which", "into", "could", "them", "other", "than", "then", "only", "its", "over", "think", "also", "two", "even", "because", "any", "these", "Price", "Cheap", "Expensive", "Medicine", "Pain", "Telephone", "Grandchild"]

# --- 3. 核心数据库读写函数 ---
def get_data_from_sheet():
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.get_worksheet(0)
        records = worksheet.get_all_records()
        return pd.DataFrame(records), worksheet
    except Exception as e:
        st.error(f"无法读取表格，请确认表格名称是否为 '{SHEET_NAME}' 且已授权给服务账号。")
        return pd.DataFrame(columns=["date", "words"]), None

def get_review_list(df):
    if df.empty: return []
    # 模拟艾宾浩斯：复习 1 天前和 4 天前
    target_dates = [
        (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")
    ]
    review_rows = df[df['date'].astype(str).isin(target_dates)]
    words = []
    for val in review_rows['words']:
        words.extend([w.strip() for w in str(val).split(",")])
    return list(set(words))

# --- 4. 界面展示 ---
st.set_page_config(page_title="妈妈英语助手", page_icon="❤️")
st.title("👵 妈妈英语：科学复习全自动版")

df, worksheet = get_data_from_sheet()
st.sidebar.header(f"📊 累计打卡：{len(df)} 天")

level = st.select_slider('选择难度：', options=['入门级', '进阶级', '挑战级'])
pool = {"入门级": EASY_WORDS, "进阶级": MEDIUM_WORDS, "挑战级": HARD_WORDS}[level]

new_words = random.sample(pool, 3)
review_words = get_review_list(df)

st.write(f"🆕 **今日新词**：{', '.join(new_words)}")
if review_words:
    st.write(f"🔄 **科学复习**：{', '.join(review_words[:2])}")
else:
    st.caption("今天还没有复习任务，继续加油！")

# --- 5. 执行推送与保存 ---
if st.button("🚀 开启今日推送并同步云端"):
    with st.spinner('🤖 AI 正在编排内容...'):
        try:
            # AI 生成
            client_ai = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"你是一个温暖的英语老师。今日新词：{new_words}。复习：{review_words}。请为妈妈写一段微信推送，包含音标、意思、1个简单例句。200字内。"
            response = client_ai.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
            ai_content = response.choices[0].message.content
            
            # 微信发送
            token_res = requests.get(f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}").json()
            access_token = token_res.get("access_token")
            
            payload = {
                "touser": WX_TOUSER,
                "template_id": WX_TEMPLATE_ID,
                "data": {"content": {"value": ai_content, "color": "#173177"}}
            }
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}", json=payload).json()
            
            if wx_res.get("errcode") == 0:
                # 写入表格
                today_str = datetime.now().strftime("%Y-%m-%d")
                worksheet.append_row([today_str, ",".join(new_words)])
                
                st.balloons()
                st.success("🎉 推送成功！数据已同步至 Google Sheets。")
                st.info(ai_content)
            else:
                st.error(f"微信端报错：{wx_res}")
        except Exception as e:
            st.error(f"执行失败：{e}")

st.markdown("---")
st.caption("Developed by Business Analytics student for Mom. ❤️")
