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
# 1. 核心认证与美化版发音引擎
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

def get_audio_html(word, idx):
    """🎙️ JS驱动的粉色发音按钮 (彻底解决不发音问题)"""
    try:
        tts = gTTS(text=word, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        audio_id = f"audio_{idx}"
        return f"""
            <audio id="{audio_id}" src="data:audio/mp3;base64,{b64}"></audio>
            <div class="play-btn" onclick="document.getElementById('{audio_id}').play()">
                ▶ <span>Listen / 听发音</span>
            </div>
        """
    except: return "发音接口忙"

# ==========================================
# 2. 卿姐专属 UI 视觉系统 (CSS 注入)
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    
    /* 核心卡片样式 */
    .word-card { 
        background: white; padding: 2.5rem; border-radius: 30px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 25px;
        text-align: center; border: 1px solid #F2F2F2; position: relative;
        transition: transform 0.3s ease;
    }
    .word-card:hover { transform: translateY(-5px); border-color: #D02090; }
    
    .big-word { font-family: 'Georgia', serif; font-size: 3.8rem; font-weight: 900; color: #2C3E50; margin: 10px 0; }
    .meaning-tag { font-size: 1.7rem; color: #D02090; background: #FFF0F5; padding: 8px 35px; border-radius: 50px; font-weight: bold; display: inline-block; }
    
    /* 圆形粉色发音按钮 */
    .play-btn {
        margin: 20px auto 0; width: 140px; background: linear-gradient(135deg, #FF69B4, #D02090);
        color: white; padding: 10px 18px; border-radius: 25px; cursor: pointer;
        display: flex; align-items: center; justify-content: center; gap: 10px;
        font-weight: bold; box-shadow: 0 4px 15px rgba(208, 32, 144, 0.3);
    }
    .play-btn:hover { filter: brightness(1.1); transform: scale(1.05); }
    
    /* AI 助记区 */
    .ai-tip-box { 
        margin-top: 20px; padding-top: 15px; border-top: 1px dashed #EEE; 
        color: #7F8C8D; font-size: 0.95rem; line-height: 1.5;
    }

    .pos-badge { font-size: 0.75rem; padding: 4px 12px; border-radius: 8px; background: #F5F5F5; color: #616161; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 数据中心 (适配 meaning & notes)
# ==========================================
gc = init_connection()
sh = gc.open("Sheet1")

# --- 词库读取 ---
ws_lib = sh.worksheet("Sheet1")
lib_raw = ws_lib.get_all_values()
lib_df = pd.DataFrame(lib_raw[1:], columns=[c.lower().strip() for c in lib_raw[0]]) if len(lib_raw)>1 else pd.DataFrame()

# --- 日志读取 ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="5")
    ws_log.append_row(["date", "word", "meaning", "notes", "level"])

log_raw = ws_log.get_all_values()
raw_log_df = pd.DataFrame(log_raw[1:], columns=[c.lower().strip() for c in log_raw[0]]) if len(log_raw)>1 else pd.DataFrame()

# ==========================================
# 4. 卿姐专属功能模块
# ==========================================
t1, t2, t3 = st.tabs(["🌟 卿姐挑战", "🔄 记忆复苏", "📚 卿姐足迹"])

# --- Tab 1: 学习模式 ---
with t1:
    col_l, col_r = st.columns([1, 4])
    with col_l:
        lvl = st.radio("今日强度：", options=["🌱 基础", "✨ 进阶", "💪 核心"])
    with col_r:
        if st.button("🚀 换一批新单词", use_container_width=True):
            if not lib_df.empty:
                st.session_state['batch'] = lib_df.sample(min(len(lib_df), 8)).to_dict('records')

    if 'batch' in st.session_state:
        display_cols = st.columns(2)
        # AI 动态生成助记建议
        ai_tips = [
            "🧠 **联想建议**：试着把这个词和你最近看的一部电影联系起来。",
            "🎧 **听力强化**：点击播放键，闭上眼模仿它的重音位置。",
            "✍️ **肌肉记忆**：在空气中用手写一遍这个单词的拼写。",
            "🗣️ **场景应用**：试着用这个词造一个描述你今天心情的句子。"
        ]
        
        for idx, item in enumerate(st.session_state['batch']):
            word = item.get('word', 'N/A')
            with display_cols[idx % 2]:
                # 组合卡片内容
                st.markdown(f"""
                    <div class="word-card">
                        <span class="pos-badge">{item.get('notes', 'Vocabulary')}</span>
                        <h1 class="big-word">{word}</h1>
                        <div class="meaning-tag">{item.get('meaning', '点击查看释义')}</div>
                        {get_audio_html(word, idx)}
                        <div class="ai-tip-box">💡 助记：{ai_tips[idx % 4]}</div>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("✅ 卿姐记住了，同步云端", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('meaning'), i.get('notes'), lvl])
            st.balloons(); time.sleep(1); st.rerun()

# --- Tab 2: 复习模式 ---
with t2:
    if not raw_log_df.empty:
        raw_log_df['dt'] = pd.to_datetime(raw_log_df['date'], errors='coerce').dt.date
        today = datetime.date.today()
        # 筛选复习点
        target_dates = [today - datetime.timedelta(days=i) for i in [1, 3, 7]]
        rev_df = raw_log_df[raw_log_df['dt'].isin(target_dates)].drop_duplicates('word')
        
        if not rev_df.empty:
            st.success(f"🌹 卿姐，今天有 {len(rev_df)} 个单词需要温故知新！")
            for idx, row in enumerate(rev_df.to_dict('records')):
                with st.expander(f"🔁 复习单词: {row['word']}"):
                    st.write(f"**中文意思**: {row['meaning']}")
                    st.write(f"**上次笔记**: {row['notes']}")
                    st.markdown(get_audio_html(row['word'], f"rev_{idx}"), unsafe_allow_html=True)
        else:
            st.info("✨ 卿姐今天太棒了，暂时没有需要复习的词！")

# --- Tab 3: 足迹模式 ---
with t3:
    if not raw_log_df.empty:
        clean_df = raw_log_df.drop_duplicates(subset=['word'], keep='last')
        display = clean_df.reindex(columns=['date', 'word', 'meaning', 'notes', 'level']).fillna("—")
        display.columns = ['学习日期', '单词', '中文释义', '词性/笔记', '难度等级']
        st.write(f"📊 卿姐已累计攻克了 **{len(clean_df)}** 个唯一单词！")
        st.dataframe(display.sort_values('学习日期', ascending=False), use_container_width=True, hide_index=True)
