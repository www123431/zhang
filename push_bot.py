import os
import datetime
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. 基础配置
CORP_ID = os.environ["CORP_ID"]
CORP_SECRET = os.environ["CORP_SECRET"]
AGENT_ID = os.environ["AGENT_ID"]
TO_USER = "obahu3Eh-YsOPCEQjwlwHqZHOfqM"
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]

def get_sheet_data():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = eval(os.environ["GOOGLE_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # 🌟 兼容性升级：自动查找现有的表，防止名字对不上报错
    sh = client.open("Sheet1")
    
    # 获取新加坡当前小时
    hour_now = (datetime.datetime.now().hour + 8) % 24
    
    if hour_now < 12: # 早上查学习记录
        try:
            ws = sh.worksheet("Learning_Log")
        except:
            ws = sh.get_worksheet(0) # 如果没有这个名，直接拿第一个 Tab
        return pd.DataFrame(ws.get_all_records()), "学习入账"
    else: # 下午查复习记录
        try:
            ws = sh.worksheet("Review_Log")
        except:
            ws = sh.get_worksheet(1) if len(sh.worksheets()) > 1 else sh.get_worksheet(0)
        return pd.DataFrame(ws.get_all_records()), "复习对账"

def get_ai_msg(task_type):
    prompt = f"你是幽默的银行英语私教。卿姐今天还没完成{task_type}，请写一段50字内的催促语。要求：用银行术语（资产、呆账、结转、入账），语气要亲切幽默。"
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
    try:
        res = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=10)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"卿姐，您的知识资产今天还没‘对账’哦，记得打卡{task_type}！"

def send_wx(msg):
    token = requests.get(f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}").json()['access_token']
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload = {"touser": TO_USER, "msgtype": "text", "agentid": AGENT_ID, "text": {"content": msg}}
    requests.post(url, json=payload)

# 执行主逻辑
try:
    df, task_name = get_sheet_data()
    today_str = str(datetime.date.today())
    
    # 检查日期字段（兼容 date 或学习日期等表头）
    date_col = 'date' if 'date' in df.columns else df.columns[0]
    has_record = today_str in df[date_col].astype(str).values
    
    if not has_record:
        msg = get_ai_msg(task_name)
        send_wx(msg)
        print(f"提醒已发送: {task_name}")
    else:
        print(f"今日已完成{task_name}，无需提醒。")
except Exception as e:
    print(f"报错详情: {e}")
    # 发送一个调试信息到微信，让你知道是哪报错了
    send_wx(f"调试提醒：脚本报错了，错误信息：{str(e)[:100]}")
