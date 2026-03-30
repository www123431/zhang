import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time

# ==========================================
# 1. 核心认证
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
    intervals = [1, 3, 7, 15]
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    return log_df[log_df['date_dt'].isin(target_dates)]

# ==========================================
# 3. UI 样式
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
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 4. 数据加载 (双表逻辑)
# ==========================================
gc = init_connection()
try:
    sh = gc.open("Sheet1") # 对应你的总文件名
except:
    st.error("❌ 找不到总文件，请检查文件名是否叫 'Sheet1'。")
    st.stop()

# --- A. 加载词库 (Sheet1 标签页) ---
ws_lib = sh.worksheet("Sheet1")
lib_data = ws_lib.get_all_values()
if len(lib_data) > 1:
    lib_df = pd.DataFrame(lib_data[1:], columns=lib_data[0])
    # 统一列名为小写并去除空格，防止 KeyError
    lib_df.columns = [c.lower().strip() for c in lib_df.columns]
    # 针对你上传的截图(Word, Chinese, Category)做映射
    name_map = {'word': 'word', 'words': 'word', 'chinese': 'chinese', 'category': 'category'}
    lib_df = lib_df.rename(columns=name_map)
else:
    lib_df = pd.DataFrame(columns=['word', 'chinese', 'category'])

# --- B. 加载/初始化记录 (Learning_Log 标签页) ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="10")
    ws_log.append_row(["date", "word", "chinese", "category", "level"])

log_all = ws_log.get_all_values()
if len(log_all) > 1:
    log_df = pd.DataFrame(log_all[1:], columns=log_all[0])
else:
    log_df = pd.DataFrame(columns=["date", "word", "chinese", "category", "level"])

# ==========================================
# 5. 主页面
# ==========================================
st.title("💃 卿姐英语加油站")
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战", "🔄 记忆复苏", "📚 学习足迹"])

with tab1:
    selected_level = st.select_slider("选择难度：", options=["🌱 简单", "✨ 中等", "💪 挑战"])
    
    if st.button("🚀 抽取 10 个新词"):
        if not lib_df.empty:
            # 根据长度过滤
            if "简单" in selected_level:
                f = lib_df[lib_df['word'].str.len() <= 5]
            elif "中等" in selected_level:
                f = lib_df[(lib_df['word'].str.len() > 5) & (lib_df['word'].str.len() <= 9)]
            else:
                f = lib_df[lib_df['word'].str.len() > 9]
            
            if not f.empty:
                st.session_state['today_batch'] = f.sample(min(len(f), 10)).to_dict('records')
            else:
                st.info("此难度下库里没词了，去上传或换个难度吧。")
        else:
            st.warning("词库为空。")

    if 'today_batch' in st.session_state:
        for item in st.session_state['today_batch']:
            st.markdown(f"""
                <div class="word-card">
                    <h3 style="margin:0; color:#FF4B4B;">{item.get('word')}</h3>
                    <p style="margin-top:10px;"><b>解释：</b>{item.get('chinese')}</p>
                    <p style="color:gray; font-size:0.8rem;">分类: {item.get('category')}</p>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 卿姐学完了，存入云端记录", type="primary", use_container_width=True):
            for item in st.session_state['today_batch']:
                # 核心：写入 Learning_Log 表
                ws_log.append_row([
                    str(datetime.date.today()), 
                    item.get('word'), 
                    item.get('chinese'), 
                    item.get('category'), 
                    selected_level
                ])
            st.success("🎉 记录成功！快去 '学习足迹' 标签页看看，表里有数据了！")
            time.sleep(1)
            st.rerun()

with tab2:
    st.subheader("🔁 艾宾浩斯复习")
    review_data = get_ebbinghaus_reviews(log_df)
    if not review_data.empty:
        cols = st.columns(2)
        for idx, row in enumerate(review_data.to_dict('records')):
            with cols[idx % 2]:
                st.markdown(f'<div class="review-card"><h4>{row["word"]}</h4></div>', unsafe_allow_html=True)
                with st.expander("揭晓答案"):
                    st.write(f"**中文**: {row['chinese']}")
    else:
        st.info("今天暂无复习任务。")

with tab3:
    st.write("📊 学习记录 (Learning_Log):")
    st.dataframe(log_df.sort_index(ascending=False))
