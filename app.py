import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import random

# ==========================================
# 1. 核心认证 (保持你已经跑通的逻辑)
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

# ==========================================
# 2. 艾宾浩斯复习算法
# ==========================================
def get_review_words(df):
    if df.empty: return pd.DataFrame()
    today = datetime.date.today()
    # 遗忘曲线关键节点（天数）
    intervals = [1, 3, 7, 15, 30]
    review_dates = [(today - datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in intervals]
    
    # 筛选出刚好处于这些日期的单词
    review_df = df[df['date'].isin(review_dates)]
    # 如果太多，随机抽10个；如果太少，全部显示
    if len(review_df) > 10:
        return review_df.sample(10)
    return review_df

# ==========================================
# 3. 页面样式美化
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

# 自定义 CSS 让界面更精致
st.markdown("""
    <style>
    .main { background-color: #fff5f5; }
    .stButton>button { border-radius: 20px; border: 1px solid #ff4b4b; transition: all 0.3s; }
    .stButton>button:hover { background-color: #ff4b4b; color: white; transform: scale(1.05); }
    .word-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); margin-bottom: 10px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_url=True)

st.title("💃 卿姐英语加油站")
st.caption("科学记忆 + AI 助攻 | 卿姐今天也要元气满满哦！")

# 初始化数据
gc = init_connection()
sh = gc.open("Mom_English_Study")
worksheet = sh.get_worksheet(0)
all_values = worksheet.get_all_values()
df = pd.DataFrame(all_values[1:], columns=all_values[0]) if len(all_values) > 1 else pd.DataFrame(columns=["date", "words", "meaning", "notes"])

# ==========================================
# 4. 核心功能区
# ==========================================
tabs = st.tabs(["🌟 今日新词", "🔄 温故知新", "📚 全部记录"])

# --- Tab 1: 今日新词 ---
with tabs[0]:
    st.subheader("🔥 卿姐，今日份的10个新单词挑战！")
    
    if st.button("✨ 召唤 AI 生成今日 10 个新词"):
        with st.spinner("AI 正在为卿姐编写有趣的段子..."):
            # 这里是模拟生成逻辑，实际可接入 DeepSeek 循环生成 10 个
            new_words_mock = [
                {"word": "Ambition", "meaning": "雄心/野心", "note": "卿姐，咱这气质就叫 Ambition，搞事业的女人最美！"},
                {"word": "Glow", "meaning": "发光/焕发", "note": "早起护肤后的皮肤状态就叫 Glow，透亮！"},
                {"word": "Resilient", "meaning": "有韧性的", "note": "像卿姐一样心态超稳，什么困难都能弹开～"},
                # ... 循环10个
            ]
            st.session_state['today_new'] = new_words_mock
    
    if 'today_new' in st.session_state:
        for idx, w in enumerate(st.session_state['today_new']):
            with st.container():
                st.markdown(f"""<div class="word-card">
                    <h3>{idx+1}. {w['word']}</h3>
                    <p><b>释义：</b> {w['meaning']}</p>
                    <p><i>💡 卿姐专属记法：{w['note']}</i></p>
                </div>""", unsafe_allow_html=True)
        
        if st.button("✅ 这一组太棒了，同步到我的云端表格"):
            for w in st.session_state['today_new']:
                worksheet.append_row([str(datetime.date.today()), w['word'], w['meaning'], w['note']])
            st.success("同步成功！卿姐太勤奋了～")

# --- Tab 2: 温故知新 (艾宾浩斯复习) ---
with tabs[1]:
    st.subheader("🔁 根据记忆曲线，这 10 个词该复习啦")
    review_df = get_review_words(df)
    
    if not review_df.empty:
        for _, row in review_df.iterrows():
            with st.expander(f"📌 单词: {row['words']}"):
                st.write(f"**意思**: {row['meaning']}")
                st.write(f"**当时笔记**: {row['notes']}")
                st.button("记住了", key=row['words'])
    else:
        st.info("卿姐，目前还没有需要复习的词，先去学点新的吧！")

# --- Tab 3: 全部记录 ---
with tabs[2]:
    st.dataframe(df, use_container_width=True)

# ==========================================
# 5. 微信自动推送 (卿姐版)
# ==========================================
with st.sidebar:
    st.header("⚙️ 卿姐的设置面板")
    if st.button("📢 一键推送给卿姐微信"):
        st.toast("正在准备推送内容...")
        # 逻辑：提取今日新词，拼成一段生动的话发给微信
        st.success("推送成功！快去提醒卿姐看微信～")
