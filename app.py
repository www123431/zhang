import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

def init_connection():
    try:
        # 1. 关键改动：使用 .to_dict() 将只读的 Secrets 转为可修改的普通字典
        creds_dict = st.secrets["gcp_service_account"].to_dict()
        
        # 2. 现在我们可以安全地清洗私钥格式了
        if "private_key" in creds_dict:
            # 替换转义字符并去除首尾空格
            fixed_key = creds_dict["private_key"].replace("\\n", "\n").strip()
            creds_dict["private_key"] = fixed_key
            
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        
        # 3. 使用修改后的字典进行认证
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证连接失败: {e}")
        st.info("提示：这通常是由于 Secrets 格式或私钥粘贴不完整导致的。")
        st.stop()

# --- 页面 UI 部分 ---
st.set_page_config(page_title="妈妈英语助手", page_icon="👵")
st.title("👵 妈妈英语全自动助手")

# 执行初始化连接
gc = init_connection()

try:
    # ⚠️ 这里的名字必须与你的 Google Sheet 文件名完全一致
    sh = gc.open("Mom_English_Study") 
    worksheet = sh.get_worksheet(0)
    
    st.success("✅ 认证成功！已连接到云端表格。")
    
    # 读取数据显示
    data = worksheet.get_all_records()
    if data:
        st.subheader("📊 学习进度预览")
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("💡 表格目前是空的，快去添加第一个单词吧！")

except Exception as e:
    st.error(f"📊 无法读取表格: {e}")
    # 自动获取当前机器人的邮箱，方便用户复制去分享
    client_email = st.secrets["gcp_service_account"].get("client_email", "未知邮箱")
    st.markdown(f"""
    **排查步骤：**
    1. 确认表格名称确实是 `Mom_English_Study`。
    2. 确认你已在表格里点击 **“分享”**。
    3. 确认已将 **Editor (编辑者)** 权限给到：`{client_email}`
    """)
