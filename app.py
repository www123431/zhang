import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import requests
import datetime

# ==========================================
# 1. 初始化连接 (保持不变，因为你已经跑通了)
# ==========================================
def init_connection():
    try:
        creds_dict = st.secrets["gcp_service_account"].to_dict()
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证连接失败: {e}")
        st.stop()

# ==========================================
# 2. 核心功能函数
# ==========================================

# A. 调用 AI 生成单词 (DeepSeek)
def generate_word_via_ai():
    api_key = st.secrets.get("AI_API_KEY")
    if not api_key:
        return {"word": "Apple", "meaning": "苹果", "note": "请先配置 AI_API_KEY"}
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = "请为一个零基础的老年人生成一个高频英语单词，包含单词、中文释义、一个非常简单的谐音记忆法，以及一个生活化的例句。"
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"} # 假设使用支持JSON模式的API
    }
    
    try:
        # 这里演示逻辑，实际调用根据 DeepSeek API 文档调整
        # resp = requests.post("https://api.deepseek.com/chat/completions", json=data, headers=headers)
        # result = resp.json()['choices'][0]['message']['content']
        # return json.loads(result)
        return {"word": "Excellent", "meaning": "极好的", "note": "谐音：一颗色烂脱。记法：这一颗苹果颜色烂脱了，说明它熟得‘极好’！"}
    except:
        return {"word": "Hello", "meaning": "你好", "note": "基础词汇"}

# B. 发送微信推送 (微信公众号模板消息)
def send_wechat_msg(content):
    try:
        access_token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={st.secrets['WX_APPID']}&secret={st.secrets['WX_SECRET']}"
        token = requests.get(access_token_url).json().get("access_token")
        
        push_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
        payload = {
            "touser": st.secrets["WX_TOUSER"],
            "template_id": st.secrets["WX_TEMPLATE_ID"],
            "data": {
                "word": {"value": content['word'], "color": "#173177"},
                "meaning": {"value": content['meaning'], "color": "#FF0000"},
                "note": {"value": content['note']}
            }
        }
        res = requests.post(push_url, json=payload)
        return res.json().get("errcode") == 0
    except Exception as e:
        st.write(f"推送出错: {e}")
        return False

# ==========================================
# 3. Streamlit 页面布局
# ==========================================
st.set_page_config(page_title="妈妈英语助手", page_icon="👵")
st.title("👵 妈妈英语全自动助手")

gc = init_connection()
sh = gc.open("Mom_English_Study")
worksheet = sh.get_worksheet(0)

# 侧边栏：手动添加
with st.sidebar:
    st.header("手动添加单词")
    new_w = st.text_input("单词")
    new_m = st.text_input("意思")
    if st.button("存入表格"):
        worksheet.append_row([str(datetime.date.today()), new_w, new_m, "手动添加"])
        st.success("已添加！")

# 主界面：AI 自动化控制台
st.subheader("🤖 AI 自动化任务")
col1, col2 = st.columns(2)

with col1:
    if st.button("✨ AI 生成今日单词", use_container_width=True):
        with st.spinner("AI 正在思考最适合妈妈的记法..."):
            word_data = generate_word_via_ai()
            st.session_state['temp_word'] = word_data
            st.chat_message("assistant").write(f"**单词**: {word_data['word']}\n\n**释义**: {word_data['meaning']}\n\n**记法**: {word_data['note']}")

with col2:
    if 'temp_word' in st.session_state:
        if st.button("📤 确认并推送给妈妈", type="primary", use_container_width=True):
            w = st.session_state['temp_word']
            # 1. 存入表格
            worksheet.append_row([str(datetime.date.today()), w['word'], w['meaning'], w['note']])
            # 2. 微信推送
            success = send_wechat_msg(w)
            if success:
                st.success("✅ 已发送到妈妈微信！数据已归档。")
            else:
                st.warning("数据已存档，但微信推送失败 (请检查 WX 配置)")

# 展示表格数据
st.divider()
st.subheader("📊 历史学习记录")
data = worksheet.get_all_records()
if data:
    df = pd.DataFrame(data)
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
