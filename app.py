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
# 1. 核心认证与美化版音频引擎
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
        st.error(f"❌ 认证失败: {e}"); st.stop()

def get_pronunciation_audio(word, idx):
    """🎙️ 生成美化版圆形播放按钮 (JS驱动)"""
    try:
        tts = gTTS(text=word, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        audio_id = f"audio_{idx}"
        return f"""
            <audio id="{audio_id}" src="data:audio/mp3;base64,{b64}"></audio>
            <div class="play-btn" onclick="document.getElementById('{audio_id}').play()">
                ▶ <span>Listen</span>
            </div>
        """
    except: return ""

# ==========================================
# 2. 卿姐专属 UI 视觉系统
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    
    /* 单词卡片美化 */
    .word-card { 
        background: white; padding: 2.5rem; border-radius: 28px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 25px;
        text-align: center; border: 1px solid #F2F2F2; transition: 0.3s;
    }
    .word-card:hover { transform: translateY(-5px); border-color: #D02090; }
    
    .big-word { font-family: 'Georgia', serif; font-size: 3.5rem; font-weight: 900; color: #2C3E50; margin: 10px 0; }
    .meaning-tag { font-size: 1.6rem; color: #D02090; background: #FFF0F5; padding: 8px 30px; border-radius: 50px; font-weight: 600; display: inline-block; }
    
    /* 圆形播放按钮 */
    .play-btn {
        margin: 15px auto 0; width: 110px; background: linear-gradient(135deg, #FF69B4, #D02090);
        color: white; padding: 8px; border-radius: 20px; cursor: pointer;
        display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 0.9rem;
    }
    .play-btn:hover { filter: brightness(1.1); }

    .pos-badge { font-size: 0.8rem; padding: 4px 12px; border-radius: 8px; background: #F5F5F5; color: #616161; font-weight: bold; }
    .review-card { background: white; padding: 1.2rem; border-radius: 15px; border-left: 5px solid #D02090; margin-bottom: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.02); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 数据中枢 (适配 meaning & notes)
# ==========================================
gc = init_connection()
sh = gc.open("Sheet1")

# --- A. 词库全量读取 ---
ws_lib = sh.worksheet("Sheet1")
lib_data = ws_lib.get_all_values()
lib_df = pd.DataFrame(lib_data[1:], columns=[c.lower().strip() for c in lib_data[0]]) if len(lib_data)>1 else pd.DataFrame()

# --- B. 学习日志读取与预处理 ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="5")
    ws_log.append_row(["date", "word", "meaning", "notes", "level"])

log_all = ws_log.get_all_values()
raw_log_df = pd.DataFrame(log_all[1:], columns=[c.lower().strip() for c in log_all[0]]) if len(log_all)>1 else pd.DataFrame()

# ==========================================
# 4. 功能标签页
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战", "🔄 记忆复苏", "📚 学习足迹"])

# --- Tab 1: 抽题与打卡 ---
with tab1:
    lvl = st.select_slider("选择今日强度：", options=["🌱 基础", "✨ 进阶", "💪 核心"])
    if st.button("🚀 开启助记之旅", use_container_width=True):
        if not lib_df.empty:
            st.session_state['batch'] = lib_df.sample(min(len(lib_df), 8)).to_dict('records')

    if 'batch' in st.session_state:
        cols = st.columns(2)
        for idx, item in enumerate(st.session_state['batch']):
            word = item.get('word', 'N/A')
            with cols[idx % 2]:
                st.markdown(f"""
                    <div class="word-card">
                        <span class="pos-badge">{item.get('notes', 'VOCAB')}</span>
                        <h1 class="big-word">{word}</h1>
                        <div class="meaning-tag">{item.get('meaning', '未记录')}</div>
                        {get_pronunciation_audio(word, idx)}
                    </div>
                """, unsafe_allow_html=True)
        
        if st.button("✅ 卿姐全部记住了，同步云端", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('meaning'), i.get('notes'), lvl])
            st.balloons(); time.sleep(1); st.rerun()

# --- Tab 2: 艾宾浩斯复习 (自动计算节点) ---
with tab2:
    st.subheader("📅 记忆复苏提醒")
    if not raw_log_df.empty:
        raw_log_df['dt'] = pd.to_datetime(raw_log_df['date'], errors='coerce').dt.date
        today = datetime.date.today()
        # 筛选 1, 3, 7 天前的词汇
        remind_dates = [today - datetime.timedelta(days=i) for i in [1, 3, 7]]
        rev_df = raw_log_df[raw_log_df['dt'].isin(remind_dates)].drop_duplicates('word')
        
        if not rev_df.empty:
            for idx, row in enumerate(rev_df.to_dict('records')):
                with st.expander(f"🔁 复习单词: {row['word']} ({row['date']})"):
                    st.write(f"**中文释义**: {row['meaning']}")
                    st.write(f"**笔记**: {row['notes']}")
                    st.markdown(get_pronunciation_audio(row['word'], f"rev_{idx}"), unsafe_allow_html=True)
        else:
            st.info("🍀 卿姐，今天暂时没有需要复习的词汇，继续加油！")
    else:
        st.write("暂无学习记录。")

# --- Tab 3: 学习足迹 (智能去重版) ---
with tab3:
    st.subheader("📚 卿姐的词汇宝库")
    if not raw_log_df.empty:
        # 逻辑去重：同一个单词只保留最后一次（最新的）打卡记录
        clean_df = raw_log_df.drop_duplicates(subset=['word'], keep='last')
        
        # 格式化展示
        display = clean_df.reindex(columns=['date', 'word', 'meaning', 'notes', 'level']).fillna("—")
        display.columns = ['打卡日期', '单词', '中文释义', '词性/笔记', '难度等级']
        
        # 统计数据
        st.write(f"📊 你已累计掌握了 **{len(clean_df)}** 个唯一单词！")
        
        st.dataframe(display.sort_values('打卡日期', ascending=False), use_container_width=True, hide_index=True)
        
        # CSV 导出功能
        csv = display.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 导出词汇档案 (CSV)",
            data=csv,
            file_name=f"卿姐英语档案_{datetime.date.today()}.csv",
            mime="text/csv"
        )
    else:
        st.info("档案室目前空空如也，快去打卡吧！")
