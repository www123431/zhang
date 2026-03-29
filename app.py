import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import openai
import requests
import random
from datetime import datetime, timedelta

# --- [BA 调试工具] 检查 Secrets 是否加载成功 ---
# 如果部署后报错，请查看网页顶部的列表里是否有 'G_PRIVATE_KEY'
if "G_PRIVATE_KEY" not in st.secrets:
    st.error("❌ 错误：Streamlit 后台未检测到 'G_PRIVATE_KEY'")
    st.write("当前可用的 Keys:", list(st.secrets.keys()))
    st.info("请确保在 Streamlit Cloud 的 Settings -> Secrets 中保存了配置。")
    st.stop()

# --- 1. 认证与核心配置 ---
try:
    # 格式化私钥：处理 TOML 可能带来的转义问题
    raw_key = st.secrets["G_PRIVATE_KEY"]
    formatted_key = raw_key.replace("\\n", "\n") if "\\n" in raw_key else raw_key

    # 构建 Google 服务账号凭据
    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["project_id"],
        "private_key": formatted_key,
        "client_email": st.secrets["G_CLIENT_EMAIL"],
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    
    # 其他 API 配置
    WX_APPID = st.secrets["WX_APPID"]
    WX_SECRET = st.secrets["WX_SECRET"]
    WX_TOUSER = st.secrets["WX_TOUSER"]
    WX_TEMPLATE_ID = st.secrets["WX_TEMPLATE_ID"]
    AI_API_KEY = st.secrets["AI_API_KEY"]
    
    # 确保此名称与你的 Google 表格名称完全一致
    SHEET_NAME = "Mom_English_Study" 
except Exception as e:
    st.error(f"⚠️ 初始化失败: {e}")
    st.stop()

# --- 2. 词库数据 (分类示例) ---
EASY_WORDS = ["Water", "Food", "Family", "Son", "Daughter", "Help", "Walk", "Park", "Friend", "Money", "Shop"]
MEDIUM_WORDS = ["Market", "Supermarket", "Vegetable", "Fruit", "Kitchen", "Cook", "Drink", "Breakfast", "Lunch", "Dinner"]
HARD_WORDS = ["Medicine", "Hospital", "Doctor", "Price", "Cheap", "Expensive", "Telephone", "Grandchild"]

# --- 3. 核心功能函数 ---
def get_data():
    """从 Google Sheets 读取历史"""
    try:
        sh = gc.open(SHEET_NAME)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        return pd.DataFrame(data), worksheet
    except Exception as e:
        st.error(f"表格读取失败，请检查表格名称是否为 '{SHEET_NAME}' 且已授权。")
        return pd.DataFrame(columns=["date", "words"]), None

def get_ebbinghaus_review(df):
    """艾宾浩斯复习逻辑：提取 1天前 和 4天前 的词"""
    if df.empty: return []
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    four_days_ago = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")
    
    review_rows = df[df['date'].astype(str).isin([yesterday, four_days_ago])]
    words = []
    for val in review_rows['words']:
        words.extend([w.strip() for w in str(val).split(",")])
    return list(set(words))

# --- 4. Streamlit 界面 ---
st.set_page_config(page_title="妈妈英语全自动助手", page_icon="❤️")
st.title("👵 妈妈英语：艾宾浩斯全自动版")

df, worksheet = get_data()
st.sidebar.header(f"📊 累计打卡：{len(df)} 天")

level = st.select_slider('选择难度：', options=['入门级', '进阶级', '挑战级'])
pool = {"入门级": EASY_WORDS, "进阶级": MEDIUM_WORDS, "挑战级": HARD_WORDS}[level]

# 随机抽取今日 3 个词
new_words = random.sample(pool, 3)
review_words = get_ebbinghaus_review(df)

st.write(f"🆕 **今日新词**：{', '.join(new_words)}")
if review_words:
    st.write(f"🔄 **科学复习**：{', '.join(review_words[:3])}")
else:
    st.caption("今天还没有需要复习的任务。")

# --- 5. 推送逻辑 ---
if st.button("🚀 开启今日推送并同步云端"):
    with st.spinner('🤖 AI 正在生成内容并写入表格...'):
        try:
            # AI 生成 (DeepSeek)
            client_ai = openai.OpenAI(api_key=AI_API_KEY, base_url="https://api.deepseek.com")
            prompt = f"你是一个温暖的英语老师。今日新词：{new_words}。复习：{review_words}。为妈妈写微信推送，含音标、中文、简单例句。200字内。"
            response = client_ai.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
            ai_content = response.choices[0].message.content
            
            # 微信推送
            token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
            access_token = requests.get(token_url).json().get("access_token")
            
            payload = {
                "touser": WX_TOUSER,
                "template_id": WX_TEMPLATE_ID,
                "data": {"content": {"value": ai_content, "color": "#173177"}}
            }
            wx_res = requests.post(f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}", json=payload).json()
            
            if wx_res.get("errcode") == 0:
                # 关键：全自动写入 Google Sheets
                today_str = datetime.now().strftime("%Y-%m-%d")
                worksheet.append_row([today_str, ",".join(new_words)])
                
                st.balloons()
                st.success("🎉 推送成功！数据已实时同步至云端。")
                st.info(ai_content)
            else:
                st.error(f"微信端推送失败：{wx_res}")
        except Exception as e:
            st.error(f"程序运行出错: {e}")

st.markdown("---")
st.caption("Developed by Business Analytics student for Mom. ❤️")
