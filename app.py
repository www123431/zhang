import streamlit as st
import docx
import openai
import requests
import json

# --- 1. 配置加载 (从 Streamlit Secrets 读取) ---
try:
    # 微信测试号参数
    WX_APPID = st.secrets["WX_APPID"]
    WX_SECRET = st.secrets["WX_SECRET"]
    WX_TOUSER = st.secrets["WX_TOUSER"]
    WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]
    
    # DeepSeek AI 参数
    AI_API_KEY = st.secrets["AI_API_KEY"]
except Exception as e:
    st.error("❌ Secrets 配置缺失！请在 Streamlit 控制台设置 WX_APPID, WX_SECRET, WX_TOUSER, WX_TEMPLATE_ID, AI_API_KEY")
    st.stop()

# --- 2. 核心功能函数 ---

def get_access_token():
    """获取微信 Access Token"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    res = requests.get(url).json()
    return res.get("access_token")

def send_wechat_template_msg(content):
    """发送模板消息 (绕过48小时互动限制)"""
    token = get_access_token()
    if not token:
        return {"errcode": -1, "errmsg": "获取 Token 失败"}
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    
    # 构建模板消息体
    # 注意：这里的 "content" 必须对应你在测试号后台定义的 {{content.DATA}}
    payload = {
        "touser": WX_TOUSER,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "content": {
                "value": content,
                "color": "#333333"
            }
        }
    }
    
    res = requests.post(url, json=payload).json()
    return res

# --- 3. Streamlit 界面设计 ---

st.set_page_config(page_title="妈妈英语助手", page_icon="📝")
st.title("👵 妈妈英语学习推手")
st.markdown("---")

uploaded_file = st.file_uploader("📂 上传本周单词 Word 文档", type="docx")

if uploaded_file:
    # 读取 Word 内容
    doc = docx.Document(uploaded_file)
    all_text = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    if all_text:
        st.success(f"✅ 成功读取 {len(all_text)} 行内容")
        
        if st.button("🚀 生成内容并推送到微信"):
            with st.spinner('🤖 DeepSeek 正在为妈妈精心准备内容...'):
                try:
                    # 调用 DeepSeek AI
                    client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
                    
                    system_prompt = "你是一个温暖的英语老师。请根据用户提供的单词，写一段给妈妈看的英语学习内容。要求：1. 语言亲切温馨；2. 包含单词、音标、简单的例句和中文翻译；3. 排版清晰，适合手机阅读。"
                    user_prompt = f"这是今天的单词：{', '.join(all_text[:5])}" # 每次取前5个避免消息太长
                    
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    
                    ai_content = response.choices[0].message.content
                    
                    # 执行微信推送
                    result = send_wechat_template_msg(ai_content)
                    
                    if result.get("errcode") == 0:
                        st.balloons()
                        st.success("🎉 发送成功！妈妈已经收到了。")
                        st.subheader("📱 推送内容预览：")
                        st.info(ai_content)
                    else:
                        st.error(f"❌ 微信推送失败：{result.get('errmsg')}")
                        
                except Exception as e:
                    st.error(f"⚠️ 运行出错：{str(e)}")
    else:
        st.warning("Word 文档似乎是空的，请检查内容。")

st.markdown("---")
st.caption("Proudly built by her Business Analytics student son ❤️")
