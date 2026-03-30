import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
from io import BytesIO
from gtts import gTTS

# ==========================================
# 1. 核心后台：安全认证与稳健发音引擎
# ==========================================
def init_connection():
    try:
        # 从 Streamlit Secrets 获取 GCP 配置
        creds_dict = st.secrets["gcp_service_account"].to_dict()
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证失败，请检查 Secrets: {e}"); st.stop()

def play_audio(word):
    """🎙️ 原生音频组件：确保在任何设备上点读必响"""
    try:
        tts = gTTS(text=word, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, format="audio/mp3")
    except:
        st.caption("🔊 语音生成中...")

# ==========================================
# 2. 视觉设计语言 (旗舰级 UI 注入)
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    
    /* 旗舰级单词卡片 */
    .word-card-box {
        background: white;
        padding: 35px 25px;
        border-radius: 28px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.04);
        border: 1px solid #F2F2F2;
        text-align: center;
        margin-bottom: 15px;
    }
    
    /* 单词大字报样式 */
    .big-word-text {
        font-family: 'Georgia', serif;
        font-size: 4rem;
        font-weight: 900;
        color: #2C3E50;
        margin-bottom: 10px;
        letter-spacing: -1px;
    }
    
    /* 释义粉色标签 */
    .pink-tag {
        font-size: 1.8rem;
        color: #D02090;
        background: #FFF0F5;
        padding: 8px 35px;
        border-radius: 50px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 15px;
    }
    
    /* 小副标题 */
    .sub-label { font-size: 0.85rem; color: #9E9E9E; text-transform: uppercase; margin-bottom: 5px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 数据层：Sheet1 (词库) & Learning_Log (足迹)
# ==========================================
gc = init_connection()
sh = gc.open("Sheet1")

# --- 读取原始词库 ---
ws_lib = sh.worksheet("Sheet1")
lib_raw = ws_lib.get_all_values()
# 自动清洗表头（转小写、去空格）以适配不同表格习惯
lib_df = pd.DataFrame(lib_raw[1:], columns=[c.lower().strip() for c in lib_raw[0]]) if len(lib_raw)>1 else pd.DataFrame()

# --- 读取/初始化学习日志 ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="5")
    ws_log.append_row(["date", "word", "meaning", "notes", "level"])

log_all = ws_log.get_all_values()
raw_log_df = pd.DataFrame(log_all[1:], columns=[c.lower().strip() for c in log_all[0]]) if len(log_all)>1 else pd.DataFrame()

# ==========================================
# 4. 核心功能：三大 Tab 联动
# ==========================================
t1, t2, t3 = st.tabs(["🌟 卿姐挑战", "🔄 记忆复苏", "📚 学习足迹"])

# --- Tab 1: 今日新词挑战 ---
with t1:
    c_set1, c_set2 = st.columns([1, 4])
    with c_set1:
        lvl = st.radio("今日强度：", options=["🌱 基础", "✨ 进阶", "💪 核心"])
    with c_set2:
        if st.button("🚀 换一批新单词", use_container_width=True):
            if not lib_df.empty:
                # 随机抽取 8 个词进行学习
                st.session_state['batch'] = lib_df.sample(min(len(lib_df), 8)).to_dict('records')

    if 'batch' in st.session_state:
        display_cols = st.columns(2)
        # AI 动态助记建议
        ai_tips = [
            "🧠 **联想建议**：把这个词和你最近在 Business Analytics 课上学到的模型联系起来。",
            "🎧 **听力强化**：点击下方原生播放条，跟着它念三遍，模仿重音位置。",
            "✍️ **肌肉记忆**：试着在纸上或心里默拼这个单词，关注它的拼写细节。",
            "🗣️ **场景模拟**：想象你在向主管汇报时，如何自然地用出这个高级词汇。"
        ]

        for idx, item in enumerate(st.session_state['batch']):
            word = item.get('word', 'N/A')
            with display_cols[idx % 2]:
                # UI 卡片展示（确保不乱码）
                st.markdown(f"""
                    <div class="word-card-box">
                        <div class="sub-label">{item.get('notes', 'VOCABULARY')}</div>
                        <div class="big-word-text">{word}</div>
                        <div class="pink-tag">{item.get('meaning', item.get('chinese', '点击听音'))}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # 功能组件：原生发音 + AI 建议
                play_audio(word)
                st.info(ai_tips[idx % 4])
                st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("✅ 卿姐记住了，同步云端档案", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                # 将数据写回 Google Sheets
                ws_log.append_row([
                    str(datetime.date.today()), 
                    i.get('word'), 
                    i.get('meaning', i.get('chinese', 'N/A')), 
                    i.get('notes', 'N/A'), 
                    lvl
                ])
            st.balloons(); time.sleep(1); st.rerun()

# --- Tab 2: 记忆复苏 (艾宾浩斯 1/3/7天科学复习) ---
with t2:
    if not raw_log_df.empty:
        raw_log_df['dt'] = pd.to_datetime(raw_log_df['date'], errors='coerce').dt.date
        today = datetime.date.today()
        # 筛选复习节点
        target_dates = [today - datetime.timedelta(days=i) for i in [1, 3, 7]]
        rev_df = raw_log_df[raw_log_df['dt'].isin(target_dates)].drop_duplicates('word')
        
        if not rev_df.empty:
            st.success(f"🌹 卿姐，今天有 {len(rev_df)} 个单词触发了“遗忘节点”，快来温习一下！")
            for idx, row in enumerate(rev_df.to_dict('records')):
                with st.expander(f"🔁 复习单词: {row['word']}"):
                    st.subheader(f"中文意思: {row['meaning']}")
                    st.write(f"上次笔记: {row['notes']}")
                    play_audio(row['word'])
        else:
            st.info("✨ 卿姐今天太棒了，目前没有到期的复习任务！")
    else:
        st.warning("词库还是空的哦，快去【今日挑战】开启第一课吧！")

# --- Tab 3: 学习足迹 (专项净化优化) ---
with tab3:
    if not raw_log_df.empty:
        # 1. 智能去重：同一个单词只保留最后一次打卡记录
        clean_df = raw_log_df.drop_duplicates(subset=['word'], keep='last').copy()
        
        # 2. 【核心优化】：彻底净化数据，把所有 N/A, nan, 空白全部变成真正的空白
        for col in ['meaning', 'notes', 'level']:
            clean_df[col] = clean_df[col].apply(lambda x: "" if str(x).strip().lower() in ["nan", "n/a", "none", ""] else x)
        
        # 3. 重新排版显示
        display = clean_df.reindex(columns=['date', 'word', 'meaning', 'notes', 'level'])
        display.columns = ['学习日期', '单词', '中文释义', '我的笔记', '掌握难度']
        
        st.write(f"📊 卿姐已累计攻克了 **{len(clean_df)}** 个词汇！")
        
        # 4. 美化表格展示，隐藏索引
        st.dataframe(
            display.sort_values('学习日期', ascending=False), 
            use_container_width=True, 
            hide_index=True
        )
        
        # 5. CSV 导出
        csv = display.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出词汇档案 (CSV)", csv, f"卿姐英语档案_{datetime.date.today()}.csv", "text/csv")
