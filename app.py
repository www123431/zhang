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
# 1. 核心认证与多模态引擎 (TTS 语音)
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
    """🎙️ 生成美化版圆形播放按钮 (JS 驱动，彻底解决不发音)"""
    try:
        tts = gTTS(text=word, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        audio_id = f"audio_{idx}"
        # 返回隐藏的音频标签 + 自定义粉色按钮
        return f"""
            <audio id="{audio_id}" src="data:audio/mp3;base64,{b64}"></audio>
            <div class="play-btn" onclick="document.getElementById('{audio_id}').play()">
                ▶ <span>Listen / 听发音</span>
            </div>
        """
    except: return "发音接口忙"

# ==========================================
# 2. 卿姐专属 UI 视觉系统 (终极美化版)
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    
    /* 核心卡片样式：圆润、温馨、大字 */
    .word-card { 
        background: white; padding: 2.8rem; border-radius: 30px; 
        box-shadow: 0 12px 35px rgba(0,0,0,0.06); margin-bottom: 30px;
        transition: all 0.4s ease; border: 1px solid #F2F2F2; text-align: center;
        position: relative;
    }
    .word-card:hover { transform: translateY(-8px); border-color: #D02090; }
    
    /* 单词主体：视觉冲击大字报 */
    .big-word { font-family: 'Georgia', serif; font-size: 4rem; font-weight: 900; color: #2C3E50; margin: 10px 0; }
    
    /* 释义：优雅粉色标签 */
    .meaning-tag { font-size: 1.8rem; color: #D02090; background: #FFF0F5; padding: 10px 35px; border-radius: 60px; font-weight: bold; display: inline-block; }
    
    /* 圆形粉色发音按钮 */
    .play-btn {
        margin: 20px auto 0; width: 140px; background: linear-gradient(135deg, #FF69B4, #D02090);
        color: white; padding: 10px 18px; border-radius: 25px; cursor: pointer;
        display: flex; align-items: center; justify-content: center; gap: 10px;
        font-weight: bold; box-shadow: 0 4px 15px rgba(208, 32, 144, 0.3); transition: 0.3s;
    }
    .play-btn:hover { filter: brightness(1.1); transform: scale(1.05); }
    
    /* AI 助记区 */
    .mnemonic-tip {
        margin-top: 20px; padding-top: 15px; border-top: 1px dashed #EEE;
        color: #7F8C8D; font-size: 1rem; font-style: italic; line-height: 1.6;
    }

    .pos-badge { font-size: 0.8rem; text-transform: uppercase; padding: 6px 16px; border-radius: 10px; font-weight: bold; background: #F5F5F5; color: #616161; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 数据中心 (适配 meaning & notes)
# ==========================================
gc = init_connection()
sh = gc.open("Sheet1")

# --- A. 词库读取 (Sheet1) ---
ws_lib = sh.worksheet("Sheet1")
lib_data = ws_lib.get_all_values()
lib_df = pd.DataFrame(lib_data[1:], columns=[c.lower().strip() for c in lib_data[0]]) if len(lib_data)>1 else pd.DataFrame()

# --- B. 日志读取 (Learning_Log) ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="5")
    ws_log.append_row(["date", "word", "meaning", "notes", "level"])

log_all = ws_log.get_all_values()
raw_log_df = pd.DataFrame(log_all[1:], columns=[c.lower().strip() for c in log_all[0]]) if len(log_all)>1 else pd.DataFrame()

# ==========================================
# 4. 卿姐功能模块
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战", "🔄 记忆复苏", "📚 学习足迹"])

# --- Tab 1: 挑战模式 ---
with tab1:
    col_a, col_b = st.columns([1, 4])
    with col_a:
        lvl = st.select_slider("今日强度：", options=["🌱 基础", "✨ 进阶", "💪 核心"])
    with col_b:
        if st.button("🚀 开启今日助记之旅", use_container_width=True):
            if not lib_df.empty:
                # 随机抽取 8 个词
                st.session_state['batch'] = lib_df.sample(min(len(lib_df), 8)).to_dict('records')

    if 'batch' in st.session_state:
        # 使用两列布局
        display_cols = st.columns(2)
        # AI 教练建议
        tips = [
            "🧠 **联想助记**：试着把这个词和你最近看的一部电影联系起来。",
            "🎧 **听读强化**：点击播放键，闭上眼跟读三遍，模仿发音。",
            "✍️ **肌肉记忆**：在心里默默拼写一遍这个词。",
            "🗣️ **场景应用**：想象你在向主管解释这个词的 Business BA 场景。"
        ]

        for idx, item in enumerate(st.session_state['batch']):
            word = item.get('word', 'N/A')
            with display_cols[idx % 2]:
                # 彻底解决显示代码的问题：所有 HTML 嵌套确保闭合，并设置 unsafe_allow_html=True
                st.markdown(f"""
                    <div class="word-card">
                        <span class="pos-badge">{item.get('notes', 'Vocabulary')}</span>
                        <h1 class="big-word">{word}</h1>
                        <div class="meaning-tag">{item.get('meaning', '点击查看')}</div>
                        {get_audio_html(word, idx)}
                        <div class="mnemonic-tip">💡 助记建议：{tips[idx % 4]}</div>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("✅ 卿姐记住了，同步云端档案", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('meaning'), i.get('notes'), lvl])
            st.balloons(); time.sleep(1); st.rerun()

# --- Tab 2: 记忆复苏 (艾宾浩斯复习) ---
with tab2:
    if not raw_log_df.empty:
        raw_log_df['dt'] = pd.to_datetime(raw_log_df['date'], errors='coerce').dt.date
        today = datetime.date.today()
        # 科学复习节点：1, 3, 7 天
        target_dates = [today - datetime.timedelta(days=i) for i in [1, 3, 7]]
        rev_df = raw_log_df[raw_log_df['dt'].isin(target_dates)].drop_duplicates('word')
        
        if not rev_df.empty:
            st.success(f"🌹 卿姐，今天有 {len(rev_df)} 个老朋友需要见见面！")
            for idx, row in enumerate(rev_df.to_dict('records')):
                with st.expander(f"🔁 复习单词: {row['word']}"):
                    st.write(f"**中文意思**: {row['meaning']}")
                    st.write(f"**上次笔记**: {row['notes']}")
                    # 复习页也使用美化版发音
                    st.markdown(get_audio_html(row['word'], f"rev_{idx}"), unsafe_allow_html=True)
        else:
            st.info("✨ 今天没有复习任务，卿姐可以直接学点新的！")

# --- Tab 3: 学习足迹 (智能去重版) ---
with tab3:
    if not raw_log_df.empty:
        # 去重逻辑：同一个单词只保留最后一次（最新的）打卡记录
        clean_df = raw_log_df.drop_duplicates(subset=['word'], keep='last')
        
        # 字段自动适配
        display = clean_df.reindex(columns=['date', 'word', 'meaning', 'notes', 'level']).fillna("—")
        display.columns = ['打卡日期', '单词', '中文释义', '词性/笔记', '难度等级']
        
        st.write(f"📊 卿姐太棒了，已经累计攻克了 **{len(clean_df)}** 个单词！")
        
        st.dataframe(display.sort_values('打卡日期', ascending=False), use_container_width=True, hide_index=True)
        
        # CSV 导出功能
        csv = display.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出我的词汇库 (CSV)", csv, f"英语档案_{datetime.date.today()}.csv", "text/csv")
