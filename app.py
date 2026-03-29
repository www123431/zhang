import streamlit as st
import docx
import openai
import requests
import random

# --- 1. 配置加载 ---
try:
    WX_APPID = st.secrets["WX_APPID"]
    WX_SECRET = st.secrets["WX_SECRET"]
    WX_TOUSER = st.secrets["WX_TOUSER"]
    WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]
    AI_API_KEY = st.secrets["AI_API_KEY"]
except Exception as e:
    st.error("❌ Secrets 配置缺失，请检查控制台设置。")
    st.stop()

# --- 2. 核心单词本 (带难度分级) ---
# 简单词：生活常用、基础代词
EASY_WORDS = [
    "the", "be", "to", "and", "a", "in", "I", "it", "for", "on", "with", "he", "you", "do", "at", 
    "we", "her", "she", "my", "me", "good", "new", "day", "us", "Water", "Food", "Family", "Son", 
    "Daughter", "Help", "Walk", "Park", "Friend", "Money", "Shop"
]

# 中等词：动作、地点、描述词
MEDIUM_WORDS = [
    "have", "that", "not", "this", "but", "his", "by", "from", "they", "say", "will", "one", 
    "all", "there", "what", "so", "up", "out", "if", "about", "who", "get", "go", "when", "make", 
    "can", "like", "time", "just", "know", "take", "people", "year", "your", "some", "see", 
    "now", "look", "come", "back", "after", "use", "how", "our", "work", "first", "well", "way", 
    "want", "give", "most", "Market", "Supermarket", "Vegetable", "Fruit", "Kitchen", "Cook", 
    "Drink", "Breakfast", "Lunch", "Dinner", "Doctor", "Hospital"
]

# 挑战词：抽象词、较长单词、医疗词
HARD_WORDS = [
    "would", "their", "which", "into", "could", "them", "other", "than", "then", "only", "its", 
    "over", "think", "also", "two", "even", "because", "any", "these", "Price", "Cheap", 
    "Expensive", "Medicine", "Pain", "Telephone", "Grandchild"
]

# --- 3. 核心功能函数 ---

def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    try:
        res = requests.get(url).json()
        return res.get("access_token")
    except:
        return None

def send_wechat_template_msg(content):
    token = get_access_token()
    if not token:
        return {"errcode": -1, "errmsg": "获取 Token 失败"}
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    
    payload = {
        "touser": WX_TOUSER,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "content": {
                "value": content,
                "color": "#173177"
            }
        }
    }
    return requests.post(url, json=payload).json()

# --- 4. Streamlit 界面设计 ---

st.set_page_config(page_title="妈妈英语助手", page_icon="❤️")
st.title("👵 妈妈英语学习推手")

# 侧边栏：功能选择
mode = st.sidebar.radio("📋 模式选择", ["📖 妈妈单词本 (内置)", "📂 临时上传 (Word)"])

final_words = []

if mode == "📖 妈妈单词本 (内置)":
    st.subheader("⚙️ 难度调节")
    
    # 【新增】难度调节滑块
    level = st.select_slider(
        '滑动选择今日难度：',
        options=['入门级', '进阶级', '挑战级'],
        value='入门级'
    )
    
    # 根据滑块选择词库
    if level == '入门级':
        word_pool = EASY_WORDS
        level_desc = "适合轻松复习最基础的词汇。"
    elif level == '进阶级':
        word_pool = MEDIUM_WORDS
        level_desc = "包含更多生活动作和场景描述。"
    else:
        word_pool = HARD_WORDS
        level_desc = "稍微有点挑战，适合提升语感。"
        
    st.caption(f"💡 {level_desc}")

    if st.button("🔄 换一批单词"):
        st.session_state.selected_words = random.sample(word_pool, min(3, len(word_pool)))
    
    if 'selected_words' not in st.session_state:
        st.session_state.selected_words = random.sample(word_pool, 3)
    
    final_words = st.session_state.selected_words
    st.info(f"今日【{level}】精选：{', '.join(final_words)}")

else:
    uploaded_file = st.file_uploader("上传本周单词 Word 文档", type="docx")
    if uploaded_file:
        doc = docx.Document(uploaded_file)
        final_words = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        st.success(f"✅ 成功读取 {len(final_words)} 个词条")

# --- 5. 推送逻辑 ---

if final_words:
    if st.button("🚀 开启今日推送"):
        with st.spinner('🤖 AI 正在根据难度组织语言...'):
            try:
                client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
                
                # 提示词微调：根据难度调整解释的深度
                system_prompt = "你是一个极具耐心的英语老师。请为妈妈写一段学习内容。要求：1.语气亲切；2.包含音标、意思、1个简单生活化例句；3.总字数严格控制在200字内；4.排版美观。"
                user_prompt = f"请讲解这几个词：{', '.join(final_words)}"
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                ai_content = response.choices[0].message.content
                result = send_wechat_template_msg(ai_content)
                
                if result.get("errcode") == 0:
                    st.balloons()
                    st.success("🎉 推送成功！")
                    st.markdown("### 📱 推送预览：")
                    st.info(ai_content)
                else:
                    st.error(f"❌ 微信端返回错误：{result}")
            except Exception as e:
                st.error(f"⚠️ 技术故障：{str(e)}")

st.markdown("---")
st.caption("Proudly built by her Business Analytics student son ❤️")
