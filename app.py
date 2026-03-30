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

def analyze_learning_progress(log_df):
    """🧠 调用 DeepSeek 分析卿姐的学习足迹"""
    if log_df.empty:
        return "卿姐，目前还没有学习记录，快去开启今天的挑战吧！"
    
    # 提取最近的学习样本（例如最近20条记录）
    recent_words = log_df.tail(20)['word'].tolist()
    levels = log_df.tail(20)['level'].value_counts().to_dict()
    
    api_key = st.secrets.get("deepseek_api_key", "你的KEY")
    url = "https://api.deepseek.com/chat/completions"
    
    prompt = f"""
    你是卿姐的私人英语助教。以下是她最近的学习数据：
    - 最近学习的单词：{', '.join(recent_words)}
    - 掌握难度分布：{levels}
    
    请根据这些数据，为卿姐写一份简短的鼓励式周报建议。
    要求：
    1. 结合她银行工作的身份，分析她的学习进展。
    2. 指出她可能面临的挑战（如长词、特定难度词）。
    3. 给出一个下周的学习锦囊。
    4. 语气要像女儿/儿子的贴心伙伴，称呼她为‘卿姐’。
    """
    
    try:
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post(url, json=data, headers={"Authorization": f"Bearer {api_key}"})
        return response.json()['choices'][0]['message']['content']
    except:
        return "卿姐，AI 助教正在休息，但你的进步我全看在眼里！继续加油！"

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

# --- Tab 2: 记忆复苏 (艾宾浩斯 + 三次强化逻辑) ---
with tab2:
    # 1. 筛选需要复习的数据
    if not raw_log_df.empty:
        raw_log_df['dt'] = pd.to_datetime(raw_log_df['date'], errors='coerce').dt.date
        today = datetime.date.today()
        # 艾宾浩斯周期：1天, 3天, 7天
        targets = [today - datetime.timedelta(days=i) for i in [1, 3, 7]]
        rev_pool = raw_log_df[raw_log_df['dt'].isin(targets)].drop_duplicates('word')

        if rev_pool.empty:
            st.info("✨ 卿姐，目前的复习任务已全部完成，太棒了！")
        else:
            # 2. 初始化复习队列 (只取前10个)
            if 'rev_queue' not in st.session_state or st.button("🔄 开启新一轮复习"):
                # 选取10个，并给每个词初始化计数器为 0
                sample_rev = rev_pool.sample(min(len(rev_pool), 10)).to_dict('records')
                for item in sample_rev:
                    item['count'] = 0
                st.session_state['rev_queue'] = sample_rev
                st.session_state['current_idx'] = 0

            # 3. 检查是否全部复习完成
            queue = st.session_state['rev_queue']
            unfinished = [i for i in queue if i['count'] < 3]

            if not unfinished:
                st.balloons()
                st.success("🎉 恭喜卿姐！这 10 个单词已经通过‘三连击’测试，彻底记牢了！")
                if st.button("开始下一组"):
                    del st.session_state['rev_queue']
                    st.rerun()
            else:
                # 4. 随机抽取一个未完成的词进行展示 (实现循环随机)
                import random
                if 'active_word' not in st.session_state or st.session_state.get('need_new_word', True):
                    st.session_state['active_word'] = random.choice(unfinished)
                    st.session_state['need_new_word'] = False
                
                current_item = st.session_state['active_word']
                
                # 5. 渲染卡片界面
                st.markdown(f"""
                    <div style="text-align:center;">
                        <p style="color:#9E9E9E;">艾宾浩斯强化中 (需记得3次，当前: {current_item['count']}/3)</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class="word-card-box">
                        <div class="big-word-text">{current_item['word']}</div>
                        <div class="pink-tag">？? ?</div> 
                    </div>
                """, unsafe_allow_html=True)
                # 隐藏释义，只有点复习时才提示

                play_audio(current_item['word'])

                # 6. 交互按钮
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2:
                    with st.expander("💡 提示 (实在想不起来点这里)"):
                        st.write(f"释义: {current_item['meaning']}")
                        st.caption(f"笔记: {current_item.get('notes', '无')}")

                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button("✅ 记得", use_container_width=True, type="primary"):
                        # 找到原队列中的词并加分
                        for i in st.session_state['rev_queue']:
                            if i['word'] == current_item['word']:
                                i['count'] += 1
                        st.session_state['need_new_word'] = True
                        st.rerun()

                with btn_c2:
                    if st.button("❌ 不记得", use_container_width=True):
                        # 不记得则计数清零，重新开始
                        for i in st.session_state['rev_queue']:
                            if i['word'] == current_item['word']:
                                i['count'] = 0 
                        st.session_state['need_new_word'] = True
                        st.toast(f"没关系卿姐，咱们再多看几次 {current_item['word']}！")
                        st.rerun()
    else:
        st.warning("卿姐，还没开始打卡学习呢，先去‘卿姐挑战’攒点词汇吧！")

# --- Tab 3: 足迹 (AI 诊断 + 专项去重清洗) ---
with tab3:
    if not raw_log_df.empty:
        # 1. 数据预处理（用于 AI 分析）
        clean_df = raw_log_df.drop_duplicates(subset=['word'], keep='last').copy()
        for col in ['meaning', 'notes', 'level']:
            if col in clean_df.columns:
                clean_df[col] = clean_df[col].apply(lambda x: "" if str(x).strip().lower() in ["nan", "n/a", "none", "", "null"] else x)

        # ---------------------------------------------------------
        # 🚀 新增：AI 学习诊断模块 (放在表格上方)
        # ---------------------------------------------------------
        st.markdown("### 📊 卿姐专属 AI 学习诊断")
        
        # 定义分析函数（如果之前没定义，请放在代码上方）
        def analyze_progress(df):
            api_key = st.secrets.get("deepseek_api_key", "sk-8c10698361c24c71af07315c3abb6582")
            url = "https://api.deepseek.com/chat/completions"
            
            # 提取最近10个词做样本，让AI知道进度
            sample_words = df.tail(10)['word'].tolist()
            prompt = f"""
            角色：卿姐的私人英语助教。卿姐在银行工作。
            数据：卿姐最近学习了 {len(df)} 个词，最近攻克的词包括：{", ".join(sample_words)}。
            任务：写一段简短的周报建议（50字内）。
            要求：幽默亲切，结合银行场景鼓励她。
            """
            try:
                res = requests.post(url, json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}]
                }, headers={"Authorization": f"Bearer {api_key}"}, timeout=8)
                return res.json()['choices'][0]['message']['content']
            except:
                return "卿姐，你最近的学习势头比银行的复利还要强劲！继续保持，你是最棒的！"

        if st.button("🪄 生成本周 AI 学习分析报告", use_container_width=True):
            with st.spinner("AI 课代表正在翻看卿姐的学习笔记..."):
                report = analyze_progress(clean_df)
                st.markdown(f"""
                    <div style="background-color: #F0F2F6; padding: 20px; border-radius: 15px; border-left: 5px solid #FF69B4; color: #2C3E50;">
                        🤖 <b>DeepSeek 诊断结果：</b><br>{report}
                    </div>
                """, unsafe_allow_html=True)
        
        st.divider() # 视觉分割线
        # ---------------------------------------------------------

        # 2. 格式化表格输出 (原本的表格逻辑)
        display = clean_df.reindex(columns=['date', 'word', 'meaning', 'notes', 'level']).fillna("")
        display.columns = ['学习日期', '单词', '中文释义', '我的笔记', '掌握难度']
        
        st.write(f"📈 卿姐已累计攻克了 **{len(clean_df)}** 个唯一词汇！")
        st.dataframe(display.sort_values('学习日期', ascending=False), use_container_width=True, hide_index=True)
        
        csv = display.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 导出词汇档案", csv, f"学习档案_{datetime.date.today()}.csv", "text/csv")
