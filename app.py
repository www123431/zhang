import streamlit as st
import docx
import openai
import requests
import random
from datetime import datetime, timedelta

# --- 1. 配置加载 (保持不变) ---
try:
    WX_APPID = st.secrets["WX_APPID"]
    WX_SECRET = st.secrets["WX_SECRET"]
    WX_TOUSER = st.secrets["WX_TOUSER"]
    WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]
    AI_API_KEY = st.secrets["AI_API_KEY"]
except Exception as e:
    st.error("❌ Secrets 缺失！")
    st.stop()

# --- 2. 词库分类 (简化展示) ---
WORDS_DB = {
    "入门级": ["the", "be", "to", "and", "a", "in", "I", "it", "for", "on", "Water", "Food", "Family"],
    "进阶级": ["have", "that", "not", "this", "but", "his", "will", "Market", "Cook", "Breakfast"],
    "挑战级": ["would", "their", "which", "Price", "Cheap", "Expensive", "Medicine", "Pain"]
}

# --- 3. 核心功能函数 ---

def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    return requests.get(url).json().get("access_token")

def send_wechat_msg(content):
    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": WX_TOUSER,
        "template_id": WX_TEMPLATE_ID,
        "data": {"content": {"value": content, "color": "#173177"}}
    }
    return requests.post(url, json=payload).json()

# --- 4. 艾宾浩斯算法模拟 ---
# 在没有外部数据库的情况下，我们通过 session_state 模拟一个学习日志
if 'study_log' not in st.session_state:
    st.session_state.study_log = {} # 格式: {日期: [单词列表]}

# --- 5. Streamlit 界面 ---
st.set_page_config(page_title="妈妈英语助手-艾宾浩斯版", page_icon="📈")
st.title("👵 妈妈英语：艾宾浩斯科学复习版")

# 侧边栏
st.sidebar.header("📈 学习数据统计")
st.sidebar.write(f"已打卡天数: {len(st.session_state.study_log)} 天")

# 难度调节
level = st.select_slider('选择难度：', options=['入门级', '进阶级', '挑战级'])
word_pool = WORDS_DB[level]

st.markdown("---")

# 逻辑核心：今日计划
today_str = datetime.now().strftime("%Y-%m-%d")
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
four_days_ago_str = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")

# 1. 获取新词
new_words = random.sample(word_pool, 2)

# 2. 获取复习词 (模拟艾宾浩斯曲线：复习昨天和4天前的内容)
review_words = []
if yesterday_str in st.session_state.study_log:
    review_words.extend(st.session_state.study_log[yesterday_str])
if four_days_ago_str in st.session_state.study_log:
    review_words.extend(st.session_state.study_log[four_days_ago_str])

st.subheader("🗓️ 今日学习清单")
col1, col2 = st.columns(2)
with col1:
    st.write("**🆕 今日新词:**")
    for w in new_words: st.write(f"- {w}")
with col2:
    st.write("**🔄 科学复习 (艾宾浩斯):**")
    if review_words:
        for w in review_words[:2]: st.write(f"- {w} (温故知新)")
    else:
        st.write("新开始，暂无复习词")

# --- 6. 生成并推送 ---
if st.button("🚀 开启科学复习推送"):
    with st.spinner('🤖 AI 正在根据遗忘曲线编排内容...'):
        try:
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            
            # AI 提示词注入艾宾浩斯逻辑
            prompt = f"""
            你是一个温暖的英语老师。
            今日新词：{', '.join(new_words)}
            复习旧词：{', '.join(review_words) if review_words else '无'}
            请写一段话：
            1. 先用亲切的话语鼓励妈妈；
            2. 简要讲解新词（音标、意思、例句）；
            3. 如果有旧词，顺带提一句复习（例如：还记得昨天的xx吗？）；
            4. 严格控制在200字内，适合微信阅读。
            """
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}]
            )
            ai_content = response.choices[0].message.content
            
            # 执行推送
            result = send_wechat_msg(ai_content)
            
            if result.get("errcode") == 0:
                # 记录学习日志（BA 数据的持久化模拟）
                st.session_state.study_log[today_str] = new_words
                st.balloons()
                st.success("🎉 科学推送成功！已记录今日学习进度。")
                st.info(ai_content)
            else:
                st.error(f"微信报错: {result}")
        except Exception as e:
            st.error(f"技术故障: {e}")

st.markdown("---")
st.caption("Proudly built by her Business Analytics student son ❤️")
