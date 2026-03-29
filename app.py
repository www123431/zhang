# -*- coding: utf-8 -*-
import streamlit as st
import docx
import openai
import requests

# --- 1. 从 Streamlit Secrets 获取配置 (安全第一) ---
try:
    CORP_ID = st.secrets["CORP_ID"]
    CORP_SECRET = st.secrets["CORP_SECRET"]
    AGENT_ID = int(st.secrets["AGENT_ID"])
    AI_API_KEY = st.secrets["AI_API_KEY"]
    # 选填：给后台加个简单的访问密码
    ADMIN_PWD = st.secrets.get("ADMIN_PASSWORD", "")
except Exception as e:
    st.error("Secrets 配置缺失，请在 Streamlit 后台设置！")
    st.stop()

# --- 2. 核心功能 ---
def get_token():
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}"
    res = requests.get(url).json()
    return res.get('access_token')

def send_msg(content):
    token = get_token()
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    data = {
        "touser": "@all",
        "msgtype": "text",
        "agentid": AGENT_ID,
        "text": {"content": content}
    }
    return requests.post(url, json=data).json()

# --- 3. 界面 ---
st.set_page_config(page_title="妈妈英语后台", page_icon="📝")

if ADMIN_PWD:
    pwd = st.sidebar.text_input("管理员密码", type="password")
    if pwd != ADMIN_PWD:
        st.info("请输入密码使用后台")
        st.stop()

st.title("👵 妈妈英语学习管理后台")

uploaded_file = st.file_uploader("上传本周单词 Word 文档", type="docx")

if uploaded_file:
    doc = docx.Document(uploaded_file)
    words = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    st.success(f"已识别到 {len(words)} 个单词")
    
    if st.button("🚀 生成今日内容并推送"):
        with st.spinner('AI 正在思考中...'):
            client = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"请为这些单词造生活化、温暖的句子，附带中文翻译：{', '.join(words[:10])}"
            
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}]
                )
                ai_content = response.choices[0].message.content
                
                # 推送
                res = send_msg(ai_content)
                if res.get("errmsg") == "ok":
                    st.balloons()
                    st.success("发送成功！")
                    st.info(ai_content)
                else:
                    st.error(f"微信推送失败: {res}")
            except Exception as e:
                st.error(f"AI 生成失败: {e}")