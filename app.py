import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import requests
import json

# ==========================================
# 1. 核心认证 (Secrets 逻辑)
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
        st.error(f"❌ 认证失败: {e}")
        st.stop()

# ==========================================
# 2. AI 生成逻辑 (接入难度分级)
# ==========================================
def generate_10_words_ai(level):
    api_key = st.secrets.get("AI_API_KEY", "")
    if not api_key:
        st.warning("⚠️ 未检测到 AI_API_KEY，正在使用演示数据...")
        return [
            {"date": str(datetime.date.today()), "words": f"Demo_{i}", "meaning": "演示", "notes": "请在 Secrets 中配置 API Key"} 
            for i in range(1, 11)
        ]

    # 根据不同难度定制 Prompt
    level_prompts = {
        "🌱 元气生活": "基础生活高频词，适合日常社交沟通。",
        "✨ 时尚达人": "进阶词汇，涉及生活品味、情感表达、地道口语。",
        "💪 职场精英": "高级词汇，侧重商业思维、逻辑表达、职场专业术语。"
    }

    prompt = f"""
    你是一个贴心的英语私教。你的学生是'卿姐'，一位优雅、上进的女性。
    请生成10个{level}难度的英语单词，要求：{level_prompts[level]}
    输出格式必须是严格的 JSON 列表，包含字段: words, meaning, notes。
    notes 要求：用赞美且幽默的口吻写出卿姐专属的助记方法。
    不要包含任何多余的文字，只返回 JSON。
    """

    try:
        # 这里预留 DeepSeek 标准 API 调用结构
        # headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        # response = requests.post("https://api.deepseek.com/v1/chat/completions", json={...}, headers=headers)
        # return response.json()['choices'][0]['message']['content']
        
        # 演示占位数据
        time.sleep(2)
        return [{"date": str(datetime.date.today()), "words": f"Word_{level}_{i}", "meaning": "含义", "notes": "卿姐最棒！"} for i in range(1, 11)]
    except Exception as e:
        st.error(f"AI 生成失败: {e}")
        return []

# ==========================================
# 3. 页面样式与布局
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFF9FB; }
    .word-card { 
        background: white; padding: 1.5rem; border-radius: 1rem; 
        border-left: 6px solid #FF4B4B; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem;
    }
    .level-box { background: #FFE4E1; padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; color: #D02090; }
    </style>
    """, unsafe_allow_html=True)

st.title("💃 卿姐英语加油站")

# 加载数据
gc = init_connection()
sh = gc.open("Mom_English_Study")
worksheet = sh.get_worksheet(0)
all_vals = worksheet.get_all_values()
df = pd.DataFrame(all_vals[1:], columns=all_vals[0]) if len(all_vals) > 1 else pd.DataFrame()

# 侧边栏：难度选择与设置
with st.sidebar:
    st.image("https://img.icons8.com/bubbles/200/woman-profile.png")
    st.header("⚙️ 学习偏好")
    selected_level = st.select_slider(
        "选择今日难度级别：",
        options=["🌱 元气生活", "✨ 时尚达人", "💪 职场精英"],
        value="✨ 时尚达人"
    )
    st.markdown(f'<div class="level-box">当前模式：{selected_level}</div>', unsafe_allow_html=True)
    st.divider()
    if st.button("📢 推送至卿姐微信"):
        st.toast("正在拼命连接微信服务器...")

# 主功能区
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战", "🔄 记忆复苏", "📚 学习档案"])

with tab1:
    st.subheader(f"🔥 卿姐，今日 {selected_level} 级别的 10 个新词已就绪！")
    
    if st.button("✨ 召唤 AI 生成今日单词"):
        with st.spinner(f"正在根据‘{selected_level}’难度为卿姐定制内容..."):
            st.session_state['new_words'] = generate_10_words_ai(selected_level)

    if 'new_words' in st.session_state:
        for item in st.session_state['new_words']:
            st.markdown(f"""
                <div class="word-card">
                    <h3 style="margin:0; color:#FF4B4B;">{item['words']}</h3>
                    <p><b>中文释义：</b>{item['meaning']}</p>
                    <p style="color:#555; background:#FDF5E6; padding:10px; border-radius:5px;">
                        <i>💡 卿姐专属助记：{item['notes']}</i>
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 确认并同步到云端表格", type="primary"):
            for item in st.session_state['new_words']:
                worksheet.append_row([item['date'], item['words'], item['meaning'], item['notes'], selected_level])
            st.success("同步成功！卿姐的学习记录又增加了。")
            time.sleep(1)
            st.rerun()

with tab2:
    st.subheader("🔁 艾宾浩斯记忆提醒")
    # 简单的复习筛选逻辑
    if not df.empty:
        # 这里可以根据之前写的 intervals [1, 3, 7] 进行筛选
        st.write("根据科学曲线，这些词卿姐可能快忘了，快温习一下：")
        st.dataframe(df.tail(10), use_container_width=True) # 演示显示最后10个
    else:
        st.info("暂无复习任务。")

with tab3:
    st.subheader("📚 卿姐的全量词库")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("档案室还是空的哦。")
