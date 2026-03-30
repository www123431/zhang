import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import base64
from io import BytesIO
from gtts import gTTS

# ==========================================
# 1. 核心认证与发音工具
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

def get_pronunciation_audio(word):
    """🎙️ 实时生成单词音频并转为 Base64"""
    try:
        tts = gTTS(text=word, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio src="data:audio/mp3;base64,{b64}" controls style="height:35px; width:100%; margin-top:15px;"></audio>'
    except:
        return ""

# ==========================================
# 2. 艾宾浩斯复习算法
# ==========================================
def get_ebbinghaus_reviews(df):
    if df.empty or 'date' not in df.columns: return pd.DataFrame()
    temp = df.copy()
    temp['date_dt'] = pd.to_datetime(temp['date'], errors='coerce').dt.date
    today = datetime.date.today()
    # 科学复习节点
    intervals = [1, 3, 7, 15]
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    return temp[temp['date_dt'].isin(target_dates)]

# ==========================================
# 3. 旗舰版 UI 样式 (助记增强)
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    .word-card { 
        background: white; padding: 2.5rem; border-radius: 24px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 25px;
        transition: all 0.4s ease; border: 1px solid #F0F0F0; text-align: center;
    }
    .word-card:hover { transform: translateY(-10px); border-color: #D02090; box-shadow: 0 20px 40px rgba(208, 32, 144, 0.15); }
    .big-word { font-family: 'Georgia', serif; font-size: 3.8rem; font-weight: 900; color: #2C3E50; margin: 15px 0; }
    .meaning-tag { font-size: 1.6rem; color: #D02090; background: #FFF0F5; padding: 8px 25px; border-radius: 50px; font-weight: bold; }
    .pos-badge { font-size: 0.85rem; text-transform: uppercase; padding: 5px 15px; border-radius: 8px; font-weight: bold; }
    .pos-verb { background: #E1F5FE; color: #0288D1; } 
    .pos-noun { background: #E8F5E9; color: #388E3C; }
    .pos-adj { background: #FFF3E0; color: #F57C00; }
    .pos-other { background: #F5F5F5; color: #616161; }
    .review-card { background: #F8F9FA; padding: 1.5rem; border-radius: 15px; border-top: 6px solid #D02090; margin-bottom: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 4. 数据中心 (双表联动 + 自动去重逻辑)
# ==========================================
gc = init_connection()
sh = gc.open("Sheet1") # 请确保主文件名为 Sheet1

# --- A. 词库加载 ---
ws_lib = sh.worksheet("Sheet1")
lib_data = ws_lib.get_all_values()
if len(lib_data) > 1:
    lib_df = pd.DataFrame(lib_data[1:], columns=lib_data[0])
    lib_df.columns = [c.lower().strip() for c in lib_df.columns]
    lib_df = lib_df.rename(columns={'words': 'word', 'chinese': 'chinese'})
else:
    lib_df = pd.DataFrame(columns=['word', 'chinese', 'category'])

# --- B. 记录加载与逻辑去重 ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="10")
    ws_log.append_row(["date", "word", "chinese", "category", "level"])

log_all = ws_log.get_all_values()
if len(log_all) > 1:
    raw_log_df = pd.DataFrame(log_all[1:], columns=log_all[0])
    raw_log_df.columns = [c.lower().strip() for c in raw_log_df.columns]
    raw_log_df = raw_log_df.rename(columns={'words': 'word'})
    # 逻辑去重：保留最新一条
    raw_log_df['sort_date'] = pd.to_datetime(raw_log_df['date'], errors='coerce')
    clean_log_df = raw_log_df.sort_values('sort_date', ascending=False).drop_duplicates(subset=['word'], keep='first')
    clean_log_df = clean_log_df.drop(columns=['sort_date'])
else:
    raw_log_df = pd.DataFrame(columns=["date", "word", "chinese", "category", "level"])
    clean_log_df = raw_log_df.copy()

# ==========================================
# 5. 交互模块
# ==========================================
st.title("💃 卿姐英语加油站")
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战", "🔄 记忆复苏", "📚 学习足迹"])

def get_style(p):
    p = str(p).lower()
    if 'v' in p: return "pos-verb"
    if 'n' in p: return "pos-noun"
    if 'adj' in p: return "pos-adj"
    return "pos-other"

# --- Tab 1: 挑战模式 ---
with tab1:
    with st.sidebar:
        st.header("⚙️ 难度调节")
        lvl = st.select_slider("选择难度：", options=["🌱 基础", "✨ 进阶", "💪 核心"])
        if not clean_log_df.empty:
            csv = clean_log_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下载唯一词汇档案", data=csv, file_name=f"卿姐词库_{datetime.date.today()}.csv")

    if st.button("🚀 开启今日挑战 (含发音)", use_container_width=True):
        if not lib_df.empty:
            if "基础" in lvl: f = lib_df[lib_df['word'].str.len() <= 5]
            elif "进阶" in lvl: f = lib_df[(lib_df['word'].str.len() > 5) & (lib_df['word'].str.len() <= 9)]
            else: f = lib_df[lib_df['word'].str.len() > 9]
            if not f.empty:
                st.session_state['batch'] = f.sample(min(len(f), 10)).to_dict('records')

    if 'batch' in st.session_state:
        for item in st.session_state['batch']:
            word = item.get('word', 'N/A')
            audio = get_pronunciation_audio(word)
            st.markdown(f"""<div class="word-card">
                <span class="pos-badge {get_style(item.get('category'))}">{item.get('category', 'WORD')}</span>
                <h1 class="big-word">{word}</h1>
                <div class="meaning-tag">{item.get('chinese', 'N/A')}</div>
                {audio}
            </div>""", unsafe_allow_html=True)
        
        if st.button("✅ 卿姐记住了，同步云端", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('chinese'), i.get('category'), lvl])
            st.balloons()
            st.success("同步成功！")
            time.sleep(1)
            st.rerun()

# --- Tab 2: 记忆复苏 ---
with tab2:
    st.subheader("🔁 艾宾浩斯复习节点")
    rev = get_ebbinghaus_reviews(raw_log_df)
    if not rev.empty:
        rev = rev.drop_duplicates(subset=['word'])
        cols = st.columns(2)
        for idx, row in enumerate(rev.to_dict('records')):
            with cols[idx % 2]:
                st.markdown(f'<div class="review-card"><h4>{row["word"]}</h4></div>', unsafe_allow_html=True)
                with st.expander("看答案"): st.write(row['chinese'])
    else:
        st.info("今日暂无复习任务。")

# --- Tab 3: 足迹 (去重版) ---
with tab3:
    st.subheader("📚 唯一词汇档案")
    if not clean_log_df.empty:
        st.dataframe(clean_log_df, use_container_width=True)
    else:
        st.write("暂无记录。")
