import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import random

# ==========================================
# 1. 核心认证与数据连接
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
# 2. 艾宾浩斯复习算法
# ==========================================
def get_ebbinghaus_reviews(log_df):
    if log_df.empty or 'date' not in log_df.columns: return pd.DataFrame()
    log_df['date_dt'] = pd.to_datetime(log_df['date'], errors='coerce').dt.date
    today = datetime.date.today()
    # 科学复习周期：1, 3, 7, 15天
    intervals = [1, 3, 7, 15]
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    return log_df[log_df['date_dt'].isin(target_dates)]

# ==========================================
# 3. 卿姐专属 UI 样式：助记增强 + 灵动交互
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    
    /* 🌟 助记增强卡片样式 */
    .word-card { 
        background: white; 
        padding: 2.5rem; 
        border-radius: 24px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-bottom: 25px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        border: 1px solid #F0F0F0;
        text-align: center;
        position: relative;
    }
    
    .word-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 40px rgba(208, 32, 144, 0.15);
        border-color: #D02090;
    }

    /* 单词大字报：视觉记忆冲击 */
    .big-word {
        font-family: 'Georgia', serif;
        font-size: 3.8rem;
        font-weight: 900;
        color: #2C3E50;
        margin: 15px 0;
        letter-spacing: -1px;
    }

    /* 释义：高亮粉色 */
    .meaning-tag {
        font-size: 1.6rem;
        color: #D02090;
        background: #FFF0F5;
        display: inline-block;
        padding: 8px 25px;
        border-radius: 50px;
        margin-bottom: 20px;
        font-weight: 500;
    }

    /* 词性勋章：色彩心理记忆 */
    .pos-badge {
        font-size: 0.85rem;
        text-transform: uppercase;
        padding: 5px 15px;
        border-radius: 8px;
        font-weight: bold;
    }
    .pos-verb { background: #E1F5FE; color: #0288D1; } 
    .pos-noun { background: #E8F5E9; color: #388E3C; }
    .pos-adj { background: #FFF3E0; color: #F57C00; }
    .pos-other { background: #F5F5F5; color: #616161; }

    /* 复习卡片：翻牌感设计 */
    .review-card {
        background: #F8F9FA; padding: 1.5rem; border-radius: 15px;
        border-top: 6px solid #D02090; margin-bottom: 10px; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 4. 数据中心：双表加载与自动纠错
# ==========================================
gc = init_connection()
try:
    # ⚠️ 请确保 Google Sheets 总文件名是 "Sheet1"
    sh = gc.open("Sheet1") 
except:
    st.error("❌ 找不到 Google Sheet 文件。请确认文件名叫 'Sheet1' 且已共享权限。")
    st.stop()

# --- A. 词库加载 (Sheet1) ---
ws_lib = sh.worksheet("Sheet1")
lib_data = ws_lib.get_all_values()
if len(lib_data) > 1:
    lib_df = pd.DataFrame(lib_data[1:], columns=lib_data[0])
    # 规范化列名，防止大小写/空格导致的 KeyError
    lib_df.columns = [c.lower().strip() for c in lib_df.columns]
    lib_df = lib_df.rename(columns={'words': 'word', 'chinese': 'chinese', 'category': 'category'})
else:
    lib_df = pd.DataFrame(columns=['word', 'chinese', 'category'])

# --- B. 记录加载 (Learning_Log) ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="10")
    ws_log.append_row(["date", "word", "chinese", "category", "level"])

log_all = ws_log.get_all_values()
log_df = pd.DataFrame(log_all[1:], columns=log_all[0]) if len(log_all) > 1 else pd.DataFrame(columns=["date", "word", "chinese", "category", "level"])

# ==========================================
# 5. 主页面功能布局
# ==========================================
st.title("💃 卿姐英语加油站")
st.caption(f"📅 学习日：{datetime.date.today()} | 每一个单词都是通往更优秀自己的阶梯。")

tab1, tab2, tab3 = st.tabs(["🌟 深度挑战", "🔄 记忆复苏", "📚 学习足迹"])

# 辅助函数：词性上色
def get_pos_class(pos_text):
    p = str(pos_text).lower()
    if 'v' in p: return "pos-verb"
    if 'n' in p: return "pos-noun"
    if 'adj' in p: return "pos-adj"
    return "pos-other"

# --- Tab 1: 深度挑战 ---
with tab1:
    with st.sidebar:
        st.header("⚙️ 卿姐调频")
        selected_level = st.select_slider("选择今日挑战等级：", options=["🌱 基础词汇", "✨ 进阶词汇", "💪 核心词汇"])
        st.divider()
        # CSV 下载备份功能
        if not log_df.empty:
            csv_data = log_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下载我的云端打卡档案", data=csv_data, file_name=f"卿姐学习记录_{datetime.date.today()}.csv")

    if st.button("🚀 开启今日助记之旅", use_container_width=True):
        if not lib_df.empty:
            if "基础" in selected_level: f = lib_df[lib_df['word'].str.len() <= 5]
            elif "进阶" in selected_level: f = lib_df[(lib_df['word'].str.len() > 5) & (lib_df['word'].str.len() <= 9)]
            else: f = lib_df[lib_df['word'].str.len() > 9]
            
            if not f.empty:
                st.session_state['batch'] = f.sample(min(len(f), 10)).to_dict('records')
            else:
                st.info("此难度库为空。")
    
    if 'batch' in st.session_state:
        for item in st.session_state['batch']:
            word = item.get('word', 'N/A')
            pos_style = get_pos_class(item.get('category', ''))
            st.markdown(f"""
                <div class="word-card">
                    <span class="pos-badge {pos_style}">{item.get('category', 'WORD')}</span>
                    <h1 class="big-word">{word}</h1>
                    <div class="meaning-tag">{item.get('chinese', 'N/A')}</div>
                    <div style="color:#999; font-size:0.85rem; border-top:1px dashed #EEE; padding-top:10px;">
                        💡 <b>助记：</b> 尝试联想一个包含 "{word}" 的场景 | 长度: {len(word)}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 卿姐记住了，同步到云端 Learning_Log", type="primary", use_container_width=True):
            for item in st.session_state['batch']:
                ws_log.append_row([str(datetime.date.today()), item.get('word'), item.get('chinese'), item.get('category'), selected_level])
            st.balloons() # 庆祝仪式感
            st.success("打卡成功！数据已实时存入 Google Sheets。")
            time.sleep(1)
            st.rerun()

# --- Tab 2: 记忆复苏 (艾宾浩斯) ---
with tab2:
    st.subheader("🔁 科学复习：你的记忆加油站")
    review_data = get_ebbinghaus_reviews(log_df)
    if not review_data.empty:
        cols = st.columns(2)
        for idx, row in enumerate(review_data.to_dict('records')):
            with cols[idx % 2]:
                st.markdown(f'<div class="review-card"><h4>{row["word"]}</h4></div>', unsafe_allow_html=True)
                with st.expander("揭晓答案"):
                    st.write(f"**中文**: {row['chinese']} | **词性**: {row['category']}")
    else:
        st.info("✨ 卿姐太棒了！今日暂无复习任务。")

# --- Tab 3: 学习足迹 ---
with tab3:
    st.subheader("📚 卿姐的学习足迹 (Learning_Log)")
    st.dataframe(log_df.sort_index(ascending=False), use_container_width=True)
