import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import time
import random

# ==========================================
# 1. 核心认证 (使用 Secrets 逻辑)
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
# 2. 艾宾浩斯复习算法 (基于 Learning_Log)
# ==========================================
def get_ebbinghaus_reviews(log_df):
    """根据遗忘曲线节点从记录中回溯筛选"""
    if log_df.empty: return pd.DataFrame()
    
    # 统一转换日期格式进行计算
    log_df['date_dt'] = pd.to_datetime(log_df['date'], errors='coerce').dt.date
    today = datetime.date.today()
    
    # 记忆节点：1, 3, 7, 15天
    intervals = [1, 3, 7, 15]
    target_dates = [today - datetime.timedelta(days=i) for i in intervals]
    
    return log_df[log_df['date_dt'].isin(target_dates)]

# ==========================================
# 3. 页面样式美化 (卿姐专属 UI)
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

# 加载数据连接
gc = init_connection()

# --- 4. 数据加载与容错处理 ---
try:
    # 这里的名字需与你 Google Sheets 左上角标题完全一致
    sh = gc.open("Sheet1") 
except:
    st.error("❌ 找不到名为 'Sheet1' 的文件。请检查文件名或共享权限。")
    st.stop()

# 加载 Sheet1 (词库)
ws_lib = sh.worksheet("Sheet1")
lib_data = ws_lib.get_all_values()
if len(lib_data) > 1:
    lib_df = pd.DataFrame(lib_data[1:], columns=lib_data[0])
    # 【修复 KeyError】强制统一列名为小写并去除空格
    lib_df.columns = [c.lower().strip() for c in lib_df.columns]
    # 建立映射字典：确保代码引用的字段始终存在
    name_map = {'words': 'word', 'word': 'word', 'chinese': 'chinese', 'category': 'category'}
    lib_df = lib_df.rename(columns=name_map)
else:
    lib_df = pd.DataFrame(columns=['word', 'chinese', 'category'])

# 加载 Learning_Log (学习记录)
try:
    ws_log = sh.worksheet("Learning_Log")
except:
    ws_log = sh.add_worksheet(title="Learning_Log", rows="1000", cols="10")
    ws_log.append_row(["date", "word", "chinese", "category", "level"])

log_data = ws_log.get_all_values()
if len(log_data) > 1:
    log_df = pd.DataFrame(log_data[1:], columns=log_data[0])
else:
    log_df = pd.DataFrame(columns=["date", "word", "chinese", "category", "level"])

# ==========================================
# 5. 主功能区
# ==========================================
tab1, tab2, tab3 = st.tabs(["🌟 今日挑战 (10词)", "🔄 记忆复苏 (卡片)", "📚 学习足迹"])

# --- Tab 1: 今日挑战 ---
with tab1:
    with st.sidebar:
        st.header("⚙️ 配置")
        selected_level = st.select_slider(
            "难度调节：",
            options=["🌱 简单 (<=5字)", "✨ 中等 (6-9字)", "💪 挑战 (>=10字)"],
            value="🌱 简单 (<=5字)"
        )
        st.divider()
        # 下载按钮：方便卿姐把云端记录存回本地
        if not log_df.empty:
            csv = log_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下载最新学习记录", data=csv, file_name=f"卿姐学习记录_{datetime.date.today()}.csv")

    st.subheader(f"🔥 今日任务：{selected_level}")
    
    if st.button("🚀 抽取 10 个新词"):
        if not lib_df.empty:
            # 单词长度分级逻辑
            if "简单" in selected_level:
                f = lib_df[lib_df['word'].str.len() <= 5]
            elif "中等" in selected_level:
                f = lib_df[(lib_df['word'].str.len() > 5) & (lib_df['word'].str.len() <= 9)]
            else:
                f = lib_df[lib_df['word'].str.len() > 9]
            
            if not f.empty:
                st.session_state['quiz_batch'] = f.sample(min(len(f), 10)).to_dict('records')
            else:
                st.info("当前难度词库为空，请尝试其他难度或上传词书。")
        else:
            st.warning("Sheet1 是空的，请先在侧边栏上传词书。")

    if 'quiz_batch' in st.session_state:
        for item in st.session_state['quiz_batch']:
            st.markdown(f"""
                <div class="word-card">
                    <h3 style="margin:0; color:#FF4B4B;">{item.get('word', 'N/A')}</h3>
                    <p style="margin-top:10px;"><b>释义：</b>{item.get('chinese', 'N/A')}</p>
                    <p style="color:#666; font-size:0.85rem;"><i>💡 词性: {item.get('category', 'N/A')}</i></p>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("✅ 卿姐记住了，打卡存入云端记录", type="primary", use_container_width=True):
            for item in st.session_state['quiz_batch']:
                # 写入 Learning_Log 标签页
                ws_log.append_row([
                    str(datetime.date.today()), 
                    item.get('word'), 
                    item.get('chinese'), 
                    item.get('category'), 
                    selected_level
                ])
            st.success("🎉 打卡成功！数据已实时存入 Google Sheets。")
            time.sleep(1)
            st.rerun()

# --- Tab 2: 记忆复苏 (艾宾浩斯) ---
with tab2:
    st.subheader("🔄 艾宾浩斯科学复习")
    # 只针对已打卡的记录进行回溯
    review_data = get_ebbinghaus_reviews(log_df)
    
    if not review_data.empty:
        st.caption(f"📢 卿姐，今日有 {len(review_data)} 个词触发了复习节点")
        cols = st.columns(2)
        for idx, row in enumerate(review_data.to_dict('records')):
            with cols[idx % 2]:
                st.markdown(f'<div class="review-card"><h4>{row["word"]}</h4></div>', unsafe_allow_html=True)
                with st.expander("揭晓答案"):
                    st.write(f"**中文**: {row['chinese']}")
                    st.write(f"**笔记**: {row['category']}")
    else:
        st.info("✨ 卿姐太棒了！今日暂无复习任务。")

# --- Tab 3: 学习记录查询 ---
with tab3:
    st.subheader("📚 卿姐的学习足迹 (Learning_Log)")
    if not log_df.empty:
        st.dataframe(log_df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("还没有打卡记录哦。")
