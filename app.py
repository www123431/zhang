import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import random

# ==========================================
# 1. 核心认证
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
# 2. 艾宾浩斯 & 长度过滤逻辑
# ==========================================
def get_ebbinghaus_reviews(df):
    if df.empty: return pd.DataFrame()
    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    today = datetime.date.today()
    intervals = [1, 3, 7, 15] 
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    # 筛选匹配日期的行
    return df[df['date_dt'].isin(target_dates)]

def filter_by_length(df, level):
    if df.empty: return pd.DataFrame()
    # 根据你的词书，单词列名为 'words' (同步到云端后的列名)
    words_col = 'words'
    if level == "🌱 简单 (长度 <= 5)":
        return df[df[words_col].str.len() <= 5]
    elif level == "✨ 中等 (长度 6-9)":
        return df[(df[words_col].str.len() >= 6) & (df[words_col].str.len() <= 9)]
    else: # 💪 挑战 (长度 >= 10)
        return df[df[words_col].str.len() >= 10]

# ==========================================
# 3. 页面样式
# ==========================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFF9FB; }
    .word-card { 
        background: white; padding: 1.5rem; border-radius: 1rem; 
        border-left: 6px solid #FF4B4B; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 1rem;
    }
    .review-card {
        background: #F8F9FA; padding: 1.2rem; border-radius: 0.8rem;
        border-top: 4px solid #D02090; margin-bottom: 0.5rem; text-align: center;
    }
    .level-tag {
        display: inline-block; padding: 2px 8px; border-radius: 5px;
        background: #FFE4E1; color: #D02090; font-size: 0.75rem; margin-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💃 卿姐英语加油站")

# 加载数据
gc = init_connection()
sh = gc.open("Mom_English_Study")
worksheet = sh.get_worksheet(0)
all_vals = worksheet.get_all_values()

# 处理云端表格列名映射
if len(all_vals) > 1:
    # 按照 Google Sheet 里的顺序：A(date), B(words), C(meaning), D(notes), E(level)
    df = pd.DataFrame(all_vals[1:], columns=all_vals[0][:5])
else:
    df = pd.DataFrame(columns=["date", "words", "meaning", "notes", "level"])

# ==========================================
# 4. 侧边栏：上传与难度
# ==========================================
with st.sidebar:
    st.header("⚙️ 学习配置")
    selected_level = st.select_slider(
        "调节今日难度：",
        options=["🌱 简单 (长度 <= 5)", "✨ 中等 (长度 6-9)", "💪 挑战 (长度 >= 10)"],
        value="🌱 简单 (长度 <= 5)"
    )
    
    st.divider()
    st.subheader("📚 导入卿姐专属词书")
    uploaded_file = st.file_uploader("上传 CSV (格式: Index, Word, Category, Chinese)", type="csv")
    
    if uploaded_file:
        # 读取上传的词书
        up_df = pd.read_csv(uploaded_file)
        st.write("📋 预览上传内容：", up_df.head(3))
        
        if st.button("📥 点击导入云端词库"):
            with st.spinner("正在同步数据..."):
                # 按照表格结构导入：日期, 单词(Word), 释义(Chinese), 备注(Category), 来源
                for _, row in up_df.iterrows():
                    worksheet.append_row([
                        str(datetime.date.today()), 
                        str(row['Word']), 
                        str(row['Chinese']), 
                        f"词性: {row['Category']}", 
                        "词书导入"
                    ])
                st.success("导入成功！")
                time.sleep(1)
                st.rerun()

# ==========================================
# 5. 主功能 Tabs
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战", "🔄 记忆复苏", "📚 学习档案"])

with tab1:
    st.subheader(f"🔥 今日任务：{selected_level}")
    if st.button("🚀 开始抽取 10 个词"):
        # 执行长度过滤
        filtered_df = filter_by_length(df, selected_level)
        if len(filtered_df) >= 10:
            st.session_state['today_batch'] = filtered_df.sample(10).to_dict('records')
        elif not filtered_df.empty:
            st.session_state['today_batch'] = filtered_df.to_dict('records')
            st.warning(f"题库中该难度的词不足 10 个，已全部展示。")
        else:
            st.info("当前难度库为空，请先上传词书或切换难度。")

    if 'today_batch' in st.session_state:
        for item in st.session_state['today_batch']:
            st.markdown(f"""
                <div class="word-card">
                    <div class="level-tag">{selected_level}</div>
                    <h3 style="margin:0; color:#FF4B4B;">{item['words']}</h3>
                    <p style="margin-top:10px;"><b>中文释义：</b>{item['meaning']}</p>
                    <p style="color:#666; font-size:0.9rem;"><i>💡 笔记：{item['notes']}</i></p>
                </div>
            """, unsafe_allow_html=True)

with tab2:
    st.subheader("🔁 艾宾浩斯翻牌卡片")
    review_data = get_ebbinghaus_reviews(df)
    if not review_data.empty:
        cols = st.columns(2)
        for idx, row in enumerate(review_data.to_dict('records')):
            with cols[idx % 2]:
                st.markdown(f'<div class="review-card"><h4>{row["words"]}</h4></div>', unsafe_allow_html=True)
                with st.expander("👀 揭晓答案"):
                    st.write(f"**意思**: {row['meaning']}")
                    st.caption(f"**笔记**: {row['notes']}")
    else:
        st.info("✨ 卿姐，目前没有需要复习的任务。")

with tab3:
    st.dataframe(df, use_container_width=True)
