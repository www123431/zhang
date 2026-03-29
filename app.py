import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import openai
import requests
import random
from datetime import datetime, timedelta

# --- 1. 配置加载 ---
try:
    WX_APPID = st.secrets["WX_APPID"]
    WX_SECRET = st.secrets["WX_SECRET"]
    WX_TOUSER = st.secrets["WX_TOUSER"]
    WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]
    AI_API_KEY = st.secrets["AI_API_KEY"]
except Exception as e:
    st.error("❌ Secrets 缺失，请检查配置。")
    st.stop()

# --- 2. 核心单词本 (带难度分级) ---
EASY_WORDS = ["the", "be", "to", "and", "a", "in", "I", "it", "for", "on", "Water", "Food", "Family", "Son", "Daughter", "Help", "Walk", "Park", "Friend", "Money", "Shop"]
MEDIUM_WORDS = ["have", "that", "not", "this", "but", "his", "by", "from", "they", "say", "will", "one", "all", "there", "what", "so", "up", "out", "if", "about", "who", "get", "go", "when", "make", "can", "like", "time", "just", "know", "take", "people", "year", "your", "some", "see", "now", "look", "come", "back", "after", "use", "how", "our", "work", "first", "well", "way", "want", "give", "most", "Market", "Supermarket", "Vegetable", "Fruit", "Kitchen", "Cook", "Drink", "Breakfast", "Lunch", "Dinner", "Doctor", "Hospital"]
HARD_WORDS = ["would", "their", "which", "into", "could", "them", "other", "than", "then", "only", "its", "over", "think", "also", "two", "even", "because", "any", "these", "Price", "Cheap", "Expensive", "Medicine", "Pain", "Telephone", "Grandchild"]

# --- 3. 数据库与复习逻辑 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_history():
    try:
        # 读取表格，强制 date 为字符串防止格式混乱
        return conn.read(ttl=0) 
    except:
        return pd.DataFrame(columns=["date", "words"])

def get_ebbinghaus_review(df):
    """根据艾宾浩斯曲线(1天, 4天)找复习词"""
    if df.empty: return []
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    four_days_ago = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")
    
    # 过滤出匹配日期的单词
    review_rows = df[df['date'].astype(str).isin([yesterday, four_days_ago])]
    words_to_review = []
    for val in review_rows['words']:
        words_to_review.extend([w.strip() for w in str(val).split(",")])
    return list(set(words_to_review))

# --- 4. 微信推送函数 ---
def send_wechat_msg(content):
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    token = requests.get(token_url).json().get("access_token")
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": WX_TOUSER,
        "template_id": WX_TEMPLATE_ID,
        "data": {"content": {"value": content, "color": "#173177"}}
    }
    return requests.post(url, json=payload).json()

# --- 5. Streamlit 界面 ---
st.set_page_config(page_title="妈妈英语助手-全自动版", page_icon="📈")
st.title("👵 妈妈英语：艾宾浩斯全自动版")

# 侧边栏：显示进度
history_df = get_history()
st.sidebar.header(f"📊 已累计打卡 {len(history_df)} 天")
if not history_df.empty:
    st.sidebar.write("最近学过：", history_df.tail(3))

# 难度调节
level = st.select_slider('选择难度：', options=['入门级', '进阶级', '挑战级'])
pool = {"入门级": EASY_WORDS, "进阶级": MEDIUM_WORDS, "挑战级": HARD_WORDS}[level]

# 生成今日内容
new_words = random.sample(pool, 3)
review_words = get_ebbinghaus_review(history_df)

st.divider()
st.write(f"🆕 **今日新词**：{', '.join(new_words)}")
if review_words:
    st.write(f"🔄 **科学复习**：{', '.join(review_words[:3])}")
else:
    st.caption("暂无需要复习的词汇，坚持学习明天就会出现复习任务哦！")

if st.button("🚀 开启今日科学推送"):
    with st.spinner('🤖 AI 正在编排内容并同步云端...'):
        try:
            # 1. AI 生成
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"你是一个温暖的英语老师。今日新词：{new_words}。复习词：{review_words}。请写一段温馨的微信推送，包含音标、意思、生活化例句。200字内。"
            response = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
            ai_content = response.choices[0].message.content
            
            # 2. 微信推送
            res = send_wechat_msg(ai_content)
            
            if res.get("errcode") == 0:
                # 3. 写入 Google Sheets (数据持久化)
                today_str = datetime.now().strftime("%Y-%m-%d")
                new_row = pd.DataFrame({"date": [today_str], "words": [",".join(new_words)]})
                updated_df = pd.concat([history_df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                
                st.balloons()
                st.success("🎉 推送成功！数据已同步至 Google Sheets。")
                st.info(ai_content)
            else:
                st.error(f"推送失败：{res}")
        except Exception as e:
            st.error(f"发生错误：{e}")

st.markdown("---")
st.caption("Proudly built by her Business Analytics student son ❤️")
