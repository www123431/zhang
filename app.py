import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import requests
from io import BytesIO
from gtts import gTTS

# ==========================================
# 1. AI 引擎：DeepSeek 银行场景私教
# ==========================================
def get_ai_mnemonic(word, meaning):
    """🧠 调用 DeepSeek API 为卿姐定制银行场景助记词"""
    api_key = st.secrets.get("deepseek_api_key", "sk-8c10698361c24c71af07315c3abb6582")
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    
    prompt = f"""
    角色：你是一名幽默的英语私教，学生‘卿姐’是一位在银行工作的资深员工。
    任务：为单词 '{word}'（释义：{meaning}）提供一个助记法。
    要求：结合银行具体场景（如柜台、理财、合规、贷款审批、VIP服务等），语气亲切幽默，开头叫‘卿姐’，40字以内。
    """
    try:
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7 
        }
        response = requests.post(url, json=data, headers=headers, timeout=8)
        return response.json()['choices'][0]['message']['content']
    except:
        return "💡 卿姐，这个词在银行系统中很常见，建议结合日常业务加强记忆。"

# ==========================================
# 2. 视觉系统 (CSS 注入)
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #FDFBFF; }
    .word-card-box {
        background: white; padding: 30px; border-radius: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid #F2F2F2;
        text-align: center; margin-bottom: 10px; min-height: 220px;
    }
    .big-word-text { font-family: 'Georgia', serif; font-size: 3.5rem; font-weight: 900; color: #2C3E50; }
    .pink-tag { font-size: 1.5rem; color: #D02090; background: #FFF0F5; padding: 5px 25px; border-radius: 50px; font-weight: bold; display: inline-block; }
    .ai-box { background-color: #F0FFF4; border-left: 5px solid #48BB78; padding: 12px; border-radius: 10px; margin-top: 10px; font-size: 0.95rem; color: #2D3748; text-align: left;}
    .sub-label { font-size: 0.8rem; color: #9E9E9E; background: #F8F9FA; padding: 4px 12px; border-radius: 8px; margin-bottom: 8px; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 数据中枢 (Google Sheets)
# ==========================================
def init_connection():
    creds_dict = st.secrets["gcp_service_account"].to_dict()
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

gc = init_connection()
sh = gc.open("Sheet1")

# 读取词库与日志
ws_lib = sh.worksheet("Sheet1")
lib_df = pd.DataFrame(ws_lib.get_all_values()[1:], columns=[c.lower().strip() for c in ws_lib.get_all_values()[0]])

try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="5")
    ws_log.append_row(["date", "word", "meaning", "notes", "level"])

raw_log_df = pd.DataFrame(ws_log.get_all_values()[1:], columns=[c.lower().strip() for c in ws_log.get_all_values()[0]])

# ==========================================
# 4. 功能模块
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 卿姐挑战", "🔄 记忆复苏", "📚 学习足迹"])

# --- Tab 1: AI 驱动学习 ---
with tab1:
    c1, c2 = st.columns([1, 4])
    with c1:
        lvl = st.radio("今日强度：", options=["🌱 基础", "✨ 进阶", "💪 核心"])
    with c2:
        if st.button("🚀 呼叫 DeepSeek 换一批", use_container_width=True):
            selected = lib_df.sample(min(len(lib_df), 8)).to_dict('records')
            with st.spinner("DeepSeek 正在结合银行场景为卿姐编写助记词..."):
                for item in selected:
                    item['ai_tip'] = get_ai_mnemonic(item.get('word'), item.get('meaning'))
            st.session_state['batch'] = selected

    if 'batch' in st.session_state:
        cols = st.columns(2)
        for idx, item in enumerate(st.session_state['batch']):
            word = item.get('word', 'N/A')
            note_raw = str(item.get('notes', '')).strip()
            note_show = "VOCAB" if note_raw in ["", "N/A", "nan", "None"] else note_raw
            
            with cols[idx % 2]:
                st.markdown(f"""
                    <div class="word-card-box">
                        <div class="sub-label">{note_show}</div>
                        <div class="big-word-text">{word}</div>
                        <div class="pink-tag">{item.get('meaning', '未录入')}</div>
                        <div class="ai-box">🤖 <b>AI 助记：</b>{item.get('ai_tip', '加载中...')}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # 原生音频
                tts = gTTS(text=word, lang='en')
                fp = BytesIO(); tts.write_to_fp(fp)
                st.audio(fp, format="audio/mp3")
                st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("✅ 卿姐记住了，同步云端", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('meaning'), i.get('notes'), lvl])
            st.balloons(); time.sleep(1); st.rerun()

# --- Tab 2: 艾宾浩斯复习 (1/3/7天) ---
with tab2:
    if not raw_log_df.empty:
        raw_log_df['dt'] = pd.to_datetime(raw_log_df['date'], errors='coerce').dt.date
        today = datetime.date.today()
        targets = [today - datetime.timedelta(days=i) for i in [1, 3, 7]]
        rev_df = raw_log_df[raw_log_df['dt'].isin(targets)].drop_duplicates('word')
        
        if not rev_df.empty:
            st.success(f"🌹 卿姐，今日有 {len(rev_df)} 个词需要巩固！")
            for row in rev_df.to_dict('records'):
                with st.expander(f"🔁 复习: {row['word']}"):
                    st.write(f"**意思**: {row['meaning']}")
                    tts = gTTS(text=row['word'], lang='en')
                    fp = BytesIO(); tts.write_to_fp(fp); st.audio(fp, format="audio/mp3")
        else:
            st.info("✨ 卿姐太棒了，目前没有到期的复习任务！")

# --- Tab 3: 足迹 (专项去重与数据清洗) ---
with tab3:
    if not raw_log_df.empty:
        # 1. 深度清洗：彻底抹除 N/A, nan 等干扰项
        clean_df = raw_log_df.drop_duplicates(subset=['word'], keep='last').copy()
        for col in ['meaning', 'notes', 'level']:
            if col in clean_df.columns:
                clean_df[col] = clean_df[col].apply(lambda x: "" if str(x).strip().lower() in ["nan", "n/a", "none", "", "null"] else x)
        
        # 2. 格式化输出
        display = clean_df.reindex(columns=['date', 'word', 'meaning', 'notes', 'level']).fillna("")
        display.columns = ['学习日期', '单词', '中文释义', '我的笔记', '掌握难度']
        
        st.write(f"📊 卿姐已累计攻克了 **{len(clean_df)}** 个词汇！")
        st.dataframe(display.sort_values('学习日期', ascending=False), use_container_width=True, hide_index=True)
        
        csv = display.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出词汇档案", csv, f"学习档案_{datetime.date.today()}.csv", "text/csv")
