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
        st.error(f"❌ 认证失败，请检查配置: {e}"); st.stop()

def get_pronunciation_audio(word, idx):
    """🎙️ 生成美化版圆形播放按钮 (初学者最爱)"""
    try:
        tts = gTTS(text=word, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        audio_id = f"audio_{idx}"
        return f"""
            <audio id="{audio_id}" src="data:audio/mp3;base64,{b64}"></audio>
            <div class="play-btn" onclick="document.getElementById('{audio_id}').play()">
                ▶ <span>Listen / 听读</span>
            </div>
        """
    except: return ""

# ==========================================
# 2. 视觉设计系统 (初学者友好风格)
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    
    /* 单词卡片：圆润、温馨、大字 */
    .word-card { 
        background: white; padding: 2rem; border-radius: 28px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 25px;
        text-align: center; border: 1px solid #F2F2F2; transition: 0.3s;
    }
    .word-card:hover { transform: translateY(-5px); border-color: #D02090; }
    
    /* 单词：超大字体，清晰易读 */
    .big-word { font-family: 'Georgia', serif; font-size: 3.5rem; font-weight: 900; color: #2C3E50; margin: 10px 0; }
    
    /* 释义：显眼的粉色标签 */
    .meaning-tag { font-size: 1.6rem; color: #D02090; background: #FFF0F5; padding: 8px 30px; border-radius: 50px; font-weight: 600; display: inline-block; }
    
    /* 美化播放按钮 */
    .play-btn {
        margin: 15px auto 0; width: 140px; background: linear-gradient(135deg, #FF69B4, #D02090);
        color: white; padding: 10px; border-radius: 25px; cursor: pointer;
        display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 1rem;
        box-shadow: 0 4px 15px rgba(208, 32, 144, 0.2);
    }
    .play-btn:hover { filter: brightness(1.1); transform: scale(1.05); }

    .tip-box { margin-top: 15px; font-size: 0.85rem; color: #7F8C8D; font-style: italic; border-top: 1px dashed #EEE; padding-top: 10px; }
    .pos-badge { font-size: 0.75rem; padding: 4px 12px; border-radius: 8px; background: #F5F5F5; color: #616161; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 数据中心 (对接 meaning & notes)
# ==========================================
gc = init_connection()
sh = gc.open("Sheet1")

ws_lib = sh.worksheet("Sheet1")
lib_raw = ws_lib.get_all_values()
lib_df = pd.DataFrame(lib_raw[1:], columns=[c.lower().strip() for c in lib_raw[0]]) if len(lib_raw)>1 else pd.DataFrame()

try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="5")
    ws_log.append_row(["date", "word", "meaning", "notes", "level"])

log_raw = ws_log.get_all_values()
raw_log_df = pd.DataFrame(log_raw[1:], columns=[c.lower().strip() for c in log_raw[0]]) if len(log_raw)>1 else pd.DataFrame()

# ==========================================
# 4. 交互逻辑
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 开始学习", "🔄 复习巩固", "📚 学习记录"])

with tab1:
    col_l, col_r = st.columns([1, 4])
    with col_l:
        lvl = st.radio("选择难度：", options=["🌱 基础", "✨ 进阶", "💪 核心"])
    with col_r:
        if st.button("🚀 换一批新单词", use_container_width=True):
            if not lib_df.empty:
                st.session_state['batch'] = lib_df.sample(min(len(lib_df), 8)).to_dict('records')

    if 'batch' in st.session_state:
        # 分两列展示，更美观
        display_cols = st.columns(2)
        tips = ["跟着声音读三遍，大声说出来！", "试着闭上眼睛，在脑海里拼写这个词。", "这个词让你想到了生活中的什么？", "记得点击播放键，模仿发音哦！"]
        
        for idx, item in enumerate(st.session_state['batch']):
            word = item.get('word', 'N/A')
            with display_cols[idx % 2]:
                st.markdown(f"""
                    <div class="word-card">
                        <span class="pos-badge">{item.get('notes', '单词')}</span>
                        <h1 class="big-word">{word}</h1>
                        <div class="meaning-tag">{item.get('meaning', '点击查看释义')}</div>
                        {get_pronunciation_audio(word, idx)}
                        <div class="tip-box">💡 助记：{tips[idx % 4]}</div>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("✅ 妈妈记住了，同步到我的档案", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('meaning'), i.get('notes'), lvl])
            st.balloons(); time.sleep(1); st.rerun()

# --- Tab 2: 艾宾浩斯复习 ---
with tab2:
    if not raw_log_df.empty:
        raw_log_df['dt'] = pd.to_datetime(raw_log_df['date'], errors='coerce').dt.date
        today = datetime.date.today()
        # 重点温习昨天、3天前、7天前的词
        remind_dates = [today - datetime.timedelta(days=i) for i in [1, 3, 7]]
        rev_df = raw_log_df[raw_log_df['dt'].isin(remind_dates)].drop_duplicates('word')
        
        if not rev_df.empty:
            st.success(f"🌷 妈妈，今天有 {len(rev_df)} 个单词需要温习一下哦！")
            for idx, row in enumerate(rev_df.to_dict('records')):
                with st.expander(f"🔁 点击复习: {row['word']}"):
                    st.subheader(f"解释: {row['meaning']}")
                    st.write(f"笔记: {row['notes']}")
                    st.markdown(get_pronunciation_audio(row['word'], f"rev_{idx}"), unsafe_allow_html=True)
        else:
            st.info("✨ 妈妈太棒了，今天暂时没有需要复习的词，可以学点新的！")

# --- Tab 3: 学习足迹 ---
with tab3:
    if not raw_log_df.empty:
        clean_df = raw_log_df.drop_duplicates(subset=['word'], keep='last')
        display = clean_df.reindex(columns=['date', 'word', 'meaning', 'notes', 'level']).fillna("—")
        display.columns = ['学习日期', '单词', '中文意思', '我的笔记', '难度']
        st.write(f"📊 妈妈已经累计学会了 **{len(clean_df)}** 个单词！")
        st.dataframe(display.sort_values('学习日期', ascending=False), use_container_width=True, hide_index=True)
