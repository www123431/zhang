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
    
    # 确保日期列格式正确
    log_df['date_dt'] = pd.to_datetime(log_df['date'], errors='coerce').dt.date
    today = datetime.date.today()
    
    # 艾宾浩斯关键节点：1天前, 3天前, 7天前, 15天前
    intervals = [1, 3, 7, 15]
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    
    # 筛选出刚好处于复习节点的单词
    return log_df[log_df['date_dt'].isin(target_dates)]

# ==========================================
# 3. 页面样式美化
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
sh = gc.open("Mom_English_Study")

# --- 读取 Sheet1: 原始词库 ---
ws_library = sh.get_worksheet(0) # 第一个表
lib_data = ws_library.get_all_values()
if len(lib_data) > 1:
    lib_df = pd.DataFrame(lib_data[1:], columns=lib_data[0])
else:
    lib_df = pd.DataFrame(columns=["Index", "Word", "Category", "Chinese"])

# --- 读取 Learning_Log: 学习记录 ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    # 如果不存在则创建
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="10")
    ws_log.append_row(["date", "words", "meaning", "notes", "level"])

log_data = ws_log.get_all_values()
if len(log_data) > 1:
    log_df = pd.DataFrame(log_data[1:], columns=log_data[0])
else:
    log_df = pd.DataFrame(columns=["date", "words", "meaning", "notes", "level"])

# ==========================================
# 4. 侧边栏：配置中心
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/bubbles/200/woman-profile.png")
    st.header("⚙️ 学习配置")
    
    # 难度分级（基于长度）
    selected_level = st.select_slider(
        "调节今日难度：",
        options=["🌱 简单 (长度 <= 5)", "✨ 中等 (长度 6-9)", "💪 挑战 (长度 >= 10)"],
        value="🌱 简单 (长度 <= 5)"
    )
    
    st.divider()
    
    # 词书上传 (存入 Sheet1)
    st.subheader("📚 导入卿姐专属词书")
    uploaded_file = st.file_uploader("上传 CSV (格式: Index, Word, Category, Chinese)", type="csv")
    if uploaded_file:
        up_df = pd.read_csv(uploaded_file)
        if st.button("📥 存入主词库"):
            with st.spinner("正在同步词库..."):
                # 清空旧词库并写入新词库（或者用 append_rows 追加）
                ws_library.clear()
                ws_library.update([up_df.columns.values.tolist()] + up_df.values.tolist())
                st.success("词库更新成功！")
                st.rerun()

# ==========================================
# 5. 主功能 Tabs
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战 (10词)", "🔄 记忆复苏 (卡片)", "📚 学习记录"])

# --- Tab 1: 今日挑战 (从词库抽题，存入记录) ---
with tab1:
    st.subheader(f"🔥 卿姐，今日挑战：{selected_level}")
    
    if st.button("🚀 抽取 10 个新词"):
        # 长度过滤逻辑
        if not lib_df.empty:
            if selected_level == "🌱 简单 (长度 <= 5)":
                filtered = lib_df[lib_df['Word'].str.len() <= 5]
            elif selected_level == "✨ 中等 (长度 6-9)":
                filtered = lib_df[(lib_df['Word'].str.len() >= 6) & (lib_df['Word'].str.len() <= 9)]
            else:
                filtered = lib_df[lib_df['Word'].str.len() >= 10]
            
            if len(filtered) >= 10:
                st.session_state['today_quiz'] = filtered.sample(10).to_dict('records')
            else:
                st.session_state['today_quiz'] = filtered.to_dict('records')
                st.warning(f"词库中该难度的词不足 10 个，已全部展示。")
        else:
            st.info("词库是空的，请先在侧边栏上传词书。")

    if 'today_quiz' in st.session_state:
        for item in st.session_state['today_quiz']:
            st.markdown(f"""
                <div class="word-card">
                    <div class="level-tag">{selected_level}</div>
                    <h3 style="margin:0; color:#FF4B4B;">{item['Word']}</h3>
                    <p style="margin-top:10px;"><b>中文：</b>{item['Chinese']}</p>
                    <p style="color:#666; font-size:0.85rem;"><i>💡 词性: {item['Category']}</i></p>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 卿姐学完了，打卡记录！", type="primary", use_container_width=True):
            for item in st.session_state['today_quiz']:
                # 将学习结果存入 Learning_Log 表
                ws_log.append_row([str(datetime.date.today()), item['Word'], item['Chinese'], item['Category'], selected_level])
            st.success("打卡成功！这些词已加入艾宾浩斯复习计划。")
            time.sleep(1)
            st.rerun()

# --- Tab 2: 记忆复苏 (从学习记录中提取) ---
with tab2:
    st.subheader("🔁 科学复习：卿姐的记忆加油站")
    # 算法只跑在 log_df 上
    review_data = get_ebbinghaus_reviews(log_df)
    
    if not review_data.empty:
        st.caption(f"📢 卿姐，这 {len(review_data)} 个词按照遗忘曲线该复习啦：")
        cols = st.columns(2)
        for idx, row in enumerate(review_data.to_dict('records')):
            with cols[idx % 2]:
                st.markdown(f'<div class="review-card"><h4>{row["words"]}</h4></div>', unsafe_allow_html=True)
                with st.expander("👀 揭晓答案"):
                    st.write(f"**中文**: {row['meaning']}")
                    st.write(f"**词性**: {row['notes']}")
    else:
        st.info("✨ 卿姐，目前没有复习任务，记忆超赞！")

# --- Tab 3: 学习记录 ---
with tab3:
    st.subheader("📚 卿姐的学习足迹")
    st.dataframe(log_df.sort_index(ascending=False), use_container_width=True)
