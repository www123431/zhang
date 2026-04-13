import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import requests
import random
from io import BytesIO
from gtts import gTTS

# =====================================================================
# 1. 页面配置 & CSS
# =====================================================================
st.set_page_config(page_title="卿姐英语加油站", page_icon="💃", layout="wide")
st.markdown("""
<style>
.stApp { background-color: #FDFBFF; }
.word-card-box {
    background: white; padding: 36px 30px; border-radius: 25px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.06); border: 1px solid #F0F0F0;
    text-align: center; margin-bottom: 12px; min-height: 200px;
}
.word-card-hard { background: #FFF5F5 !important; border-color: #FED7D7 !important; }
.big-word-text { font-family: 'Georgia', serif; font-size: 3.5rem; font-weight: 900; color: #2C3E50; line-height: 1.2; }
.phonetic-text { font-size: 1.1rem; color: #718096; margin: 6px 0; letter-spacing: 0.5px; }
.pink-tag { font-size: 1.6rem; color: #D02090; background: #FFF0F5; padding: 6px 28px; border-radius: 50px; font-weight: bold; display: inline-block; margin-top: 10px; }
.hidden-tag { font-size: 1.6rem; color: #CBD5E0; background: #F7FAFC; padding: 6px 28px; border-radius: 50px; font-weight: bold; display: inline-block; margin-top: 10px; border: 2px dashed #CBD5E0; }
.ai-box { background: #F0FFF4; border-left: 5px solid #48BB78; padding: 14px 16px; border-radius: 12px; margin-top: 12px; font-size: 0.95rem; color: #2D3748; text-align: left; }
.example-box { background: #EBF8FF; border-left: 5px solid #4299E1; padding: 14px 16px; border-radius: 12px; margin-top: 8px; font-size: 0.95rem; color: #2D3748; text-align: left; }
.sub-label { font-size: 0.78rem; color: #A0AEC0; background: #F7FAFC; padding: 4px 14px; border-radius: 8px; margin-bottom: 10px; display: inline-block; }
.metric-card { background: white; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. 基础工具函数
# =====================================================================

def init_connection():
    """初始化 Google Sheets 连接"""
    creds_dict = st.secrets["gcp_service_account"].to_dict()
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)


def play_audio(word):
    """TTS 发音"""
    try:
        tts = gTTS(text=str(word), lang="en")
        fp = BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, format="audio/mp3")
    except Exception:
        st.caption("🔊 语音加载中…")


def get_phonetic(word):
    """从免费词典 API 获取 IPA 音标（无需 key）"""
    try:
        resp = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower().strip()}",
            timeout=4,
        )
        data = resp.json()
        if isinstance(data, list) and data:
            for p in data[0].get("phonetics", []):
                if p.get("text"):
                    return p["text"]
    except Exception:
        pass
    return ""


def analyze_progress_ai(df):
    """AI 学习诊断报告（传入真实词汇数据）"""
    api_key = st.secrets.get("deepseek_api_key", "")
    if not api_key:
        return "卿姐，你的学习资产负债表相当漂亮！继续保持！"
    sample = df["word"].tail(12).tolist() if len(df) > 0 else []
    prompt = (
        f"角色：银行英语私教。\n"
        f"数据：卿姐已学 {len(df)} 词，最近学的有：{', '.join(sample[:10])}。\n"
        f"任务：写 60 字以内的学习诊断报告，用银行术语（资产、坏账、逾期、清收、平账）评价，幽默亲切。"
    )
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=10,
        )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return "卿姐，你的学习资产负债表相当漂亮！继续保持！"


# =====================================================================
# 3. 个性化记忆画像系统
# =====================================================================

def profile_get(df_profile: pd.DataFrame, key: str, default: str = "") -> str:
    """从 Memory_Profile 表读取某个字段"""
    if df_profile.empty or "key" not in df_profile.columns:
        return default
    row = df_profile[df_profile["key"] == key]
    return str(row.iloc[0]["value"]) if not row.empty else default


def build_local_profile(log_df: pd.DataFrame, srs_df: pd.DataFrame) -> dict:
    """
    从本地数据提取客观统计指标，供 AI 分析使用。
    不含任何 AI 推断，只有真实数据。
    """
    profile = {
        "total_learned": 0,
        "avg_ef": 2.5,
        "days_active": 0,
        "hard_words_ctx": "",   # 顽固词+释义，给 AI 分析
        "easy_words_ctx": "",   # 掌握好的词+释义，给 AI 分析
        "hard_words_list": [],
    }

    if not log_df.empty and "word" in log_df.columns:
        unique_log = log_df.drop_duplicates("word")
        profile["total_learned"] = len(unique_log)
        if "date" in log_df.columns:
            profile["days_active"] = log_df["date"].nunique()

        # 构建 word→meaning 映射
        if "meaning" in log_df.columns:
            wm = unique_log.set_index("word")["meaning"].to_dict()
        else:
            wm = {}
    else:
        wm = {}

    if not srs_df.empty and "ease_factor" in srs_df.columns:
        srs_w = srs_df.copy()
        srs_w["ease_factor"] = pd.to_numeric(srs_w["ease_factor"], errors="coerce").fillna(2.5)
        srs_w["repetitions"] = pd.to_numeric(srs_w.get("repetitions", pd.Series()), errors="coerce").fillna(0)

        profile["avg_ef"] = round(float(srs_w["ease_factor"].mean()), 2)

        hard = srs_w[srs_w["ease_factor"] < 1.8].sort_values("ease_factor").head(12)
        easy = srs_w[srs_w["ease_factor"] > 3.0].sort_values("ease_factor", ascending=False).head(12)

        profile["hard_words_list"] = hard["word"].tolist()
        profile["hard_words_ctx"] = "、".join(
            f"{w}（{wm.get(w, '?')}）" for w in hard["word"].tolist()
        ) or "暂无"
        profile["easy_words_ctx"] = "、".join(
            f"{w}（{wm.get(w, '?')}）" for w in easy["word"].tolist()
        ) or "暂无"

    return profile


def get_ai_profile_analysis(local_profile: dict) -> dict:
    """
    让 DeepSeek 深度分析卿姐的个人记忆规律。
    返回结构化的画像字典，写入 Memory_Profile 表持久化。
    """
    api_key = st.secrets.get("deepseek_api_key", "")
    if not api_key:
        return {}

    prompt = f"""你是专业的英语记忆认知专家，正在为"卿姐"（银行资深员工）建立个人记忆档案。

【客观学习数据】
- 已学词汇总量：{local_profile["total_learned"]} 个
- 平均掌握度（EF值）：{local_profile["avg_ef"]}（2.5为标准，越高越好）
- 累计学习天数：{local_profile["days_active"]} 天
- 反复遗忘的顽固词：{local_profile["hard_words_ctx"]}
- 快速掌握的优质词：{local_profile["easy_words_ctx"]}

【分析任务】
请像真正的记忆教练一样，从以上数据中找出卿姐独特的记忆规律，按格式输出：

记忆特点：[从顽固词和优质词中分析她的记忆偏好，例如：她更容易记住什么类型的词（具体/抽象、长/短、熟悉场景/陌生场景），什么特征的词容易遗忘，2-3句具体分析]
助记风格：[根据她的记忆特点，推荐最适合她的助记策略，要具体（如：谐音联想/故事串联/图像记忆/场景嵌入），并说明为什么这种方式最适合她]
强化重点：[从顽固词中挑出最需要本周突破的3个词，逐词给出针对性攻克建议]
节奏建议：[根据她的整体数据（EF均值、学习天数），建议每日新词量、复习频率是否需要调整，要有具体数字]"""

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        content = resp.json()["choices"][0]["message"]["content"].strip()
        parsed = {}
        for line in content.split("\n"):
            for key in ["记忆特点", "助记风格", "强化重点", "节奏建议"]:
                if line.startswith(f"{key}：") or line.startswith(f"{key}:"):
                    parsed[key] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        return parsed
    except Exception:
        return {}


def save_memory_profile(profile_data: dict):
    """将 AI 分析结果写入 Memory_Profile 表"""
    gc = init_connection()
    sh = gc.open("Sheet1")
    try:
        ws = sh.worksheet("Memory_Profile")
    except Exception:
        ws = sh.add_worksheet("Memory_Profile", rows="20", cols="2")
        ws.append_row(["key", "value"])

    existing = ws.get_all_values()
    key_row = {r[0]: i + 1 for i, r in enumerate(existing) if r}

    profile_data["last_updated"] = str(datetime.date.today())
    for k, v in profile_data.items():
        if k in key_row:
            ws.update_cell(key_row[k], 2, str(v))
        else:
            ws.append_row([k, str(v)])


def get_ai_word_info_smart(word: str, meaning: str, profile_ctx: str = "") -> tuple:
    """
    DeepSeek 助记 + 例句：核心升级版。
    当有记忆画像时，AI 会根据卿姐的个人记忆特点定制助记策略，
    而不是每次都套用同一个银行场景模板。
    """
    api_key = st.secrets.get("deepseek_api_key", "")
    if not api_key:
        return "💡 结合银行日常业务来记忆这个词。", ""

    if profile_ctx:
        profile_line = (
            f"\n【卿姐的个人记忆特点】{profile_ctx}\n"
            f"请严格根据以上特点选择最适合她的助记方式，不要用通用银行场景模板。"
        )
    else:
        profile_line = ""

    prompt = (
        f"你是卿姐（银行员工）的专属英语记忆教练。{profile_line}\n\n"
        f"请为单词 '{word}'（释义：{meaning}）设计：\n"
        f"1. 助记：叫"卿姐"，30字内，根据她的记忆特点选最有效的方式\n"
        f"2. 例句：银行场景英文例句 + 中文翻译\n\n"
        f"严格按格式输出：\n"
        f"助记：[内容]\n"
        f"例句：[English]（[中文]）"
    )
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            },
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        content = resp.json()["choices"][0]["message"]["content"].strip()
        mnemonic, example = "", ""
        for line in content.split("\n"):
            if line.startswith("助记："):
                mnemonic = line.replace("助记：", "").strip()
            elif line.startswith("例句："):
                example = line.replace("例句：", "").strip()
        return mnemonic or "💡 结合银行日常业务来记忆这个词。", example
    except Exception:
        return "💡 结合银行日常业务来记忆这个词。", ""


# =====================================================================
# 4. SM-2 间隔重复算法
# =====================================================================

def save_srs_results(rev_results: list):
    """将 SM-2 复习结果批量写入 Words_SRS，返回 True/False"""
    gc = init_connection()
    sh = gc.open("Sheet1")
    try:
        ws_srs = sh.worksheet("Words_SRS")
    except Exception:
        ws_srs = sh.add_worksheet("Words_SRS", rows="2000", cols="6")
        ws_srs.append_row(["word", "ease_factor", "interval", "repetitions", "next_review_date", "last_review_date"])

    existing = ws_srs.get_all_values()
    word_row_map = {r[0]: i + 2 for i, r in enumerate(existing[1:]) if r}

    for res in rev_results:
        w = res["word"]
        nxt = str(datetime.date.today() + datetime.timedelta(days=res["interval"]))
        row = [w, str(res["ef"]), str(res["interval"]), str(res["reps"]), nxt, str(datetime.date.today())]
        if w in word_row_map:
            ws_srs.update(f"A{word_row_map[w]}:F{word_row_map[w]}", [row])
        else:
            ws_srs.append_row(row)
    return True

def sm2_update(ease_factor: float, interval: int, repetitions: int, quality: int):
    """
    SM-2 算法核心：
    quality 0-5  (0=完全忘, 2=模糊, 4=记得, 5=脱口而出)
    返回 (new_ef, new_interval, new_reps)
    """
    if quality >= 3:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ease_factor)
        new_reps = repetitions + 1
    else:
        new_interval = 1
        new_reps = 0

    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, round(new_ef, 3))
    return new_ef, new_interval, new_reps


# =====================================================================
# 4. 数据层（一次性读取全部，300s 缓存）
# =====================================================================

@st.cache_data(ttl=300)
def fetch_all_data():
    try:
        gc = init_connection()
        sh = gc.open("Sheet1")
        ws_titles = [w.title for w in sh.worksheets()]

        # ── 词库 ──────────────────────────────────────────────────────
        ws_lib = sh.worksheet("Sheet1")
        lib_raw = ws_lib.get_all_values()
        df_lib = (
            pd.DataFrame(lib_raw[1:], columns=[c.lower().strip() for c in lib_raw[0]])
            if len(lib_raw) > 1
            else pd.DataFrame(columns=["word", "meaning"])
        )

        # ── 学习日志 ──────────────────────────────────────────────────
        if "Learning_Log" not in ws_titles:
            ws_log = sh.add_worksheet(title="Learning_Log", rows="2000", cols="5")
            ws_log.append_row(["date", "word", "meaning", "notes", "level"])
            df_log = pd.DataFrame(columns=["date", "word", "meaning", "notes", "level"])
        else:
            ws_log = sh.worksheet("Learning_Log")
            log_raw = ws_log.get_all_values()
            df_log = (
                pd.DataFrame(log_raw[1:], columns=[c.lower().strip() for c in log_raw[0]])
                if len(log_raw) > 1
                else pd.DataFrame(columns=["date", "word", "meaning", "notes", "level"])
            )

        # ── SRS 记忆数据 ──────────────────────────────────────────────
        if "Words_SRS" not in ws_titles:
            ws_srs = sh.add_worksheet(title="Words_SRS", rows="2000", cols="6")
            ws_srs.append_row(["word", "ease_factor", "interval", "repetitions", "next_review_date", "last_review_date"])
            df_srs = pd.DataFrame(columns=["word", "ease_factor", "interval", "repetitions", "next_review_date", "last_review_date"])
        else:
            ws_srs = sh.worksheet("Words_SRS")
            srs_raw = ws_srs.get_all_values()
            df_srs = (
                pd.DataFrame(srs_raw[1:], columns=[c.lower().strip() for c in srs_raw[0]])
                if len(srs_raw) > 1
                else pd.DataFrame(columns=["word", "ease_factor", "interval", "repetitions", "next_review_date", "last_review_date"])
            )

        # ── 用户设置 ──────────────────────────────────────────────────
        if "User_Settings" not in ws_titles:
            ws_cfg = sh.add_worksheet(title="User_Settings", rows="20", cols="2")
            ws_cfg.append_row(["key", "value"])
            ws_cfg.append_row(["daily_new_words", "10"])
            ws_cfg.append_row(["daily_review_words", "20"])
            df_cfg = pd.DataFrame(
                [["daily_new_words", "10"], ["daily_review_words", "20"]],
                columns=["key", "value"],
            )
        else:
            ws_cfg = sh.worksheet("User_Settings")
            cfg_raw = ws_cfg.get_all_values()
            df_cfg = (
                pd.DataFrame(cfg_raw[1:], columns=[c.lower().strip() for c in cfg_raw[0]])
                if len(cfg_raw) > 1
                else pd.DataFrame(columns=["key", "value"])
            )

        # ── 记忆画像 ──────────────────────────────────────────────
        if "Memory_Profile" not in ws_titles:
            ws_mp = sh.add_worksheet(title="Memory_Profile", rows="20", cols="2")
            ws_mp.append_row(["key", "value"])
            df_profile = pd.DataFrame(columns=["key", "value"])
        else:
            ws_mp = sh.worksheet("Memory_Profile")
            mp_raw = ws_mp.get_all_values()
            df_profile = (
                pd.DataFrame(mp_raw[1:], columns=["key", "value"])
                if len(mp_raw) > 1
                else pd.DataFrame(columns=["key", "value"])
            )

        return df_lib, df_log, df_srs, df_cfg, df_profile

    except Exception as e:
        st.error(f"🚨 连接表格失败：{e}")
        return (
            pd.DataFrame(columns=["word", "meaning"]),
            pd.DataFrame(columns=["date", "word", "meaning", "notes", "level"]),
            pd.DataFrame(columns=["word", "ease_factor", "interval", "repetitions", "next_review_date", "last_review_date"]),
            pd.DataFrame(columns=["key", "value"]),
            pd.DataFrame(columns=["key", "value"]),
        )


def cfg_get(df_cfg: pd.DataFrame, key: str, default: int) -> int:
    if df_cfg.empty or "key" not in df_cfg.columns:
        return default
    row = df_cfg[df_cfg["key"] == key]
    if row.empty:
        return default
    try:
        return int(row.iloc[0]["value"])
    except Exception:
        return default


# =====================================================================
# 5. 全局数据 & 预计算
# =====================================================================
lib_df, log_df, srs_df, cfg_df, profile_df = fetch_all_data()

# 从画像表提取记忆特点，供 AI 助记使用（空则 AI 用通用模式）
profile_ctx = profile_get(profile_df, "记忆特点")

today = datetime.date.today()
today_str = str(today)

# 今日已学词数
if not log_df.empty and "date" in log_df.columns and "word" in log_df.columns:
    today_learned_words = set(log_df[log_df["date"] == today_str]["word"].tolist())
else:
    today_learned_words = set()
today_count = len(today_learned_words)

# 连续打卡天数
streak = 0
if not log_df.empty and "date" in log_df.columns:
    learned_dates = sorted(
        pd.to_datetime(log_df["date"], errors="coerce").dt.date.dropna().unique(),
        reverse=True,
    )
    check = today
    for d in learned_dates:
        if d == check:
            streak += 1
            check -= datetime.timedelta(days=1)
        elif d < check:
            break

# 设置值（从云端，已在 sidebar 可覆盖）
default_new = cfg_get(cfg_df, "daily_new_words", 10)
default_rev = cfg_get(cfg_df, "daily_review_words", 20)

# =====================================================================
# 6. 侧栏：设置 + 状态
# =====================================================================
with st.sidebar:
    st.markdown("## ⚙️ 学习计划")
    daily_new = st.slider("每日新词目标", 5, 50, default_new, key="sl_new")
    daily_rev = st.slider("每日复习目标", 5, 100, default_rev, key="sl_rev")

    if st.button("💾 保存计划", use_container_width=True):
        try:
            gc2 = init_connection()
            ws_cfg2 = gc2.open("Sheet1").worksheet("User_Settings")
            all_cfg = ws_cfg2.get_all_values()
            key_to_row = {r[0]: i + 1 for i, r in enumerate(all_cfg) if r}
            if "daily_new_words" in key_to_row:
                ws_cfg2.update_cell(key_to_row["daily_new_words"], 2, str(daily_new))
            else:
                ws_cfg2.append_row(["daily_new_words", str(daily_new)])
            if "daily_review_words" in key_to_row:
                ws_cfg2.update_cell(key_to_row["daily_review_words"], 2, str(daily_rev))
            else:
                ws_cfg2.append_row(["daily_review_words", str(daily_rev)])
            st.cache_data.clear()
            st.success("✅ 已保存！")
        except Exception as e:
            st.error(f"保存失败：{e}")

    st.divider()
    st.markdown("### 📊 今日状态")
    st.metric("🔥 连续打卡", f"{streak} 天")
    st.progress(
        min(today_count / max(daily_new, 1), 1.0),
        text=f"今日新词：{today_count} / {daily_new}",
    )

    # 复习进度
    if not srs_df.empty and "last_review_date" in srs_df.columns:
        rev_today = len(srs_df[srs_df["last_review_date"] == today_str])
    else:
        rev_today = 0
    st.progress(
        min(rev_today / max(daily_rev, 1), 1.0),
        text=f"今日复习：{rev_today} / {daily_rev}",
    )

    st.divider()
    st.markdown("### 📥 词库导入")
    st.caption("支持 .txt 格式，每行：单词[tab或逗号]释义")
    uploaded = st.file_uploader("上传词库文件", type=["txt"], label_visibility="collapsed")
    if uploaded:
        try:
            raw_text = uploaded.read().decode("utf-8")
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            parsed = []
            for line in lines:
                sep = "\t" if "\t" in line else ","
                parts = line.split(sep, 1)
                if len(parts) == 2:
                    parsed.append([parts[0].strip(), parts[1].strip()])

            if parsed:
                st.write(f"识别到 **{len(parsed)}** 条，预览前 3 条：")
                st.dataframe(
                    pd.DataFrame(parsed[:3], columns=["单词", "释义"]),
                    hide_index=True, use_container_width=True,
                )
                if st.button("✅ 确认导入", use_container_width=True):
                    gc3 = init_connection()
                    ws_lib3 = gc3.open("Sheet1").worksheet("Sheet1")
                    # 去重：已有的词不重复导入
                    existing_words = set(lib_df["word"].str.lower().tolist()) if not lib_df.empty else set()
                    new_rows = [p for p in parsed if p[0].lower() not in existing_words]
                    if new_rows:
                        ws_lib3.append_rows(new_rows)
                        st.cache_data.clear()
                        st.success(f"✅ 新增 {len(new_rows)} 词（跳过 {len(parsed)-len(new_rows)} 重复）")
                    else:
                        st.info("所有词已在词库中，无需导入。")
            else:
                st.warning("未识别到有效数据，请检查格式。")
        except Exception as e:
            st.error(f"导入失败：{e}")

# =====================================================================
# 7. 主体：四个 Tab
# =====================================================================
tab1, tab2, tab3, tab4 = st.tabs(["📖 今日学习", "🔄 智能复习", "🎯 AI 挑战", "📊 学习足迹"])


# ─────────────────────────────────────────────────────────────────────
# Tab 1：今日学习（主动回忆 · 逐词翻牌）
# ─────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 📖 今日新词学习")

    col_p, col_n = st.columns([3, 1])
    with col_p:
        st.progress(min(today_count / max(daily_new, 1), 1.0))
    with col_n:
        st.markdown(f"**{today_count} / {daily_new}**")

    if today_count >= daily_new:
        st.success(f"🎉 卿姐今日 {daily_new} 词全部完成！去复习巩固一下吧～")
    else:
        # 可学的词 = 词库中未学过的词
        if not lib_df.empty and "word" in lib_df.columns:
            all_learned = set(log_df["word"].tolist()) if not log_df.empty and "word" in log_df.columns else set()
            unlearned = lib_df[~lib_df["word"].isin(all_learned)].reset_index(drop=True)
        else:
            unlearned = pd.DataFrame()

        if unlearned.empty:
            st.info("🎊 词库全部学完！去复习巩固吧。")
        else:
            # 初始化批次
            need_init = "learn_batch" not in st.session_state
            if need_init:
                batch_n = min(daily_new - today_count, len(unlearned))
                batch = unlearned.head(batch_n).to_dict("records")
                st.session_state.update({
                    "learn_batch": batch,
                    "learn_idx": 0,
                    "learn_flipped": False,
                    "learn_ai_cache": {},
                    "learn_confirmed": set(),
                })

            batch = st.session_state["learn_batch"]
            idx = st.session_state["learn_idx"]
            confirmed = st.session_state["learn_confirmed"]

            # ── 全部翻完，等待同步 ─────────────────────────────────
            if idx >= len(batch):
                to_sync = [w for w in batch if w["word"] in confirmed]
                unconfirmed = [w for w in batch if w["word"] not in confirmed]

                st.markdown(f"✅ **本批 {len(batch)} 词翻完！** 记住了 **{len(to_sync)}** 词，还没记住 **{len(unconfirmed)}** 词。")

                if to_sync:
                    if st.button("☁️ 同步记住的词并继续", type="primary", use_container_width=True):
                        try:
                            gc4 = init_connection()
                            ws4 = gc4.open("Sheet1").worksheet("Learning_Log")
                            rows = [
                                [today_str, w.get("word"), w.get("meaning", ""), "", "新学"]
                                for w in to_sync
                            ]
                            ws4.append_rows(rows)
                            st.cache_data.clear()
                            st.balloons()
                            for k in ["learn_batch", "learn_idx", "learn_flipped", "learn_ai_cache", "learn_confirmed"]:
                                st.session_state.pop(k, None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"同步失败：{e}")

                if unconfirmed:
                    col_r1, col_r2 = st.columns(2)
                    if col_r1.button(f"🔁 重试没记住的 {len(unconfirmed)} 词", use_container_width=True):
                        # 只重置索引和翻牌状态，把 batch 换成未确认的词
                        st.session_state["learn_batch"] = unconfirmed
                        st.session_state["learn_idx"] = 0
                        st.session_state["learn_flipped"] = False
                        st.session_state["learn_confirmed"] = set()
                        st.rerun()
                    if col_r2.button("⏭️ 跳过，学下一批", use_container_width=True):
                        # 先同步已记住的（如果有），再清空 batch
                        if to_sync:
                            try:
                                gc4b = init_connection()
                                ws4b = gc4b.open("Sheet1").worksheet("Learning_Log")
                                ws4b.append_rows([
                                    [today_str, w.get("word"), w.get("meaning", ""), "", "新学"]
                                    for w in to_sync
                                ])
                                st.cache_data.clear()
                            except Exception:
                                pass
                        for k in ["learn_batch", "learn_idx", "learn_flipped", "learn_ai_cache", "learn_confirmed"]:
                            st.session_state.pop(k, None)
                        st.rerun()

            # ── 显示当前单词卡 ─────────────────────────────────────
            else:
                curr = batch[idx]
                word = curr.get("word", "")
                meaning = curr.get("meaning", "未录入")
                flipped = st.session_state["learn_flipped"]

                # 翻牌后才加载 AI + 音标（缓存到 session）
                ai_cache = st.session_state["learn_ai_cache"]
                if flipped and word not in ai_cache:
                    with st.spinner("AI 正在根据你的记忆特点生成助记…"):
                        mnemonic, example = get_ai_word_info_smart(word, meaning, profile_ctx)
                        phonetic = get_phonetic(word)
                        ai_cache[word] = {"mnemonic": mnemonic, "example": example, "phonetic": phonetic}
                    st.session_state["learn_ai_cache"] = ai_cache

                ai = ai_cache.get(word, {})
                phonetic_html = f'<div class="phonetic-text">{ai.get("phonetic","")}</div>' if flipped and ai.get("phonetic") else ""
                meaning_html = f'<div class="pink-tag">{meaning}</div>' if flipped else '<div class="hidden-tag">？？？</div>'

                # 进度标记
                st.markdown(
                    f'<div style="text-align:right"><span class="sub-label">{idx+1} / {len(batch)}</span></div>',
                    unsafe_allow_html=True,
                )

                st.markdown(f"""
                <div class="word-card-box">
                    <div class="big-word-text">{word}</div>
                    {phonetic_html}
                    {meaning_html}
                </div>
                """, unsafe_allow_html=True)

                play_audio(word)

                if flipped:
                    if ai.get("mnemonic"):
                        st.markdown(f'<div class="ai-box">🤖 <b>AI 助记：</b>{ai["mnemonic"]}</div>', unsafe_allow_html=True)
                    if ai.get("example"):
                        st.markdown(f'<div class="example-box">📝 <b>例句：</b>{ai["example"]}</div>', unsafe_allow_html=True)

                    col_ok, col_no = st.columns(2)
                    if col_ok.button("✅ 记住了", use_container_width=True, type="primary", key="learn_ok"):
                        st.session_state["learn_confirmed"].add(word)
                        st.session_state["learn_idx"] += 1
                        st.session_state["learn_flipped"] = False
                        st.rerun()
                    if col_no.button("❌ 还没记住", use_container_width=True, key="learn_no"):
                        st.session_state["learn_idx"] += 1
                        st.session_state["learn_flipped"] = False
                        st.rerun()
                else:
                    if st.button("👀 翻开看答案", use_container_width=True, type="primary", key="learn_flip"):
                        st.session_state["learn_flipped"] = True
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────
# Tab 2：智能复习（SM-2 自适应 · 优先顽固词 · 逾期补救）
# ─────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 🔄 智能复习（SM-2 自适应）")

    if log_df.empty or "word" not in log_df.columns:
        st.warning("卿姐还没有学习记录，先去学几个词吧！")
    else:
        all_learned_df = log_df.drop_duplicates("word", keep="last").copy()

        # 计算哪些词今天需要复习
        if not srs_df.empty and "word" in srs_df.columns and "next_review_date" in srs_df.columns:
            srs_work = srs_df.copy()
            srs_work["next_review_date"] = pd.to_datetime(
                srs_work["next_review_date"], errors="coerce"
            ).dt.date
            srs_work["ease_factor"] = pd.to_numeric(srs_work["ease_factor"], errors="coerce").fillna(2.5)

            # 逾期 or 今日到期
            due_mask = srs_work["next_review_date"] <= today
            due_words = set(srs_work[due_mask]["word"].tolist())

            # 学了但还没进入 SRS 的词（首次复习）
            srs_word_set = set(srs_work["word"].tolist())
            first_review = set(all_learned_df["word"].tolist()) - srs_word_set

            review_candidates = all_learned_df[
                all_learned_df["word"].isin(due_words | first_review)
            ].copy()

            # 顽固词（EF 小）优先
            ef_map = srs_work.set_index("word")["ease_factor"].to_dict()
            review_candidates["ef"] = review_candidates["word"].map(ef_map).fillna(2.5)
            review_candidates = review_candidates.sort_values("ef")
        else:
            # 还没有 SRS 数据，所有学过的词都加入
            review_candidates = all_learned_df.copy()
            review_candidates["ef"] = 2.5

        total_due = len(review_candidates)

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("待复习", f"{total_due} 词")
        col_m2.metric("今日已复习", f"{rev_today} / {daily_rev}")
        overdue_n = int((
            pd.to_datetime(srs_df.get("next_review_date", pd.Series()), errors="coerce").dt.date < today
        ).sum()) if not srs_df.empty and "next_review_date" in srs_df.columns else 0
        col_m3.metric("🔴 逾期未复习", f"{overdue_n} 词")

        if review_candidates.empty:
            st.success("✨ 今日复习全部完成！记忆账户余额充裕！")
        else:
            limit = min(daily_rev, total_due)

            if "rev_queue" not in st.session_state or st.button("🔄 刷新复习列表", key="rev_refresh"):
                pool = review_candidates.head(limit).to_dict("records")
                # 附上当前 SM-2 状态
                srs_idx = {} if srs_df.empty else srs_df.set_index("word").to_dict("index")
                for item in pool:
                    srs_row = srs_idx.get(item["word"], {})
                    item["ef"] = float(srs_row.get("ease_factor", 2.5) or 2.5)
                    item["interval"] = int(srs_row.get("interval", 1) or 1)
                    item["reps"] = int(srs_row.get("repetitions", 0) or 0)
                st.session_state["rev_queue"] = pool
                st.session_state["rev_idx"] = 0
                st.session_state["rev_flipped"] = False
                st.session_state["rev_results"] = []
                st.session_state["rev_ai_cache"] = {}

            queue = st.session_state["rev_queue"]
            rev_idx = st.session_state["rev_idx"]
            rev_results = st.session_state["rev_results"]
            done_n = len(rev_results)

            st.progress(done_n / max(len(queue), 1))
            st.markdown(f"**{done_n} / {len(queue)}** 已复习")

            # ── 全部完成：自动保存，无需手动点击 ─────────────────
            if rev_idx >= len(queue):
                # 首次到达完成页面时自动保存
                if not st.session_state.get("rev_saved", False):
                    with st.spinner("正在自动保存复习结果…"):
                        try:
                            save_srs_results(rev_results)
                            st.cache_data.clear()
                            st.session_state["rev_saved"] = True
                        except Exception as e:
                            st.error(f"自动保存失败，请截图联系儿子：{e}")

                if st.session_state.get("rev_saved", False):
                    if not st.session_state.get("rev_balloons_done", False):
                        st.balloons()
                        st.session_state["rev_balloons_done"] = True
                    st.success(f"🎉 卿姐太棒了！{len(queue)} 个词全部复习完成，已自动保存！")
                    if st.button("✅ 完成，回到首页", type="primary", use_container_width=True):
                        for k in ["rev_queue", "rev_idx", "rev_flipped", "rev_results",
                                  "rev_ai_cache", "rev_saved", "rev_balloons_done"]:
                            st.session_state.pop(k, None)
                        st.rerun()

            # ── 显示当前复习卡 ─────────────────────────────────────
            else:
                curr = queue[rev_idx]
                word = curr.get("word", "")
                meaning = curr.get("meaning", "")
                ef = curr.get("ef", 2.5)
                flipped = st.session_state["rev_flipped"]

                hardness = "🔴 顽固词" if ef < 1.8 else ("🟡 普通" if ef < 2.5 else "🟢 掌握良好")
                nxt_days = curr.get("interval", 1)

                # 翻牌后加载音标 + AI 助记/例句（缓存避免重复调用）
                rev_ai_cache = st.session_state.get("rev_ai_cache", {})
                if flipped and word not in rev_ai_cache:
                    with st.spinner("AI 根据你的记忆特点生成复习提示…"):
                        mnemonic, example = get_ai_word_info_smart(word, meaning, profile_ctx)
                        phonetic = get_phonetic(word)
                        rev_ai_cache[word] = {"mnemonic": mnemonic, "example": example, "phonetic": phonetic}
                    st.session_state["rev_ai_cache"] = rev_ai_cache

                rev_ai = rev_ai_cache.get(word, {})
                phonetic_html = f'<div class="phonetic-text">{rev_ai["phonetic"]}</div>' if flipped and rev_ai.get("phonetic") else ""
                card_class = "word-card-box word-card-hard" if ef < 1.8 else "word-card-box"
                meaning_html = f'<div class="pink-tag">{meaning}</div>' if flipped else '<div class="hidden-tag">？？？</div>'

                st.markdown(f"""
                <div class="{card_class}">
                    <div class="sub-label">{hardness} | 上次间隔 {nxt_days} 天</div>
                    <div class="big-word-text">{word}</div>
                    {phonetic_html}
                    {meaning_html}
                </div>
                """, unsafe_allow_html=True)

                play_audio(word)

                if not flipped:
                    if st.button("👀 翻开看答案", use_container_width=True, type="primary", key="rev_flip"):
                        st.session_state["rev_flipped"] = True
                        st.rerun()
                else:
                    if rev_ai.get("mnemonic"):
                        st.markdown(f'<div class="ai-box">🤖 <b>AI 助记：</b>{rev_ai["mnemonic"]}</div>', unsafe_allow_html=True)
                    if rev_ai.get("example"):
                        st.markdown(f'<div class="example-box">📝 <b>例句：</b>{rev_ai["example"]}</div>', unsafe_allow_html=True)
                    st.markdown("**我记得这个词…**")
                    b1, b2, b3, b4 = st.columns(4)

                    def do_review(q):
                        new_ef, new_iv, new_rp = sm2_update(ef, curr["interval"], curr["reps"], q)
                        st.session_state["rev_results"].append({
                            "word": word, "ef": new_ef, "interval": new_iv, "reps": new_rp
                        })
                        st.session_state["rev_idx"] += 1
                        st.session_state["rev_flipped"] = False
                        st.rerun()

                    if b1.button("❌ 完全忘了", use_container_width=True, key="rv0"): do_review(0)
                    if b2.button("😅 有点模糊", use_container_width=True, key="rv2"): do_review(2)
                    if b3.button("✅ 记得", use_container_width=True, type="primary", key="rv4"): do_review(4)
                    if b4.button("⭐ 脱口而出", use_container_width=True, key="rv5"): do_review(5)


# ─────────────────────────────────────────────────────────────────────
# Tab 3：AI 挑战（选择题测试）
# ─────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 🎯 AI 挑战：选词配义")

    if log_df.empty or "word" not in log_df.columns:
        st.warning("先去学一些词再来挑战！")
    else:
        learned_recs = log_df.drop_duplicates("word", keep="last").to_dict("records")
        all_meanings = (
            lib_df["meaning"].dropna().tolist()
            if not lib_df.empty and "meaning" in lib_df.columns
            else [r.get("meaning", "") for r in learned_recs]
        )

        if len(learned_recs) < 4:
            st.info(f"至少需要学 4 个词才能参与挑战（当前 {len(learned_recs)} 词），加油！")
        else:
            quiz_size = st.slider("题目数量", 3, 10, 5, key="quiz_size")

            def gen_quiz():
                items = []
                pool = [r for r in learned_recs if r.get("meaning")]
                sample = random.sample(pool, min(quiz_size, len(pool)))
                for w in sample:
                    correct = w["meaning"]
                    wrongs = [m for m in all_meanings if m and m != correct]
                    if len(wrongs) < 3:
                        continue
                    opts = random.sample(wrongs, 3) + [correct]
                    random.shuffle(opts)
                    items.append({"word": w["word"], "correct": correct, "options": opts})
                return items

            if st.button("🎲 出新题", use_container_width=True, type="primary", key="quiz_gen") \
                    or "quiz_items" not in st.session_state:
                st.session_state["quiz_items"] = gen_quiz()
                st.session_state["quiz_answers"] = {}
                st.session_state["quiz_done"] = False

            items = st.session_state.get("quiz_items", [])
            answers = st.session_state.get("quiz_answers", {})
            done = st.session_state.get("quiz_done", False)

            for i, q in enumerate(items):
                st.markdown(f"**第 {i+1} 题** ｜ `{q['word']}` 的意思是？")
                if done:
                    if answers.get(i) == q["correct"]:
                        st.success(f"✅ 正确：{q['correct']}")
                    else:
                        st.error(f"❌ 你选了「{answers.get(i,'未选')}」，正确答案：{q['correct']}")
                else:
                    choice = st.radio(
                        f"q{i}", q["options"],
                        key=f"quiz_q{i}_{q['word']}",
                        label_visibility="collapsed",
                    )
                    answers[i] = choice
                st.session_state["quiz_answers"] = answers
                st.divider()

            if not done:
                if st.button("📝 提交答案", use_container_width=True, type="primary", key="quiz_submit"):
                    st.session_state["quiz_done"] = True
                    st.rerun()
            else:
                score = sum(1 for i, q in enumerate(items) if answers.get(i) == q["correct"])
                pct = int(score / max(len(items), 1) * 100)
                if pct == 100:
                    st.balloons()
                    st.success(f"🏆 满分 {score}/{len(items)}！卿姐太厉害了！")
                elif pct >= 60:
                    st.info(f"🎯 得分 {score}/{len(items)}（{pct}%），继续加油！")
                else:
                    st.warning(f"💪 得分 {score}/{len(items)}（{pct}%），这几个词需要多练练～")
                if st.button("🔄 换一组题目", use_container_width=True, key="quiz_again"):
                    st.session_state.pop("quiz_items", None)
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────
# Tab 4：学习足迹（统计 · AI诊断 · 顽固词 · 全词表）
# ─────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 📊 学习足迹")

    if log_df.empty:
        st.info("还没有学习记录，去学几个词吧！")
    else:
        clean_df = log_df.drop_duplicates(subset=["word"], keep="last").copy()
        total_words = len(clean_df)

        # 掌握度统计
        if not srs_df.empty and "ease_factor" in srs_df.columns:
            srs_ef = pd.to_numeric(srs_df["ease_factor"], errors="coerce").fillna(2.5)
            mastered_n = int((srs_ef >= 2.5).sum())
            hard_n = int((srs_ef < 1.8).sum())
        else:
            mastered_n = 0
            hard_n = 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📚 总学词数", total_words)
        m2.metric("🔥 连续打卡", f"{streak} 天")
        m3.metric("🟢 掌握良好", mastered_n)
        m4.metric("🔴 顽固词", hard_n)

        # ── 个性化记忆画像 ────────────────────────────────────────
        st.markdown("#### 🧠 卿姐专属记忆画像")

        last_updated = profile_get(profile_df, "last_updated")
        mem_char = profile_get(profile_df, "记忆特点")
        mem_style = profile_get(profile_df, "助记风格")
        mem_focus = profile_get(profile_df, "强化重点")
        mem_pace = profile_get(profile_df, "节奏建议")

        if mem_char:
            st.caption(f"📅 上次分析：{last_updated}")
            cols_p = st.columns(2)
            with cols_p[0]:
                st.markdown(f"""
                <div style="background:#F0FFF4;border-left:4px solid #48BB78;padding:14px;border-radius:10px;margin-bottom:10px;">
                <b>🔍 记忆特点</b><br>{mem_char}
                </div>
                <div style="background:#EBF8FF;border-left:4px solid #4299E1;padding:14px;border-radius:10px;">
                <b>🎯 最适合的助记风格</b><br>{mem_style}
                </div>
                """, unsafe_allow_html=True)
            with cols_p[1]:
                st.markdown(f"""
                <div style="background:#FFF5F5;border-left:4px solid #FC8181;padding:14px;border-radius:10px;margin-bottom:10px;">
                <b>💪 本周强化重点</b><br>{mem_focus}
                </div>
                <div style="background:#FFFFF0;border-left:4px solid #ECC94B;padding:14px;border-radius:10px;">
                <b>📅 节奏建议</b><br>{mem_pace}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("还没有记忆画像。学习并复习一段时间后，点击下方按钮让 AI 分析卿姐的记忆规律。")

        if st.button(
            "🔬 重新分析记忆规律（更新画像）" if mem_char else "🔬 生成首次记忆画像",
            use_container_width=True,
            key="gen_profile",
        ):
            with st.spinner("AI 正在深度分析卿姐的记忆规律，请稍候…"):
                local_stats = build_local_profile(log_df, srs_df)
                if local_stats["total_learned"] < 5:
                    st.warning("学习词汇数量还不够（需要至少 5 个词），请继续学习后再来分析。")
                else:
                    new_profile = get_ai_profile_analysis(local_stats)
                    if new_profile:
                        try:
                            save_memory_profile(new_profile)
                            st.cache_data.clear()
                            st.success("✅ 记忆画像已更新！以后每个助记词都会根据这份画像定制。")
                            st.rerun()
                        except Exception as e:
                            st.error(f"保存失败：{e}")
                    else:
                        st.error("AI 分析失败，请检查 DeepSeek API Key 是否配置正确。")

        st.divider()

        # AI 诊断
        if st.button("🪄 生成 AI 学习诊断报告", use_container_width=True, key="ai_report"):
            with st.spinner("正在扫描记忆资产…"):
                report = analyze_progress_ai(clean_df)
            st.markdown(
                f'<div style="background:#F0F2F6;padding:20px;border-radius:15px;'
                f'border-left:5px solid #FF69B4;color:#2C3E50;">'
                f'🤖 <b>DeepSeek 诊断：</b><br>{report}</div>',
                unsafe_allow_html=True,
            )

        # 顽固词排行
        if not srs_df.empty and "ease_factor" in srs_df.columns:
            st.divider()
            st.markdown("#### 🔴 顽固词排行（掌握度最低）")
            srs_show = srs_df.copy()
            srs_show["ease_factor"] = pd.to_numeric(srs_show["ease_factor"], errors="coerce")
            srs_show["interval"] = pd.to_numeric(srs_show["interval"], errors="coerce")
            srs_show["repetitions"] = pd.to_numeric(srs_show["repetitions"], errors="coerce")
            hard_table = (
                srs_show.sort_values("ease_factor")
                .head(10)[["word", "ease_factor", "interval", "repetitions"]]
                .rename(columns={
                    "word": "单词",
                    "ease_factor": "掌握度(EF)",
                    "interval": "下次间隔(天)",
                    "repetitions": "累计复习次",
                })
            )
            st.dataframe(hard_table, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### 📋 全部词汇记录")
        for col in ["meaning", "notes", "level"]:
            if col in clean_df.columns:
                clean_df[col] = clean_df[col].apply(
                    lambda x: "" if str(x).strip().lower() in ["nan", "none", "null", "n/a", ""] else x
                )
        display = clean_df.reindex(columns=["date", "word", "meaning", "notes", "level"]).fillna("")
        display.columns = ["学习日期", "单词", "中文释义", "笔记", "难度"]
        st.dataframe(
            display.sort_values("学习日期", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
