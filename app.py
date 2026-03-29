import streamlit as st
import docx
import openai
import requests

# 1. 配置信息 (从 Streamlit Secrets 读取)
try:
    # 微信测试号参数
    WX_APPID = st.secrets["WX_APPID"]
    WX_SECRET = st.secrets["WX_SECRET"]
    WX_TOUSER = st.secrets["WX_TOUSER"] # 就是你刚才发的那串 OpenID
    
    # AI 参数
    AI_API_KEY = st.secrets["AI_API_KEY"]
    ADMIN_PWD = st.secrets.get("ADMIN_PASSWORD", "123456")
except Exception as e:
    st.error("Secrets 配置缺失！请在 Streamlit 后台设置 WX_APPID, WX_SECRET, WX_TOUSER, AI_API_KEY")
    st.stop()

# 2. 微信发送逻辑 (模板消息)
def send_wechat_msg(content):
    # 第一步：获取 Access Token
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    token_res = requests.get(token_url).json()
    access_token = token_res.get('access_token')
    
    if not access_token:
        return f"Token 获取失败: {token_res}"

    # 第二步：发送客服消息 (最简单，不需要配置模板 ID)
    # 注意：如果发送失败，说明需要先去后台新建一个“模板消息”，这里我们先尝试最通用的客服接口
    send_url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"
    data = {
        "touser": WX_TOUSER,
        "msgtype": "text",
        "text": {"content": content}
    }
    res = requests.post(send_url, json=data).json()
    return res

# --- 界面 ---
st.set_page_config(page_title="妈妈英语后台", page_icon="📖")
st.title("👵 妈妈英语学习管理后台 (微信版)")

uploaded_file = st.file_uploader("上传本周单词 Word 文档", type="docx")

if uploaded_file:
    doc = docx.Document(uploaded_file)
    words = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    st.success(f"已识别到 {len(words)} 个单词")
    
    if st.button("🚀 生成今日内容并推送"):
        with st.spinner('AI 正在为妈妈写句子...'):
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"请为这些英语单词造生活化、温暖的句子，附带中文翻译和音标：{', '.join(words[:10])}"
            
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}]
                )
                ai_content = response.choices[0].message.content
                
                # 推送消息
                res = send_wechat_msg(ai_content)
                if res.get("errcode") == 0:
                    st.balloons()
                    st.success("发送成功！妈妈的微信应该响啦~")
                    st.info(ai_content)
                else:
                    st.error(f"微信推送失败: {res}")
            except Exception as e:
                st.error(f"生成失败: {e}")
