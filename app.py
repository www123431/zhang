import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import requests

# ==========================================
# 1. 核心认证 (使用已验证的 Secrets 逻辑)
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
# 2. 艾宾浩斯复习算法 (基于日期筛选)
# ==========================================
def get_ebbinghaus_reviews(df):
    if df.empty: return pd.DataFrame()
    
    # 确保日期列是标准格式
    df['date'] = pd.to_datetime(df['date']).dt.date
    today = datetime.date.today()
    
    # 记忆曲线节点：1天前, 3天前, 7天前
    intervals = [1, 3, 7]
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    
    # 筛选出需要复习的行
    review_df = df[df['date'].isin(target_dates)]
    return review_df.head(10) # 每天建议复习10个

# ==========================================
# 3. 页面样式美化 (卿姐专属 UI)
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFF9FB; }
    /* 新词卡片：红色左边框 */
    .word-card { 
        background: white; padding: 1.5rem; border-radius: 1rem; 
        border-left: 6px solid #FF4B4B; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem;
    }
    /* 复习卡片：深粉色顶边框 */
    .review-card {
        background: #F8F9FA; padding: 1.2rem; border-radius: 0.8rem;
        border-top: 4px solid #D02090; margin-bottom: 0.5rem;
        text-align: center;
    }
    .level-tag {
        display: inline-block; padding: 2px 8px; border-radius: 5px;
        background: #FFE4E1; color: #D02090; font-size: 0.7rem; margin-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💃 卿姐英语加油站")
st.write(f"今天是 {datetime.date.today()} | 卿姐，保持优雅，持续进阶！✨")

# 加载数据
gc = init_connection()
sh = gc.open("Mom_English_Study")
worksheet = sh.get_worksheet(0)
all_vals = worksheet.get_all_values()

# 数据框初始化
if len(all_vals) > 1:
    df = pd.DataFrame(all_vals[1:], columns=all_vals[0])
else:
    # 如果是空表，初始化结构
    df = pd.DataFrame(columns=["date", "words", "meaning", "notes", "level"])

# ==========================================
# 4. 侧边栏：难度调节
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/bubbles/200/woman-profile.png")
    st.header("⚙️ 学习偏好")
    selected_level = st.select_slider(
        "选择今日词汇难度：",
        options=["🌱 元气生活", "✨ 时尚达人", "💪 职场精英"],
        value="✨ 时尚达人"
    )
    st.info(f"当前模式：{selected_level}")
    st.divider()
    if st.button("📢 推送至卿姐微信"):
        st.toast("推送指令已发出...")

# ==========================================
# 5. 主功能区：Tab 布局
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战 (10词)", "🔄 记忆复苏 (卡片)", "📚 全部档案"])

# --- Tab 1: 今日新词 ---
with tab1:
    st.subheader(f"🔥 卿姐，挑战今日的 {selected_level} 词汇吧！")
    
    if st.button("🚀 召唤 AI 生成 10 个单词"):
        with st.spinner("AI 正在根据卿姐的品味定制单词..."):
            # 模拟生成逻辑
            time.sleep(1.5)
            mock_words = [
                {"words": f"Radiant_{i}", "meaning": "光彩照人", "notes": "卿姐气场全开！"} 
                for i in range(1, 11)
            ]
            st.session_state['new_words_list'] = mock_words

    if 'new_words_list' in st.session_state:
        for item in st.session_state['new_words_list']:
            st.markdown(f"""
                <div class="word-card">
                    <div class="level-tag">{selected_level}</div>
                    <h3 style="margin:0; color:#FF4B4B;">{item['words']}</h3>
                    <p style="margin-top:10px;"><b>释义：</b>{item['meaning']}</p>
                    <p style="color:#666; font-size:0.9rem;"><i>💡 助记：{item['notes']}</i></p>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 确认并打卡存入表格", type="primary", use_container_width=True):
            for item in st.session_state['new_words_list']:
                # 存入表格：日期, 单词, 释义, 笔记, 难度
                worksheet.append_row([str(datetime.date.today()), item['words'], item['meaning'], item['notes'], selected_level])
            st.success("存入成功！卿姐今天也超棒的！🌸")
            time.sleep(1)
            st.rerun()

# --- Tab 2: 记忆复苏 (精致卡片化) ---
with tab2:
    st.subheader("🔁 卿姐，这几个词需要回想一下哦")
    review_df = get_ebbinghaus_reviews(df)
    
    if not review_df.empty:
        # 使用两列布局展示复习卡片
        review_items = review_df.to_dict('records')
        cols = st.columns(2)
        
        for idx, row in enumerate(review_items):
            with cols[idx % 2]:
                st.markdown(f"""
                    <div class="review-card">
                        <span style="font-size:0.7rem; color:gray;">📅 学习日期: {row.get('date')}</span>
                        <h4 style="margin:8px 0; color:#D02090;">{row.get('words')}</h4>
                    </div>
                """, unsafe_allow_html=True)
                
                # “翻面”查看详情
                with st.expander("🔍 揭晓答案"):
                    st.write(f"**意思**: {row.get('meaning')}")
                    st.write(f"**助记**: {row.get('notes')}")
                    st.caption(f"难度: {row.get('level', '默认')}")
                    if st.button("我记住了", key=f"check_{idx}"):
                        st.toast("厉害了卿姐！")
    else:
        st.info("卿姐，目前暂时没有需要复习的词，先去学点新的吧！")

# --- Tab 3: 全部档案 ---
with tab3:
    st.subheader("📚 卿姐的学习足迹")
    if not df.empty:
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("档案室还是空的，开始卿姐的第一课吧！")
