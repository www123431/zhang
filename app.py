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
# 1. 核心后台：安全认证与多模态工具
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
        st.error(f"❌ 认证失败，请检查 Secrets 配置: {e}"); st.stop()

def get_pronunciation_audio(word):
    """🎙️ 生成单词发音音频"""
    try:
        tts = gTTS(text=word, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio src="data:audio/mp3;base64,{b64}" controls style="height:32px; width:100%; margin-top:15px; border-radius:10px;"></audio>'
    except: return ""

# ==========================================
# 2. 卿姐专属 UI 视觉语言
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    .word-card { 
        background: white; padding: 2.8rem; border-radius: 28px; 
        box-shadow: 0 12px 35px rgba(0,0,0,0.06); margin-bottom: 30px;
        text-align: center; border: 1px solid #F2F2F2;
    }
    .big-word { font-family: 'Georgia', serif; font-size: 4rem; font-weight: 900; color: #2C3E50; margin: 10px 0; }
    .meaning-tag { font-size: 1.7rem; color: #D02090; background: #FFF0F5; padding: 10px 35px; border-radius: 60px; font-weight: 600; display: inline-block; }
    .pos-badge { font-size: 0.85rem; text-transform: uppercase; padding: 6px 16px; border-radius: 10px; font-weight: 800; background: #F5F5F5; color: #616161; }
    .review-card { background: white; padding: 1.5rem; border-radius: 18px; border-left: 6px solid #D02090; margin-bottom: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 数据中心 (适配 meaning & notes)
# ==========================================
gc = init_connection()
sh = gc.open("Sheet1")

# --- A. 词库读取 (Sheet1) ---
ws_lib = sh.worksheet("Sheet1")
lib_raw = ws_lib.get_all_values()
# 强制清理表头名（转小写、去空格），确保代码逻辑一致
lib_df = pd.DataFrame(lib_raw[1:], columns=[c.lower().strip() for c in lib_raw[0]]) if len(lib_raw)>1 else pd.DataFrame()

# --- B. 日志读取 (Learning_Log) ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="5")
    ws_log.append_row(["date", "word", "meaning", "notes", "level"])

log_raw = ws_log.get_all_values()
raw_log_df = pd.DataFrame(log_raw[1:], columns=[c.lower().strip() for c in log_raw[0]]) if len(log_raw)>1 else pd.DataFrame()

# 数据清洗去重（用于足迹展示）
if not raw_log_df.empty:
    clean_log_df = raw_log_df.drop_duplicates(subset=['word'], keep='last')
else:
    clean_log_df = pd.DataFrame(columns=["date", "word", "meaning", "notes", "level"])

# ==========================================
# 4. 页面功能逻辑
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战", "🔄 记忆复苏", "📚 学习足迹"])

# --- Tab 1: 挑战与同步 ---
with tab1:
    lvl = st.select_slider("强度：", options=["🌱 基础", "✨ 进阶", "💪 核心"])
    if st.button("🚀 开启今日助记之旅", use_container_width=True):
        if not lib_df.empty:
            st.session_state['batch'] = lib_df.sample(min(len(lib_df), 8)).to_dict('records')

    if 'batch' in st.session_state:
        for item in st.session_state['batch']:
            word = item.get('word', 'N/A')
            st.markdown(f"""
                <div class="word-card">
                    <span class="pos-badge">{item.get('notes', 'Vocabulary')}</span>
                    <h1 class="big-word">{word}</h1>
                    <div class="meaning-tag">{item.get('meaning', '未找到释义')}</div>
                    {get_pronunciation_audio(word)}
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 卿姐记住了，同步云端", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                # 严格按照列名写入：meaning 和 notes
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('meaning'), i.get('notes'), lvl])
            st.balloons(); st.rerun()

# --- Tab 2: 艾宾浩斯复习提醒 ---
with tab2:
    st.subheader("🔄 记忆复苏节点")
    if not raw_log_df.empty:
        raw_log_df['date_dt'] = pd.to_datetime(raw_log_df['date'], errors='coerce').dt.date
        today = datetime.date.today()
        # 科学节点：1, 3, 7天前打卡的词
        target_dates = [today - datetime.timedelta(days=i) for i in [1, 3, 7]]
        rev_df = raw_log_df[raw_log_df['date_dt'].isin(target_dates)].drop_duplicates('word')
        
        if not rev_df.empty:
            cols = st.columns(2)
            for idx, row in enumerate(rev_df.to_dict('records')):
                with cols[idx % 2]:
                    st.markdown(f"""<div class="review-card">
                        <h3>{row.get('word')}</h3>
                        <p style="color:#7F8C8D;">上次打卡：{row.get('date')}</p>
                    </div>""", unsafe_allow_html=True)
                    with st.expander("🔍 揭晓答案"):
                        st.write(f"**释义**: {row.get('meaning')}")
                        st.write(f"**笔记**: {row.get('notes')}")
        else:
            st.info("✨ 今日暂无需要复习的词，非常棒！")

# --- Tab 3: 学习足迹 ---
with tab3:
    st.subheader("📚 唯一词汇档案")
    if not clean_log_df.empty:
        # 使用 reindex 确保即便是空表格也不会崩
        display_df = clean_log_df.reindex(columns=['date', 'word', 'meaning', 'notes', 'level']).fillna("—")
        display_df.columns = ['打卡日期', '单词', '中文释义', '词性/笔记', '难度等级']
        st.dataframe(display_df.sort_values('打卡日期', ascending=False), use_container_width=True, hide_index=True)
        
        # 导出功能
        csv = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出我的词汇库", data=csv, file_name=f"英语档案_{datetime.date.today()}.csv")
    else:
        st.info("还没有记录，快去完成今日挑战吧！")
