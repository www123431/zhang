import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time

# ==========================================
# 1. 核心认证 (使用你已跑通的 Secrets 逻辑)
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
# 2. 艾宾浩斯复习逻辑 (BA 自动化筛选)
# ==========================================
def get_review_data(df):
    if df.empty: return pd.DataFrame()
    # 确保日期格式统一
    df['date'] = pd.to_datetime(df['date']).dt.date
    today = datetime.date.today()
    # 遗忘曲线节点：1天前, 3天前, 7天前
    intervals = [1, 3, 7]
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    
    review_df = df[df['date'].isin(target_dates)]
    return review_df.head(10) # 每天复习前10个

# ==========================================
# 3. 页面配置与 UI 美化
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

# 修正后的 CSS
st.markdown("""
    <style>
    .stApp { background-color: #FFF9FB; }
    .word-card { 
        background: white; 
        padding: 1.5rem; 
        border-radius: 1rem; 
        border-left: 6px solid #FF4B4B;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    .review-tag { color: #FF4B4B; font-weight: bold; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("💃 卿姐英语加油站")
st.write(f"今天是 {datetime.date.today()} | 卿姐，今天也要元气满满哦！✨")

# 加载数据
gc = init_connection()
sh = gc.open("Mom_English_Study")
worksheet = sh.get_worksheet(0)
all_vals = worksheet.get_all_values()

# 数据框初始化 (处理空表头情况)
if len(all_vals) > 1:
    df = pd.DataFrame(all_vals[1:], columns=all_vals[0])
else:
    df = pd.DataFrame(columns=["date", "words", "meaning", "notes"])

# ==========================================
# 4. 核心功能 Tab
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 今日新词 (10个)", "🔄 艾宾浩斯复习", "📚 学习档案"])

with tab1:
    st.subheader("🔥 卿姐，今日份的新词挑战！")
    
    if st.button("🚀 召唤 AI 生成 10 个生动词汇"):
        with st.spinner("正在为卿姐量身定制内容..."):
            # 模拟 AI 生成 10 个词的列表
            # 实际接入时，请在这里循环调用 DeepSeek API
            new_list = []
            words_pool = [
                ("Elegance", "优雅", "卿姐的代名词！记法：饿了也保持精致(Gance)，就是优雅。"),
                ("Sparkle", "闪耀", "卿姐眼睛里有星辰！记法：Spark(火花)+le，每天闪亮亮。"),
                ("Confident", "自信", "搞事业的卿姐最美。记法：Con(全部)+fident(信任)，全方位相信自己！"),
                ("Radiant", "光彩照人", "形容卿姐今天的气色。记法：像Radius(半径)一样散发光芒。"),
                ("Fabulous", "棒极了", "卿姐做的决定总是 Fabulous！"),
                ("Vibrant", "充满活力的", "卿姐每天的能量值。"),
                ("Wisdom", "智慧", "岁月沉淀的美。"),
                ("Inspire", "鼓舞", "卿姐总是能激励身边的人。"),
                ("Graceful", "得体的", "举手投足间的魅力。"),
                ("Balance", "平衡", "卿姐最擅长平衡生活与爱好。")
            ]
            for w, m, n in words_pool:
                new_list.append({"date": str(datetime.date.today()), "words": w, "meaning": m, "notes": n})
            
            st.session_state['new_words'] = new_list

    if 'new_words' in st.session_state:
        for item in st.session_state['new_words']:
            st.markdown(f"""
                <div class="word-card">
                    <span style="color:gray; font-size:0.8rem;">NEW单词</span>
                    <h3 style="margin:0;">{item['words']}</h3>
                    <p><b>意思：</b>{item['meaning']}</p>
                    <p style="color:#555;"><i>💡 卿姐助记：{item['notes']}</i></p>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 确认并同步到表格", type="primary"):
            for item in st.session_state['new_words']:
                worksheet.append_row([item['date'], item['words'], item['meaning'], item['notes']])
            st.success("同步成功！卿姐太勤奋了，奖励一朵小红花 🌹")
            time.sleep(1)
            st.rerun()

with tab2:
    st.subheader("🔁 卿姐，温故而知新")
    review_data = get_review_data(df)
    
    if not review_data.empty:
        st.write("根据艾宾浩斯遗忘曲线，这几个词需要卿姐回想一下哦：")
        for _, row in review_data.iterrows():
            with st.expander(f"✨ 单词: {row['words']}"):
                st.write(f"**意思**: {row['meaning']}")
                st.write(f"**助记**: {row['notes']}")
                st.write(f"**初次学习日期**: {row['date']}")
                st.button("记住了！", key=f"btn_{row['words']}")
    else:
        st.info("卿姐，目前还没有复习任务，继续保持哦！")

with tab3:
    st.subheader("📚 卿姐的学习足迹")
    st.dataframe(df, use_container_width=True)

# 侧边栏推送
with st.sidebar:
    st.image("https://img.icons8.com/bubbles/200/woman-profile.png")
    st.header("卿姐专属后台")
    if st.button("📢 推送今日单词至微信"):
        st.info("推送功能开发中...（需配置微信 Secrets）")
