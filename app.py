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

# --- 2. 核心单词本 (整合你提供的 1000 词清单) ---
# 这里提取了你提供的清单中的核心词汇，去掉了重复项
RAW_WORDS = [
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "I", "it", "for", "not", "on", "with", "he", "as", "you", "do", "at", 
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would", "there", 
    "their", "what", "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", 
    "no", "just", "him", "know", "take", "people", "into", "year", "your", "good", "some", "could", "them", "see", "other", "than", 
    "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two", "how", "our", "work", 
    "first", "well", "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us", "Market", "Supermarket", 
    "Vegetable", "Fruit", "Price", "Cheap", "Expensive", "Kitchen", "Cook", "Water", "Drink", "Food", "Breakfast", "Lunch", "Dinner", 
    "Doctor", "Hospital", "Medicine", "Pain", "Help", "Walk", "Park", "Friend", "Family", "Son", "Daughter", "Grandchild", "Telephone", 
    "Money", "Shop"
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

# 侧边栏：选择模式
mode = st.sidebar.radio("📋 模式选择", ["📖 妈妈单词本 (内置)", "📂 临时上传 (Word)"])

final_words = []

if mode == "📖 妈妈单词本 (内置)":
    st.subheader("📚 1000 词核心库")
    # 随机选 3 个，这样妈妈每天点开都有新鲜感
    if st.button("🔄 换一批单词"):
        st.session_state.selected_words = random.sample(RAW_WORDS, 3)
    
    if 'selected_words' not in st.session_state:
        st.session_state.selected_words = RAW_WORDS[:3]
    
    final_words = st.session_state.selected_words
    st.info(f"今日精选：{', '.join(final_words)}")

else:
    uploaded_file = st.file_uploader("上传本周单词 Word 文档", type="docx")
    if uploaded_file:
        doc = docx.Document(uploaded_file)
        final_words = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        st.success(f"✅ 成功读取 {len(final_words)} 个词条")

# --- 5. 推送逻辑 ---

if final_words:
    if st.button("🚀 开启今日推送"):
        with st.spinner('🤖 DeepSeek 正在为妈妈精心准备内容...'):
            try:
                client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
                
                system_prompt = "你是一个极具耐心且温暖的英语老师。请为妈妈写一段学习内容。要求：1.语气亲切；2.包含音标、意思、1个非常贴近生活的例句；3.总字数严格控制在200字内；4.排版美观。"
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
                    st.success("🎉 推送成功！妈妈应该已经收到通知了。")
                    st.markdown("### 📱 推送预览：")
                    st.info(ai_content)
                else:
                    st.error(f"❌ 微信端返回错误：{result}")
            except Exception as e:
                st.error(f"⚠️ 遇到技术故障：{str(e)}")

st.markdown("---")
st.caption("Proudly built by her Business Analytics student son ❤️")
