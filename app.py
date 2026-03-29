import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime, timedelta

# --- 1. 核心认证逻辑 (包含私钥格式清洗) ---
def init_connection():
    try:
        # 获取原始私钥并进行清洗
        raw_key = st.secrets["G_PRIVATE_KEY"]
        
        # 针对 "Unable to load PEM file" 的核心修复逻辑
        # 1. 处理字面量 \n 字符 2. 确保头部和尾部没有多余空格
        formatted_key = raw_key.replace("\\n", "\n").strip()
        
        # 构建 Google 服务账号字典
        creds_dict = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key": formatted_key,
            "client_email": st.secrets["G_CLIENT_EMAIL"],
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        
        # 授权范围
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证初始化失败: {e}")
        st.info("请检查 Secrets 中的 G_PRIVATE_KEY 格式是否正确。")
        st.stop()

# 初始化客户端
gc = init_connection()

# --- 2. 基础配置 ---
SHEET_NAME = "Mom_English_Study"
AI_API_KEY = st.secrets["AI_API_KEY"]
WX_APPID = st.secrets["WX_APPID"]
WX_SECRET = st.secrets["WX_SECRET"]
WX_TOUSER = st.secrets["WX_TOUSER"]
WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]

# 词库
EASY_WORDS = ["Water", "Food", "Family", "Son", "Daughter", "Help", "Walk", "Park", "Friend", "Money", "Shop"]
MEDIUM_WORDS = ["Market", "Supermarket", "Vegetable", "Fruit", "Kitchen", "Cook", "Drink", "Breakfast", "Lunch", "Dinner"]
HARD_WORDS = ["Medicine", "Hospital", "Doctor", "Price", "Cheap", "Expensive", "Telephone", "Grandchild"]

# --- 3. 数据读写逻辑 ---
def get_data():
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        return pd.DataFrame(data), worksheet
    except Exception as e:
        st.error(f"📊 表格读取失败: {e}")
        st.info(f"请确保表格已 Share 给 {st.secrets['G_CLIENT_EMAIL']} 并设为 Editor。")
        return pd.DataFrame(columns=["date", "words"]), None

def get_review_words(df):
    """艾宾浩斯复习：提取1天前和4天前的词"""
    if df.empty: return []
    today = datetime.now().date()
    # 转换为日期格式进行计算
    df['date_dt'] = pd.to_datetime(df['date']).dt.date
    targets = [today - timedelta(days=1), today - timedelta(days=4)]
    
    review_list = df[df['date_dt'].isin(targets)]['words'].tolist()
    all_review_words = []
    for s in review_list:
        all_review_words.extend([w.strip() for w in str(s).split(",")])
    return list(set(all_review_words))

# --- 4. 界面设计 ---
st.set_page_config(page_title="Mom's English Helper", page_icon="👵")
st.title("👵 妈妈英语全自动助手")

df, worksheet = get_data()

# 侧边栏状态
with st.sidebar:
    st.header("📈 学习进度")
    st.metric("累计天数", len(df))
    level = st.radio("选择今日难度", ["入门级", "进阶级", "挑战级"])

# 准备内容
pool = {"入门级": EASY_WORDS, "进阶级": MEDIUM_WORDS, "挑战级": HARD_WORDS}[level]
today_new = random.sample(pool, 3)
today_review = get_review_words(df)

col1, col2 = st.columns(2)
with col1:
    st.subheader("🆕 今日新词")
    for w in today_new: st.write(f"- **{w}**")
with col2:
    st.subheader("🔄 科学复习")
    if today_review:
        for w in today_review[:3]: st.write(f"- {w}")
    else:
        st.write("暂无复习任务")

# --- 5. 推送与保存 ---
if st.button("🚀 开启今日推送并同步云端"):
    with st.spinner("正在生成温馨推送内容..."):
        try:
            # 1. 调用 AI 生成内容
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"你是一个温暖的英语老师。今日单词：{today_new}，复习单词：{today_review}。请为一位老人家写微信推送，包含单词、音标、中文和简单生活化例句。200字内。"
            ai_res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
            push_content = ai_res.choices[0].message.content

            # 2. 微信推送
            token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
            token = requests.get(token_url).json().get("access_token")
            
            payload = {
                "touser": WX_TOUSER,
                "template_id": WX_TEMPLATE_ID,
                "data": {"content": {"value": push_content, "color": "#173177"}}
            }
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}", json=payload).json()

            # 3. 写入 Google Sheets
            if wx_res.get("errcode") == 0:
                today_str = datetime.now().strftime("%Y-%m-%d")
                worksheet.append_row([today_str, ",".join(today_new)])
                st.success("✅ 推送成功！数据已同步至 Google 表格。")
                st.balloons()
                st.info(push_content)
            else:
                st.error(f"微信推送失败: {wx_res}")
                
        except Exception as e:
            st.error(f"运行出错: {e}")

st.divider()
st.caption("Postgraduate Business Analytics Project for Mom ❤️")
