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
# 1. 核心认证与多模态工具 (TTS)
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
    """🎙️ 为卡片生成优雅的 Base64 音频流"""
    try:
        tts = gTTS(text=word, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        return f'<audio src="data:audio/mp3;base64,{b64}" controls style="height:32px; width:100%; margin-top:15px; border-radius:10px;"></audio>'
    except:
        return ""

# ==========================================
# 2. 卿姐专属 UI 设计语言 (保持优秀视觉设计)
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

st.markdown("""
    <style>
    /* 全局背景色：柔和淡紫色 */
    .stApp { background-color: #FDFBFF; }
    
    /* 🌟 核心：灵动助记卡片设计 */
    .word-card { 
        background: white; 
        padding: 2.8rem; 
        border-radius: 28px; 
        box-shadow: 0 12px 35px rgba(0,0,0,0.06); 
        margin-bottom: 30px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        border: 1px solid #F2F2F2; 
        text-align: center;
        position: relative;
    }
    .word-card:hover { 
        transform: translateY(-12px); 
        border-color: #D02090; 
        box-shadow: 0 22px 45px rgba(208, 32, 144, 0.12); 
    }

    /* 单词：视觉冲击大字报 */
    .big-word { 
        font-family: 'Georgia', serif; 
        font-size: 4rem; 
        font-weight: 900; 
        color: #2C3E50; 
        margin: 10px 0; 
        letter-spacing: -1px;
    }

    /* 释义：优雅粉色标签 */
    .meaning-tag { 
        font-size: 1.7rem; 
        color: #D02090; 
        background: #FFF0F5; 
        display: inline-block;
        padding: 10px 35px; 
        border-radius: 60px; 
        font-weight: 600;
        margin-top: 10px;
    }

    /* 助记贴士区 */
    .mnemonic-tip {
        margin-top: 20px;
        padding-top: 15px;
        border-top: 1px dashed #EEE;
        color: #7F8C8D;
        font-size: 0.9rem;
        font-style: italic;
    }

    /* 词性勋章：色彩心理记忆 */
    .pos-badge { font-size: 0.85rem; text-transform: uppercase; padding: 6px 16px; border-radius: 10px; font-weight: 800; letter-spacing: 1px; }
    .pos-verb { background: #E1F5FE; color: #0288D1; } 
    .pos-noun { background: #E8F5E9; color: #388E3C; }
    .pos-adj { background: #FFF3E0; color: #F57C00; }
    .pos-other { background: #F5F5F5; color: #616161; }
    
    /* 复习区微调 */
    .review-card { background: #FFFFFF; padding: 1.8rem; border-radius: 20px; border-left: 8px solid #D02090; margin-bottom: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 数据中心 (自动去重 + 容错加载)
# ==========================================
gc = init_connection()
sh = gc.open("Sheet1")

# --- 词库读取 ---
ws_lib = sh.worksheet("Sheet1")
lib_data = ws_lib.get_all_values()
lib_df = pd.DataFrame(lib_data[1:], columns=lib_data[0]) if len(lib_data)>1 else pd.DataFrame()
if not lib_df.empty:
    lib_df.columns = [c.lower().strip() for c in lib_df.columns]
    lib_df = lib_df.rename(columns={'words': 'word', 'chinese': 'chinese'})

# --- 日志读取与展示层去重 ---
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="10")
    ws_log.append_row(["date", "word", "chinese", "category", "level"])

log_all = ws_log.get_all_values()
raw_log_df = pd.DataFrame(log_all[1:], columns=log_all[0]) if len(log_all)>1 else pd.DataFrame(columns=["date", "word", "chinese", "category", "level"])

if not raw_log_df.empty:
    raw_log_df.columns = [c.lower().strip() for c in raw_log_df.columns]
    raw_log_df['sort_date'] = pd.to_datetime(raw_log_df['date'], errors='coerce')
    clean_log_df = raw_log_df.sort_values('sort_date', ascending=False).drop_duplicates(subset=['word'], keep='first').drop(columns=['sort_date'])
else:
    clean_log_df = raw_log_df.copy()

# ==========================================
# 4. 主页面逻辑
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 深度助记挑战", "🔄 记忆复苏", "📚 学习足迹"])

# 样式映射
def get_pos_style(p):
    p = str(p).lower()
    if 'v' in p: return "pos-verb"
    if 'n' in p: return "pos-noun"
    if 'adj' in p: return "pos-adj"
    return "pos-other"

# --- Tab 1: 挑战与助记 ---
with tab1:
    with st.sidebar:
        st.header("⚙️ 调频中心")
        lvl = st.select_slider("今日强度：", options=["🌱 基础", "✨ 进阶", "💪 核心"])
        st.info("💡 技巧：点击卡片下的播放键，闭上眼跟读 3 遍，效果翻倍！")

    if st.button("🚀 开启今日助记之旅", use_container_width=True):
        if not lib_df.empty:
            f = lib_df[lib_df['word'].str.len() <= 5] if "基础" in lvl else lib_df[lib_df['word'].str.len() > 5]
            st.session_state['batch'] = f.sample(min(len(f), 8)).to_dict('records')

    if 'batch' in st.session_state:
        for item in st.session_state['batch']:
            word = item.get('word', 'N/A')
            audio = get_pronunciation_audio(word)
            
            # 生成随机助记建议
            tips = [
                f"尝试用 '{word}' 造一个和 Business Analytics 相关的句子。",
                f"联想一个包含 '{word}' 的职场沟通场景。",
                f"这个词的词根是什么？试着拆解它。",
                f"想象你正在向你的 supervisor 解释这个词。"
            ]
            
            st.markdown(f"""
                <div class="word-card">
                    <span class="pos-badge {get_pos_style(item.get('category'))}">{item.get('category', 'WORD')}</span>
                    <h1 class="big-word">{word}</h1>
                    <div class="meaning-tag">{item.get('chinese', 'N/A')}</div>
                    {audio}
                    <div class="mnemonic-tip">💡 助记建议：{tips[int(time.time()) % 4]}</div>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 卿姐记住了，同步云端档案", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('chinese'), i.get('category'), lvl])
            st.balloons()
            st.rerun()

# --- Tab 2: 记忆复苏 (艾宾浩斯复习逻辑) ---
with tab2:
    st.subheader("🔄 记忆复苏节点")
    
    def get_ebbinghaus_list(df):
        if df.empty or 'date' not in df.columns: return pd.DataFrame()
        temp = df.copy()
        # 强制转换日期格式，防止格式不一报错
        temp['date_dt'] = pd.to_datetime(temp['date'], errors='coerce').dt.date
        today = datetime.date.today()
        # 科学复习节点：1, 3, 7, 15天
        intervals = [1, 3, 7, 15]
        target_dates = [today - datetime.timedelta(days=i) for i in intervals]
        return temp[temp['date_dt'].isin(target_dates)]

    rev_df = get_ebbinghaus_list(raw_log_df)
    if not rev_df.empty:
        # 确保 word 列存在再进行去重
        if 'word' in rev_df.columns:
            rev_df = rev_df.drop_duplicates(subset=['word'])
            cols = st.columns(2)
            for idx, row in enumerate(rev_df.to_dict('records')):
                with cols[idx % 2]:
                    st.markdown(f"""
                    <div class="review-card">
                        <h3 style="color:#2C3E50;">{row.get('word', 'Unknown')}</h3>
                        <p style="color:#7F8C8D; font-size:0.8rem;">上次打卡：{row.get('date', 'N/A')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    with st.expander("🔍 揭晓答案"):
                        st.write(f"**中文含义**: {row.get('chinese', '未记录')}")
                        st.write(f"**词性分类**: {row.get('category', '未分类')}")
    else:
        st.info("✨ 卿姐，今日暂无需要复习的单词，继续保持！")

# --- Tab 3: 学习足迹 (根据卿姐最新表格名适配) ---
with tab3:
    st.subheader("📚 唯一词汇档案")
    
    if not clean_log_df.empty:
        st.write(f"🎉 卿姐已经累计攻克了 **{len(clean_log_df)}** 个唯一单词！")
        
        # 【核心适配】：改为匹配你图片里的新表头名
        # 你图片里是：date, word, meaning, notes, level
        required_columns = ['date', 'word', 'meaning', 'notes', 'level']
        
        # 强制对齐
        display_df = clean_log_df.reindex(columns=required_columns)
        
        # 填充缺失并重命名为中文标签
        display_df = display_df.fillna("未记录")
        display_df.columns = ['打卡日期', '单词', '中文释义', '词性/笔记', '难度等级']
        
        # 渲染表格
        st.dataframe(
            display_df.sort_values('打卡日期', ascending=False), 
            use_container_width=True,
            hide_index=True
        )
        
        # 导出功能
        csv = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 导出我的词汇库 (CSV)",
            data=csv,
            file_name=f"卿姐英语档案_{datetime.date.today()}.csv",
            mime="text/csv",
        )
    else:
        st.warning("📭 档案室暂时是空的。")
