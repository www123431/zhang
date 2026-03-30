import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import random

# ==========================================
# 1. 核心认证 (使用已验证的 Secrets 逻辑)
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
# 2. 艾宾浩斯复习算法 & 难度过滤
# ==========================================
def get_ebbinghaus_reviews(df):
    """根据遗忘曲线节点回溯筛选"""
    if df.empty: return pd.DataFrame()
    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    today = datetime.date.today()
    intervals = [1, 3, 7, 15] # 复习周期
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    return df[df['date_dt'].isin(target_dates)]

def filter_by_length(df, level):
    """根据单词长度筛选难度"""
    if df.empty: return pd.DataFrame()
    if level == "🌱 简单 (长度 < 5)":
        return df[df['words'].str.len() <= 5]
    elif level == "✨ 中等 (长度 6-9)":
        return df[(df['words'].str.len() >= 6) & (df['words'].str.len() <= 9)]
    else: # 💪 挑战
        return df[df['words'].str.len() >= 10]

# ==========================================
# 3. 页面配置与 UI 美化
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFF9FB; }
    /* 今日挑战卡片 */
    .word-card { 
        background: white; padding: 1.5rem; border-radius: 1rem; 
        border-left: 6px solid #FF4B4B; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem;
    }
    /* 复习卡片 */
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
st.write(f"今天是 {datetime.date.today()} | 卿姐，保持优雅，持续进阶！✨")

# 连接表格
gc = init_connection()
sh = gc.open("Mom_English_Study")
worksheet = sh.get_worksheet(0)
all_vals = worksheet.get_all_values()

# 初始化 DataFrame (增加对 C1, D1 为空的鲁棒性处理)
if len(all_vals) > 1:
    headers = all_vals[0]
    # 如果表头有空，自动填充
    clean_headers = [h if h.strip() else f"col_{i}" for i, h in enumerate(headers)]
    df = pd.DataFrame(all_vals[1:], columns=clean_headers)
    # 统一列名引用
    df.columns = ['date', 'words', 'meaning', 'notes', 'level'] + list(df.columns[5:])
else:
    df = pd.DataFrame(columns=["date", "words", "meaning", "notes", "level"])

# ==========================================
# 4. 侧边栏：配置中心
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/bubbles/200/woman-profile.png")
    st.header("⚙️ 学习调频")
    
    # 难度分级调节
    selected_level = st.select_slider(
        "调节今日难度：",
        options=["🌱 简单 (长度 < 5)", "✨ 中等 (长度 6-9)", "💪 挑战 (长度 > 10)"],
        value="✨ 中等 (长度 6-9)"
    )
    
    st.divider()
    
    # 词书上传
    st.subheader("📚 导入新词书")
    uploaded_file = st.file_uploader("上传 CSV (格式: 单词,意思,助记)", type="csv")
    if uploaded_file:
        up_df = pd.read_csv(uploaded_file)
        if st.button("📥 点击导入云端"):
            with st.spinner("同步中..."):
                for _, row in up_df.iterrows():
                    worksheet.append_row([str(datetime.date.today()), str(row[0]), str(row[1]), str(row[2]), "词书上传"])
                st.success("导入成功！刷新后即可学习。")
                time.sleep(1)
                st.rerun()

# ==========================================
# 5. 主功能 Tabs
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战 (10词)", "🔄 记忆复苏 (卡片)", "📚 学习档案"])

# --- Tab 1: 今日挑战 ---
with tab1:
    st.subheader(f"🔥 卿姐，今日任务：{selected_level}")
    
    if st.button("🚀 开始今日 10 个词学习"):
        # 从总库中筛选出符合长度的词，随机抽10个
        filtered_df = filter_by_length(df, selected_level)
        
        if len(filtered_df) >= 10:
            st.session_state['today_batch'] = filtered_df.sample(10).to_dict('records')
        elif not filtered_df.empty:
            st.warning(f"符合要求的词只有 {len(filtered_df)} 个。")
            st.session_state['today_batch'] = filtered_df.to_dict('records')
        else:
            st.info("当前词库没有符合该难度的词，请先上传词书。")

    if 'today_batch' in st.session_state:
        for item in st.session_state['today_batch']:
            st.markdown(f"""
                <div class="word-card">
                    <div class="level-tag">{selected_level}</div>
                    <h3 style="margin:0; color:#FF4B4B;">{item['words']}</h3>
                    <p style="margin-top:10px;"><b>释义：</b>{item['meaning']}</p>
                    <p style="color:#666; font-size:0.9rem; background:#FDF5E6; padding:8px; border-radius:5px;">
                        <i>💡 助记：{item['notes']}</i>
                    </p>
                </div>
            """, unsafe_allow_html=True)
        st.success("卿姐今天也超棒的！奖励一朵小红花 🌹")

# --- Tab 2: 记忆复苏 (艾宾浩斯) ---
with tab2:
    st.subheader("🔁 科学复习：这些词快飞走了")
    
    review_df = get_ebbinghaus_reviews(df)
    
    if not review_df.empty:
        st.caption(f"📢 根据艾宾浩斯曲线，今日建议温习 {len(review_df)} 个词")
        cols = st.columns(2)
        for idx, row in enumerate(review_df.to_dict('records')):
            with cols[idx % 2]:
                st.markdown(f"""
                    <div class="review-card">
                        <span style="font-size:0.7rem; color:gray;">📅 首次学习: {row['date']}</span>
                        <h4 style="margin:8px 0; color:#D02090;">{row['words']}</h4>
                    </div>
                """, unsafe_allow_html=True)
                with st.expander("👀 揭晓答案"):
                    st.write(f"**意思**: {row['meaning']}")
                    st.info(f"**助记**: {row['notes']}")
    else:
        st.info("✨ 卿姐，目前没有复习任务，记忆力 Max！")

# --- Tab 3: 学习档案 ---
with tab3:
    st.subheader("📚 卿姐的学习足迹")
    if not df.empty:
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("档案室还是空的。")
