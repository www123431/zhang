import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import requests
import random  
from io import BytesIO
from gtts import gTTS

# ==========================================
# 1. 核心引擎：AI 助记与语音
# ==========================================
def play_audio(word):
    """🎙️ 原生音频播放函数"""
    try:
        tts = gTTS(text=str(word), lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, format="audio/mp3")
    except:
        st.caption("🔊 语音加载中...")

def get_ai_mnemonic(word, meaning):
    """🧠 调用 DeepSeek API 为卿姐定制银行场景助记词"""
    api_key = st.secrets.get("deepseek_api_key", "sk-8c10698361c24c71af07315c3abb6582")
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    
    prompt = f"角色：你是一名幽默的英语私教，学生‘卿姐’是一位在银行工作的资深员工。任务：为单词 '{word}'（释义：{meaning}）提供一个助记法。要求：结合银行具体场景，语气亲切幽默，开头叫‘卿姐’，40字以内。"
    try:
        data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
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
@st.cache_resource
def init_connection():
    try:
        creds_dict = st.secrets["gcp_service_account"].to_dict()
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 初始化连接失败，请检查 Secrets 配置。")
        st.stop()

gc = init_connection()

# 🛡️ 尝试打开表格（增加异常处理）
try:
    # 如果 gc.open("Sheet1") 依然报错，请把下面的代码改为 gc.open_by_url("你的完整表格URL")
    sh = gc.open("Sheet1") 
except gspread.exceptions.SpreadsheetNotFound:
    st.error("🚨 找不到名为 'Sheet1' 的表格！请检查表格名称，或确保已共享给 Service Account 邮箱。")
    st.stop()
except Exception as e:
    st.error(f"🚨 连接表格时发生错误: {e}")
    st.stop()

# 读取词库
ws_lib = sh.worksheet("Sheet1")
lib_data = ws_lib.get_all_values()
lib_df = pd.DataFrame(lib_data[1:], columns=[c.lower().strip() for c in lib_data[0]])

# ==========================================
# 3. 数据中枢：准备日志表 (修复版逻辑)
# ==========================================

# 获取所有工作表的标题列表
worksheet_list = [sheet.title for sheet in sh.worksheets()]

if "Learning_Log" in worksheet_list:
    # 如果存在，直接读取
    ws_log = sh.worksheet("Learning_Log")
else:
    # 如果不存在，再创建
    try:
        ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="5")
        ws_log.append_row(["date", "word", "meaning", "notes", "level"])
    except Exception as e:
        st.error(f"创建日志表失败: {e}")
        st.stop()

# 读取最新的日志数据
log_data = ws_log.get_all_values()
if len(log_data) > 1:
    raw_log_df = pd.DataFrame(log_data[1:], columns=[c.lower().strip() for c in log_data[0]])
else:
    raw_log_df = pd.DataFrame(columns=["date", "word", "meaning", "notes", "level"])

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
            with st.spinner("AI 正在为卿姐编写助记词..."):
                for item in selected:
                    item['ai_tip'] = get_ai_mnemonic(item.get('word'), item.get('meaning'))
            st.session_state['batch'] = selected

    if 'batch' in st.session_state:
        cols = st.columns(2)
        for idx, item in enumerate(st.session_state['batch']):
            word = item.get('word', 'N/A')
            with cols[idx % 2]:
                st.markdown(f"""
                    <div class="word-card-box">
                        <div class="big-word-text">{word}</div>
                        <div class="pink-tag">{item.get('meaning', '未录入')}</div>
                        <div class="ai-box">🤖 <b>AI 助记：</b>{item.get('ai_tip', '加载中...')}</div>
                    </div>
                """, unsafe_allow_html=True)
                play_audio(word)
                st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("✅ 卿姐记住了，同步云端", type="primary", use_container_width=True):
            for i in st.session_state['batch']:
                ws_log.append_row([str(datetime.date.today()), i.get('word'), i.get('meaning'), i.get('notes'), lvl])
            st.balloons(); time.sleep(1); st.rerun()

# --- Tab 2: 记忆复苏 (艾宾浩斯逻辑) ---
with tab2:
    if not raw_log_df.empty:
        raw_log_df['dt'] = pd.to_datetime(raw_log_df['date'], errors='coerce').dt.date
        today = datetime.date.today()
        targets = [today - datetime.timedelta(days=i) for i in [1, 3, 7]]
        rev_pool = raw_log_df[raw_log_df['dt'].isin(targets)].drop_duplicates('word')

        if rev_pool.empty:
            st.info("✨ 卿姐，目前的复习任务已全部完成！")
        else:
            if 'rev_queue' not in st.session_state or st.button("🔄 开启新一轮复习"):
                sample_rev = rev_pool.sample(min(len(rev_pool), 10)).to_dict('records')
                for item in sample_rev: item['count'] = 0
                st.session_state['rev_queue'] = sample_rev
                st.session_state['need_new_word'] = True

            queue = st.session_state.get('rev_queue', [])
            unfinished = [i for i in queue if i['count'] < 3]

            if not unfinished:
                st.balloons()
                st.success("🎉 10 个单词已通过‘三连击’测试！")
            else:
                if st.session_state.get('need_new_word', True):
                    st.session_state['active_word'] = random.choice(unfinished)
                    st.session_state['need_new_word'] = False
                
                curr = st.session_state['active_word']
                st.markdown(f'<p style="text-align:center; color:#9E9E9E;">强化进度: {curr["count"]}/3</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="word-card-box"><div class="big-word-text">{curr["word"]}</div><div class="pink-tag">？? ?</div></div>', unsafe_allow_html=True)
                play_audio(curr['word'])

                with st.expander("💡 提示"):
                    st.write(f"释义: {curr['meaning']}")
                
                b1, b2 = st.columns(2)
                if b1.button("✅ 记得", use_container_width=True, type="primary"):
                    for i in st.session_state['rev_queue']:
                        if i['word'] == curr['word']: i['count'] += 1
                    st.session_state['need_new_word'] = True
                    st.rerun()
                if b2.button("❌ 不记得", use_container_width=True):
                    for i in st.session_state['rev_queue']:
                        if i['word'] == curr['word']: i['count'] = 0
                    st.session_state['need_new_word'] = True
                    st.rerun()
    else:
        st.warning("词库为空，先去学习吧！")

# --- Tab 3: 足迹 (AI 诊断报告) ---
with tab3:
    if not raw_log_df.empty:
        clean_df = raw_log_df.drop_duplicates(subset=['word'], keep='last').copy()
        for col in ['meaning', 'notes', 'level']:
            if col in clean_df.columns:
                clean_df[col] = clean_df[col].apply(lambda x: "" if str(x).strip().lower() in ["nan", "n/a", "none", "", "null"] else x)

        st.markdown("### 📊 卿姐专属 AI 学习诊断")
        
        def analyze_progress(df):
            api_key = st.secrets.get("deepseek_api_key", "sk-8c10698361c24c71af07315c3abb6582")
            sample_words = df.tail(10)['word'].tolist()
            prompt = f"角色：银行英语私教。数据：卿姐已学{len(df)}词，近期词：{', '.join(sample_words)}。任务：写一段50字内的鼓励式学习分析报告，要亲切幽默。"
            try:
                res = requests.post("https://api.deepseek.com/chat/completions", 
                                    json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]},
                                    headers={"Authorization": f"Bearer {api_key}"}, timeout=8)
                return res.json()['choices'][0]['message']['content']
            except:
                return "卿姐，你的学习进度比银行存款利息增长得还稳健！继续保持哦！"

        if st.button("🪄 生成本周 AI 学习分析报告", use_container_width=True):
            with st.spinner("AI 课代表正在分析报告..."):
                report = analyze_progress(clean_df)
                st.markdown(f'<div style="background-color: #F0F2F6; padding: 20px; border-radius: 15px; border-left: 5px solid #FF69B4; color: #2C3E50;">🤖 <b>DeepSeek 诊断结果：</b><br>{report}</div>', unsafe_allow_html=True)
        
        st.divider()
        display = clean_df.reindex(columns=['date', 'word', 'meaning', 'notes', 'level']).fillna("")
        display.columns = ['学习日期', '单词', '中文释义', '我的笔记', '掌握难度']
        st.dataframe(display.sort_values('学习日期', ascending=False), use_container_width=True, hide_index=True)
