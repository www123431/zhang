import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time

# ==========================================
# 1. 核心认证与连接 (GCP)
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
        st.error(f"❌ 认证失败，请检查 Secrets 配置: {e}")
        st.stop()

# ==========================================
# 2. 艾宾浩斯复习逻辑 (科学回溯)
# ==========================================
def get_ebbinghaus_reviews(df):
    if df.empty or 'date' not in df.columns:
        return pd.DataFrame()
    temp = df.copy()
    # 转换为日期格式进行计算
    temp['date_dt'] = pd.to_datetime(temp['date'], errors='coerce').dt.date
    today = datetime.date.today()
    # 遗忘曲线关键节点：1, 3, 7, 15 天
    target_dates = [today - datetime.timedelta(days=i) for i in [1, 3, 7, 15]]
    return temp[temp['date_dt'].isin(target_dates)]

# ==========================================
# 3. 卿姐专属 UI 样式 (灵动助记版)
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    /* 助记卡片 */
    .word-card { 
        background: white; padding: 2.5rem; border-radius: 24px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 25px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        border: 1px solid #F0F0F0; text-align: center;
    }
    .word-card:hover { transform: translateY(-10px); border-color: #D02090; box-shadow: 0 15px 40px rgba(208, 32, 144, 0.15); }
    .big-word { font-family: 'Georgia', serif; font-size: 3.8rem; font-weight: 900; color: #2C3E50; margin: 15px 0; }
    .meaning-tag { font-size: 1.6rem; color: #D02090; background: #FFF0F5; padding: 8px 25px; border-radius: 50px; font-weight: bold; }
    /* 词性样式 */
    .pos-badge { font-size: 0.85rem; text-transform: uppercase; padding: 5px 15px; border-radius: 8px; font-weight: bold; }
    .pos-verb { background: #E1F5FE; color: #0288D1; } 
    .pos-noun { background: #E8F5E9; color: #388E3C; }
    .pos-adj { background: #FFF3E0; color: #F57C00; }
    .pos-other { background: #F5F5F5; color: #616161; }
    /* 复习卡片 */
    .review-card { background: #F8F9FA; padding: 1.5rem; border-radius: 15px; border-top: 6px solid #D02090; margin-bottom: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 4. 数据中心 (全功能容错逻辑)
# ==========================================
gc = init_connection()
try:
    sh = gc.open("Sheet1")
except:
    st.error("❌ 找不到 Google Sheet 文件 'Sheet1'。请确保文件名正确且已共享。")
    st.stop()

# --- A. 词库加载 (Sheet1) ---
ws_lib = sh.worksheet("Sheet1")
lib_data = ws_lib.get_all_values()
if len(lib_data) > 1:
    lib_df = pd.DataFrame(lib_data[1:], columns=lib_data[0])
    lib_df.columns = [c.lower().strip() for c in lib_df.columns]
    # 兼容 words/word, chinese/meanings 等写法
    lib_df = lib_df.rename(columns={'words': 'word', 'chinese': 'chinese', 'category': 'category'})
else:
    lib_df = pd.DataFrame(columns=['word', 'chinese', 'category'])

# --- B. 记录加载与【去重保护】逻辑 ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="10")
    ws_log.append_row(["date", "word", "chinese", "category", "level"])

log_all = ws_log.get_all_values()
raw_log_df = pd.DataFrame(columns=["date", "word", "chinese", "category", "level"])
clean_log_df = raw_log_df.copy()

if len(log_all) > 1:
    raw_log_df = pd.DataFrame(log_all[1:], columns=log_all[0])
    # 格式化列名
    raw_log_df.columns = [c.lower().strip() for c in raw_log_df.columns]
    raw_log_df = raw_log_df.rename(columns={'words': 'word'})
    
    # 【核心修复】：只有当 'word' 列确实存在时才进行去重，否则直接展示
    if 'word' in raw_log_df.columns:
        try:
            # 增加一个临时排序列
            temp_sort = raw_log_df.copy()
            temp_sort['sort_date'] = pd.to_datetime(temp_sort['date'], errors='coerce')
            # 按日期降序，保留第一个（即最新一个）单词
            clean_log_df = temp_sort.sort_values('sort_date', ascending=False).drop_duplicates(subset=['word'], keep='first')
            clean_log_df = clean_log_df.drop(columns=['sort_date'])
        except:
            clean_log_df = raw_log_df
    else:
        clean_log_df = raw_log_df
else:
    # 如果表是空的，clean_log_df 就是初始化的空表
    pass

# ==========================================
# 5. 主页面交互
# ==========================================
st.title("💃 卿姐英语加油站")
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战", "🔄 记忆复苏", "📚 学习足迹"])

# 辅助函数：词性样式
def get_pos_style(txt):
    t = str(txt).lower()
    if 'v' in t: return "pos-verb"
    if 'n' in t: return "pos-noun"
    if 'adj' in t: return "pos-adj"
    return "pos-other"

# --- Tab 1: 今日挑战 ---
with tab1:
    with st.sidebar:
        st.header("⚙️ 卿姐调频")
        lvl = st.select_slider("选择挑战难度：", options=["🌱 基础词汇", "✨ 进阶词汇", "💪 核心词汇"])
        st.divider()
        if not clean_log_df.empty:
            # 提供去重后的 CSV 下载
            csv = clean_log_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下载我的唯一词库", data=csv, file_name=f"卿姐词库_{datetime.date.today()}.csv")

    if st.button("🚀 开启今日助记之旅", use_container_width=True):
        if not lib_df.empty:
            # 简单的长度分级逻辑
            if "基础" in lvl: f = lib_df[lib_df['word'].str.len() <= 5]
            elif "进阶" in lvl: f = lib_df[(lib_df['word'].str.len() > 5) & (lib_df['word'].str.len() <= 9)]
            else: f = lib_df[lib_df['word'].str.len() > 9]
            
            if not f.empty:
                st.session_state['current_batch'] = f.sample(min(len(f), 10)).to_dict('records')
            else:
                st.info("此难度库暂无单词，请尝试其他难度。")

    if 'current_batch' in st.session_state:
        for item in st.session_state['current_batch']:
            word = item.get('word', 'N/A')
            st.markdown(f"""
                <div class="word-card">
                    <span class="pos-badge {get_pos_style(item.get('category'))}">{item.get('category', 'WORD')}</span>
                    <h1 class="big-word">{word}</h1>
                    <div class="meaning-tag">{item.get('chinese', 'N/A')}</div>
                    <div style="color:#999; font-size:0.85rem; border-top:1px dashed #EEE; padding-top:15px; margin-top:15px;">
                        💡 <b>助记提示：</b> 长度 {len(word)} | 尝试联想一个工作场景。
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 卿姐记住了，同步云端档案", type="primary", use_container_width=True):
            for i in st.session_state['current_batch']:
                # 实时写入 Google Sheet
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('chinese'), i.get('category'), lvl])
            st.balloons()
            st.success("打卡成功！数据已存入 Learning_Log 表格。")
            time.sleep(1)
            st.rerun()

# --- Tab 2: 记忆复苏 (艾宾浩斯) ---
with tab2:
    st.subheader("🔁 科学复习")
    reviews = get_ebbinghaus_reviews(raw_log_df)
    if not reviews.empty:
        # 复习展示也去重
        reviews = reviews.drop_duplicates(subset=['word'])
        cols = st.columns(2)
        for idx, row in enumerate(reviews.to_dict('records')):
            with cols[idx % 2]:
                st.markdown(f'<div class="review-card"><h4>{row["word"]}</h4></div>', unsafe_allow_html=True)
                with st.expander("揭晓答案"):
                    st.write(f"**中文**: {row['chinese']} | **分类**: {row['category']}")
    else:
        st.info("✨ 卿姐，今日暂无复习任务。")

# --- Tab 3: 学习足迹 (去重展示) ---
with tab3:
    st.subheader("📚 唯一词汇足迹")
    if not clean_log_df.empty:
        st.caption("此处仅展示每个单词最近一次的学习记录，已自动去重。")
        st.dataframe(clean_log_df, use_container_width=True)
    else:
        st.info("档案室还是空的，快去打卡吧！")
