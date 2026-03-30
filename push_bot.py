import os
import datetime
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. 配置参数 (从 GitHub Secrets 中读取，保护隐私)
CORP_ID = os.environ["CORP_ID"]
CORP_SECRET = os.environ["CORP_SECRET"]
AGENT_ID = os.environ["AGENT_ID"]
TO_USER = "obahu3Eh-YsOPCEQjwlwHqZHOfqM"
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]

# 2. 初始化 Google Sheets 连接
def get_sheet_data(sheet_name):
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # 你的 Service Account JSON 存放在 Secrets 里
    creds_dict = eval(os.environ["GOOGLE_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return pd.DataFrame(client.open("Sheet1").worksheet(sheet_name).get_all_records())

# 3. AI 生成有趣的消息
def get_ai_msg(task_type):
    hour = datetime.datetime.now().hour + 8 # 转换到新加坡时间
    weather = "新加坡依然是热情的 31 度" # 这里可以接入天气 API，或者让 AI 随机发挥
    
    prompt = f"你是银行英语私教。现在是{hour}点，背景：{weather}。任务：卿姐还没做今天的{task_type}，请写一段50字内幽默的催促语，多用银行术语（资产、利息、呆账、对账、入账）。"
    
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
    res = requests.post("https://api.deepseek.com/chat/completions", json=data, headers=headers)
    return res.json()['choices'][0]['message']['content']

# 4. 发送企业微信
def send_wx(msg):
    token = requests.get(f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}").json()['access_token']
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload = {"touser": TO_USER, "msgtype": "text", "agentid": AGENT_ID, "text": {"content": msg}}
    requests.post(url, json=payload)

# 5. 执行主逻辑
today_str = str(datetime.date.today())
hour_now = (datetime.datetime.now().hour + 8) % 24 # 转新加坡时间

if hour_now < 12: # 早晨检查
    df = get_sheet_data("Learning_Log")
    if today_str not in df['date'].astype(str).values:
        send_wx(get_ai_msg("学习入账"))
else: # 下午检查
    df = get_sheet_data("Review_Log")
    if today_str not in df['date'].astype(str).values:
        send_wx(get_ai_msg("复习对账"))
