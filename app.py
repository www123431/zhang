import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import random

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
# 2. 艾宾浩斯复习算法 (基于 Learning_Log 表)
# ==========================================
def get_ebbinghaus_reviews(log_df):
    """从学习记录中根据日期回溯筛选"""
    if log_df.empty: return pd.DataFrame()
    
    log_df['date_dt'] = pd.to_datetime(log_df['date'], errors='coerce').dt.date
    today = datetime.date.today()
    
    # 艾宾浩斯周期：1, 3, 7, 15天
    intervals = [1, 3, 7, 15]
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    
    return log_df[log_df['date_dt'].isin(target_dates)]

# ==========================================
# 3. 页面样式
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFF9FB; }
    .word-card { 
        background: white; padding: 1.5rem; border-radius: 1rem; 
        border-left: 6px solid #FF4B4B; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem;
    }
    .review-card {
        background: #F8F9FA; padding: 1.2rem; border-radius: 0.8rem;
        border-top: 4px solid #D02090; margin-bottom: 0.5rem; text-align: center;
    }
    .level-tag {
        display: inline-block; padding: 2px 8px; border-radius: 5px;
        background: #FFE4E1; color: #D02090; font-size: 0.75rem; margin-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💃 卿姐英语加油站")

# 加载数据
gc = init_connection()

# --- 注意：这里改为你最新的 Google Sheet 总文件名 ---
try:
    # 如果你的总文件名叫 "Mom_English_Study"，请保持不变；
    # 如果你把整个文件也改名了，请修改此处引号内的内容
    sh = gc.open("Sheet1") 
except gspread.exceptions.SpreadsheetNotFound:
    st.error("❌ 找不到名为 'Sheet1' 的文件。请检查文件名或共享权限。")
    st.stop()

# --- 4. 读取工作表 ---

# 读取 Sheet1 (原始词库)
ws_library = sh.worksheet("Sheet1") 
lib_data = ws_library.get_all_values()
if len(lib_data) > 1:
    # 自动识别你的词书表头：Index, Word, Category, Chinese
    lib_df = pd.DataFrame(lib_data[1:], columns=lib_data[0])
else:
    lib_df = pd.DataFrame(columns=["Index", "Word", "Category", "Chinese"])

# 读取 Learning_Log (学习记录)
try:
    ws_log = sh.worksheet("Learning_Log")
except gspread.exceptions.WorksheetNotFound:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="10")
    ws_log.append_row(["date", "words", "meaning", "notes", "level"])

log_data = ws_log.get_all_values()
if len(log_data) > 1:
    log_df = pd.DataFrame(log_data[1:], columns=log_data[0])
else:
    log_df = pd.DataFrame(columns=["date", "words", "meaning", "notes", "level"])

# ==========================================
# 5. 侧边栏与主功能 (保持之前逻辑)
# ==========================================
with st.sidebar:
    st.header("⚙️ 学习配置")
    selected_level = st.select_slider(
        "调节今日难度：",
        options=["🌱 简单 (长度 <= 5)", "✨ 中等 (长度 6-9)", "💪 挑战 (长度 >= 10)"],
        value="🌱 简单 (长度 <= 5)"
    )
    st.divider()
    st.subheader("📚 导入卿姐专属词书")
    uploaded_file = st.file_uploader("上传 CSV (格式: Index, Word, Category, Chinese)", type="csv")
    if uploaded_file:
        up_df = pd.read_csv(uploaded_file)
        if st.button("📥 存入 Sheet1 词库"):
            with st.spinner("同步中..."):
                ws_library.clear()
                ws_library.update([up_df.columns.values.tolist()] + up_df.values.tolist())
                st.success("词库已存入 Sheet1！")
                st.rerun()

tab1, tab2, tab3 = st.tabs(["🌟 今日挑战", "🔄 记忆复苏", "📚 学习档案"])

with tab1:
    st.subheader(f"🔥 今日任务：{selected_level}")
    if st.button("🚀 抽取 10 个词"):
        if not lib_df.empty:
            # 这里的 Word 对应你词书里的列名
            if selected_level == "🌱 简单 (长度 <= 5)":
                filtered = lib_df[lib_df['Word'].str.len() <= 5]
            elif selected_level == "✨ 中等 (长度 6-9)":
                filtered = lib_df[(lib_df['Word'].str.len() >= 6) & (lib_df['Word'].str.len() <= 9)]
            else:
                filtered = lib_df[lib_df['Word'].str.len() >= 10]
            
            if not filtered.empty:
                st.session_state['quiz'] = filtered.sample(min(len(filtered), 10)).to_dict('records')
            else:
                st.info("该难度下暂无单词。")
        else:
            st.warning("Sheet1 是空的，请先上传词书。")

    if 'quiz' in st.session_state:
        for item in st.session_state['quiz']:
            st.markdown(f"""
                <div class="word-card">
                    <h3 style="margin:0; color:#FF4B4B;">{item['Word']}</h3>
                    <p><b>中文：</b>{item['Chinese']}</p>
                    <p style="font-size:0.8rem; color:gray;">词性: {item['Category']}</p>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 卿姐学完了，记入 Learning_Log", type="primary"):
            for item in st.session_state['quiz']:
                # 存入第二个表：日期, 单词, 释义, 笔记, 难度
                ws_log.append_row([str(datetime.date.today()), item['Word'], item['Chinese'], item['Category'], selected_level])
            st.success("记录成功！")
            time.sleep(1)
            st.rerun()

with tab2:
    st.subheader("🔄 记忆复苏 (基于 Learning_Log)")
    review_df = get_ebbinghaus_reviews(log_df)
    if not review_df.empty:
        cols = st.columns(2)
        for idx, row in enumerate(review_df.to_dict('records')):
            with cols[idx % 2]:
                st.markdown(f'<div class="review-card"><h4>{row["words"]}</h4></div>', unsafe_allow_html=True)
                with st.expander("揭晓答案"):
                    st.write(f"**意思**: {row['meaning']}")
    else:
        st.info("✨ 卿姐，Learning_Log 里暂时没有需要复习的任务。")

with tab3:
    st.write("📊 卿姐的学习足迹 (Learning_Log):")
    st.dataframe(log_df, use_container_width=True)
