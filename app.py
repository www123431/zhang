import streamlit as st
import docx
import openai
import requests

# --- 1. 基础配置 ---
try:
    WX_APPID = st.secrets["WX_APPID"]
    WX_SECRET = st.secrets["WX_SECRET"]
    WX_TOUSER = st.secrets["WX_TOUSER"]
    WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]
    AI_API_KEY = st.secrets["AI_API_KEY"]
except Exception as e:
    st.error("❌ Secrets 缺失，请检查 Streamlit 后台设置。")
    st.stop()

# --- 2. 微信推送逻辑 ---

def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    try:
        res = requests.get(url).json()
        return res.get("access_token")
    except:
        return None

def send_wechat_msg(content):
    token = get_access_token()
    if not token:
        return {"errcode": -1, "errmsg": "Token获取失败"}
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    
    # 确保 Key 是 content，匹配你的模板 {{content.DATA}}
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

# --- 3. Streamlit 界面 ---

st.set_page_config(page_title="妈妈英语助手", page_icon="❤️")
st.title("👵 妈妈英语学习 - 自动推送")

uploaded_file = st.file_uploader("📂 选择本周单词 Word 文档", type="docx")

if uploaded_file:
    doc = docx.Document(uploaded_file)
    words = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    if words:
        st.success(f"✅ 已识别 {len(words)} 个词条")
        
        if st.button("🚀 生成并推送到微信"):
            with st.spinner('🤖 AI 正在组织语言...'):
                try:
                    client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
                    
                    # 提示词保持温馨风格
                    prompt = f"你是一个温暖的英语老师，请为以下单词制作一个给妈妈看的学习卡片，包含音标、意思和简单的生活化句子。排版要清晰，每次取前5个：{', '.join(words[:5])}"
                    
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    ai_content = response.choices[0].message.content
                    
                    # 执行推送
                    result = send_wechat_msg(ai_content)
                    
                    if result.get("errcode") == 0:
                        st.balloons()
                        st.success("🎉 发送成功！妈妈已经收到了。")
                        st.subheader("📱 内容预览：")
                        st.markdown(ai_content)
                    else:
                        st.error(f"❌ 推送失败：{result}")
                except Exception as e:
                    st.error(f"⚠️ 出错了：{e}")

# --- 4. 底部文案 (保留你喜欢的版本) ---
st.markdown("---")
st.caption("Proudly built by her Business Analytics student son ❤️")
