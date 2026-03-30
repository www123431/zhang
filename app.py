import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

def init_connection():
    try:
        # 获取 Secrets 中的信息
        creds_info = st.secrets["gcp_service_account"]
        
        # 核心修复：自动处理私钥中的换行符和空格
        if "private_key" in creds_info:
            # 处理可能的双重转义，并去除每一行前后的不可见空格
            fixed_key = creds_info["private_key"].replace("\\n", "\n").strip()
            creds_info["private_key"] = fixed_key
            
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ 认证连接失败: {e}")
        st.stop()

st.title("👵 妈妈英语全自动助手")

# 执行连接
gc = init_connection()

try:
    # ⚠️ 请确保表格名字是 Mom_English_Study
    sh = gc.open("Mom_English_Study") 
    worksheet = sh.get_worksheet(0)
    st.success("✅ 认证成功！已连接到 Google Sheets 表格。")
    
    # 读取数据显示
    data = worksheet.get_all_records()
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.info("💡 表格目前是空的。")

except Exception as e:
    st.error(f"📊 无法读取表格: {e}")
    email = st.secrets["gcp_service_account"]["client_email"]
    st.markdown(f"**关键提醒：** 请检查 Google 表格是否已点击“共享”，并将编辑器权限给到：`{email}`")
