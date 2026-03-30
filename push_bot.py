import os
import datetime
import requests
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials

# 1. 基础配置 (从 GitHub Secrets 读取)
CORP_ID = os.environ["CORP_ID"]
CORP_SECRET = os.environ["CORP_SECRET"]
AGENT_ID = os.environ["AGENT_ID"]
TO_USER = "ZhangXiZhe"
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]

def get_sheet_data():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # 🌟 优化点：使用 json.loads 替代 eval，解决解析报错
    creds_dict = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # 打开你的 Google Sheet (请确保你的表名是 Sheet1)
    sh = client.open("Sheet1")
    
    # 获取新加坡当前小时 (UTC+8)
    hour_now = (datetime.datetime.now().hour + 8) % 24
    
    if hour_now < 12: # 早上 8 点任务
        try:
            ws = sh.worksheet("Learning_Log")
        except:
            ws = sh.get_worksheet(0)
        return pd.DataFrame(ws.get_all_records()), "学习入账"
    else: # 下午 2 点任务
        try:
            ws = sh.worksheet("Review_Log")
        except:
            ws = sh.get_worksheet(1) if len(sh.worksheets()) > 1 else sh.get_worksheet(0)
        return pd.DataFrame(ws.get_all_records()), "复习对账"

def get_ai_msg(task_type):
    # 模拟天气情境增加趣味性
    weather = "新加坡午后可能有阵雨"
    prompt = f"你是幽默的银行英语私教。卿姐还没完成{task_type}，请写一段50字内催促语。背景：{weather}。要求：多用银行术语（资产、呆账、坏账、清收、平账），语气亲切幽默。"
    
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
    try:
        res = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=12)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"卿姐，您的今日{task_type}尚未入账，为了记忆资产的安全，请及时对账！"

def send_wx(msg):
    # 获取企业微信 Token
    token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}"
    token = requests.get(token_url).json().get('access_token')
    
    # 发送文本消息
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload = {
        "touser": TO_USER,
        "msgtype": "text",
        "agentid": AGENT_ID,
        "text": {"content": msg}
    }
    requests.post(url, json=payload)

# --- 执行主逻辑 ---
try:
    # 1. 尝试获取数据
    df, task_name = get_sheet_data()
    
    # 2. 🌟 智能对账模式：只有没记录时才发送
    today_str = str(datetime.date.today())
    # 检查日期字段（兼容表头名字）
    date_col = 'date' if 'date' in df.columns else df.columns[0]
    has_record = today_str in df[date_col].astype(str).values

    if not has_record:
        print(f"📡 检测到今日未入账，正在申请 AI 催清收...")
        msg = get_ai_msg(task_name)
        send_wx(msg)
        print(f"✅ 提醒已发送: {task_name}")
    else:
        print(f"✅ 今日已完成{task_name}，资产状态正常，无需提醒。")

except Exception as e:
    error_msg = f"❌ 脚本运行失败: {str(e)}"
    print(error_msg)
    try:
        send_wx(f"系统审计报告：运行出错。详情：{str(e)[:100]}")
    except:
        pass
