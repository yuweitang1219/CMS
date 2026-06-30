# core/chatbot.py

import os
import json
import datetime
import google.generativeai as genai
from pymongo import MongoClient
from .constants import (
    CONDITIONS_LIST, SENSORY_LIST, TUBES_LIST, COGNITION_LIST,
    FALLS_LIST, INCOME_LIST, ADL_LIST, IADL_LIST, LTC_SERVICES
)

# MongoDB 雲端資料庫連線初始化
MONGO_URI = os.environ.get("MONGO_URI")
mongo_client = None
mongo_db = None
mongo_col = None
mongo_rules_col = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI)
        mongo_db = mongo_client.get_database("line_bot_db")
        mongo_col = mongo_db.get_collection("sessions")
        mongo_rules_col = mongo_db.get_collection("rules")
        print("Successfully connected to MongoDB Atlas!")
    except Exception as e:
        print("Failed to initialize MongoDB client:", e)

if os.path.exists("/data") and os.path.isdir("/data"):
    SESSION_DIR = "/data/sessions"
else:
    SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sessions')


def get_default_state():
    import datetime
    today = datetime.date.today().isoformat()
    return {
        "name": "未提供資料",
        "birthYear": "1940",
        "familyName": "未提供資料",
        "familyRel": "未提供資料",
        "visitDate": today,
        "visitTime": "09:00",  # 訪視時間，格式為 HH:MM
        "statusVal": "1",  # 1=一般, 2=中低收, 3=低收
        "livingStr": "與子女同住",
        "burdenStr": "無明顯負荷",
        "hasF": False,
        "cmsLvl": "4",
        "trafLvl": "2",
        "selectedIncome": ["案子提供"],
        "selectedConditions": [],
        "selectedSensory": [],
        "selectedTubes": [],
        "selectedCognition": [],
        "selectedFalls": [],
        "adlData": {},
        "iadlData": {},
        "familyStatusVal": "無",
        "activeServices": [],
        "serviceTimes": {},
        "customPrices": {},
        "planType": "AA01",
        "specialistName": "",   # 照專姓名
        "lastProblemList": "",   # 上次問題清單（複評/AA01 用）
        "gender": "女",                 # 性別，如 "男"、"女"
        "consciousness": "清楚",        # 意識狀態，如 "清楚"、"不清"、"混亂"、"臥床叫喚無反應"
        "interaction": "簡單對話",     # 對談/互動，如 "正常與人應答"、"簡單對談"、"雙向對談"、"無法對談"
        "orientation": "清楚",          # 人事時地物定向感，如 "皆清楚"、"模糊"、"部分混亂"
        "vision": "正常",               # 視力，如 "正常"、"模糊"、"退化"、"左眼幾乎失明"、"可辨別大字"
        "hearing": "正常",              # 聽力，如 "正常"、"雙耳重聽"、"退化"
        "recentFalls": "近半年無",       # 跌倒及住院，如 "近半年無"、"近期無"、"有跌倒過"、"近一年無"
        "emotion": "穩定",              # 情緒，如 "穩定"、"平穩"、"波動"
        "caregiverBirthYear": "ＯＯ",    # 主要照顧者出生年/年次，如 "49年次"、"75年次"
        "caregiverJob": "退休",          # 主要照顧者工作/無業，如 "退休"、"在景碩科技上班"、"無業"
        "caregiverHealth": "無明顯不適", # 主要照顧者健康狀況，如 "健康狀況佳"、"身體狀況尚可"、"同為長照個案"
        "serviceUsageStatus": "服務穩定使用中",  # 個案服務使用情形/需求，如 "服務穩定使用中"、"有長照服務使用"
        "address": ""  # 個案住家地址，字串，例如 "桃園市中壢區中山路100號"
    }


def load_session(user_id):
    if mongo_col is not None:
        try:
            doc = mongo_col.find_one({"user_id": user_id})
            if doc:
                return doc.get("state", get_default_state())
            return get_default_state()
        except Exception as e:
            print(f"Error loading session from MongoDB for {user_id}: {e}")
            # Fallback to local file below

    os.makedirs(SESSION_DIR, exist_ok=True)
    session_path = os.path.join(SESSION_DIR, f"{user_id}.json")
    if os.path.exists(session_path):
        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session for {user_id}: {e}")
            return get_default_state()
    else:
        return get_default_state()

def save_session(user_id, state):
    if mongo_col is not None:
        try:
            mongo_col.update_one(
                {"user_id": user_id},
                {"$set": {"state": state, "updated_at": datetime.datetime.utcnow()}},
                upsert=True
            )
            return
        except Exception as e:
            print(f"Error saving session to MongoDB for {user_id}: {e}")
            # Fallback to local file below

    os.makedirs(SESSION_DIR, exist_ok=True)
    session_path = os.path.join(SESSION_DIR, f"{user_id}.json")
    try:
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving session for {user_id}: {e}")

def clear_session(user_id):
    if mongo_col is not None:
        try:
            mongo_col.delete_one({"user_id": user_id})
            return
        except Exception as e:
            print(f"Error clearing session from MongoDB for {user_id}: {e}")
            # Fallback to local file below

    os.makedirs(SESSION_DIR, exist_ok=True)
    session_path = os.path.join(SESSION_DIR, f"{user_id}.json")
    if os.path.exists(session_path):
        try:
            os.remove(session_path)
        except Exception as e:
            print(f"Error removing session for {user_id}: {e}")

def load_rules(user_id):
    if mongo_rules_col is not None:
        try:
            doc = mongo_rules_col.find_one({"user_id": user_id})
            if doc:
                return doc.get("rules", [])
            return []
        except Exception as e:
            print(f"Error loading rules from MongoDB for {user_id}: {e}")

    os.makedirs(SESSION_DIR, exist_ok=True)
    rules_path = os.path.join(SESSION_DIR, f"rules_{user_id}.json")
    if os.path.exists(rules_path):
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading rules for {user_id}: {e}")
            return []
    return []

def save_rules(user_id, rules_list):
    if mongo_rules_col is not None:
        try:
            mongo_rules_col.update_one(
                {"user_id": user_id},
                {"$set": {"rules": rules_list, "updated_at": datetime.datetime.utcnow()}},
                upsert=True
            )
            return
        except Exception as e:
            print(f"Error saving rules to MongoDB for {user_id}: {e}")

    os.makedirs(SESSION_DIR, exist_ok=True)
    rules_path = os.path.join(SESSION_DIR, f"rules_{user_id}.json")
    try:
        with open(rules_path, 'w', encoding='utf-8') as f:
            json.dump(rules_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving rules for {user_id}: {e}")

def clear_rules(user_id):
    if mongo_rules_col is not None:
        try:
            mongo_rules_col.delete_one({"user_id": user_id})
            return
        except Exception as e:
            print(f"Error clearing rules from MongoDB for {user_id}: {e}")

    os.makedirs(SESSION_DIR, exist_ok=True)
    rules_path = os.path.join(SESSION_DIR, f"rules_{user_id}.json")
    if os.path.exists(rules_path):
        try:
            os.remove(rules_path)
        except Exception as e:
            print(f"Error removing rules for {user_id}: {e}")

def process_chat(user_id, user_message, api_key):
    """
    Load the session state, send it alongside the new user message to Gemini,
    update the state, save it, and return the AI text reply.
    """
    state = load_session(user_id)
    history = state.pop("_history", [])
    
    # Load learned rules
    rules = load_rules(user_id)
    if rules:
        rules_str = "\n".join([f"- {r}" for r in rules])
    else:
        rules_str = "（目前暫無自訂規則）"
    
    # Append the new user message to history
    history.append({"role": "user", "content": user_message})
    
    # Format history as a readable string block
    history_str = ""
    for msg in history[:-1]:  # exclude the latest user message
        role_name = "個管師" if msg["role"] == "user" else "AI 助理"
        history_str += f"{role_name}: {msg['content']}\n"
        
    # Configure Gemini
    genai.configure(api_key=api_key)

    # Calculate current date in both formats
    import datetime
    today_iso = datetime.date.today().isoformat()
    roc_parts = today_iso.split('-')
    today_roc = f"{int(roc_parts[0])-1911}年{roc_parts[1]}月{roc_parts[2]}日"

    # If first message in a new session, auto-set visitDate to today
    is_first_message = len(history) == 1  # only the current message, no prior history
    if is_first_message:
        state['visitDate'] = today_iso

    # Setup prompt with guidelines and constants
    prompt = f"""
你是一位專業的長照個案管理師(個管師)的 AI 助理。你的任務是與個管師協作，透過對話逐步收集個案資訊，更新下方的狀態 JSON。

【今日日期】: {today_iso}（民國 {today_roc}）

【你已學習的使用者自訂規則與偏好（重要，請務必嚴格遵循這些自訂偏好與規則來處理個案狀態與對話）】:
{rules_str}

【重要角色與口吻設定】:
1. 對話對象是「個管師」而非個案家屬，請以「專業同事/助手」的口吻溝通。
2. 保持對話「簡短、專業、精確」，不要有冗長客套。
3. **主動引導問答（重要）**：每次回覆時，簡短確認剛才更新的資訊後，請**主動挑選 1-2 個最需要補齊的關鍵欄位直接向個管師發問**。這能引導個管師順著你的問題回答，使對話體驗更流暢。
   - 範例：「已記錄姓名陳阿公與高血壓。請問他的訪視日期是哪一天？身分別是一般戶嗎？」
   - 範例：「已更新身分為低收、CMS 5。為了評估照顧需求，請問阿公在沐浴、進食等日常起居（ADL）需要人協助嗎？」
4. 每次發問控制在 1-2 個欄位，不要一次問太多，保持專注與節奏。
5. **日期處理規則**：
   - 家訪日期 (visitDate) 已**自動預設為今天（{today_roc}）**。若個管師沒有特別說明日期，請保留此預設值。
   - 若個管師說「今天」、「就今天」，visitDate 維持 {today_iso} 不變。
   - 若個管師說具體日期（如「6月10號」），請轉換為 {roc_parts[0]}-06-10 格式更新。
   - 對話剛開始時，請**主動告知**個管師：「家訪日期已預設為今天（{today_roc}），如需更改請告知。」
6. **自訂規則與偏好套用**：
   - 務必將「你已學習的使用者自訂規則與偏好」列出的所有規則（如照專姓名、特定服務項目的預設核定次數等）作為最高優先級。
   - 當個案狀態中對應的欄位為空或為預設值，且自訂規則中有提及時，你必須**主動且自動將規則中的值套用到當前個案狀態 JSON 中**（例如：若自訂規則包含「照專為王美美」，且 JSON 中的 `specialistName` 為空或為預設值，你必須將其更新為 `"王美美"`；若自訂規則包含「BA02核定15次」，且個案要申請或已配置 BA02，你必須自動將 `serviceTimes` 中的 `BA02` 設為 `15`）。

【重要名詞與縮寫定義（攸關屬性分類正確性，務必嚴格遵守）】:
1. 「案主」或「個案」：指受服務的長照對象本人。
2. 「案子」：代表「個案的兒子」，絕非指個案本人或某個案件！
   - 例如：「經濟來源由兒子提供」➔ 應分類為 selectedIncome 中的 "案子提供"。
3. 「案女」：代表「個案的女兒」。
4. 「案妻」/「案夫」：指個案的配偶。
5. 「案家」：指個案的家屬或家庭。


【歷史對話紀錄】:
{history_str or "（對話剛剛開始，無歷史對話）"}

【當前個案狀態 JSON】:
{json.dumps(state, ensure_ascii=False, indent=2)}

【台灣長照口語與生活情境對照指引（重要，使你更聰明地解讀個管師的口語輸入）】:
1. ADL 自理能力對照：
   - 「洗澡要人牽」、「走路要人扶」、「穿衣要人拉一把」、「上廁所要人牽」 ➔ 判定為「部分協助」或「需協助」。
   - 「洗澡無法自己做」、「吃飯要人餵」、「完全走不動」、「整天躺床」、「大小便都在床上」 ➔ 判定為「完全協助」或「完全依賴」。
   - 「吃飯可以自己吃」、「穿衣可以自己穿」、「行走正常」 ➔ 判定為「獨立」。
2. 跌倒與住院史對照：
   - 「腳無力常軟腳」、「上星期才剛防摔倒」、「最近剛出院」 ➔ 判定為「近半年有跌倒及住院紀錄」。
3. 疾病史對照：
   - 「記性很差丟三落四」、「會迷路認不得人」、「失智」 ➔ 疾病史 (selectedConditions) 應加入「失智症」。
   - 「血糖很高」、「糖分高」 ➔ 疾病史應加入「糖尿病」。
   - 「血壓飆高」、「血壓不穩」 ➔ 疾病史應加入「高血壓」。
   - 「關節磨損不舒服」、「骨關節炎」 ➔ 疾病史應加入「骨關節炎」。
4. 社會支持與家庭照顧對照：
   - 「大兒子照顧，但他工作很累/有壓力」 ➔ 照顧負荷 (burdenStr) 應判定為「需輪班工作/無替手」或「照顧者有壓力」。

【欄位可選值與規範】:
1. 姓名 (name): 字串
2. 出生年 (birthYear): 西元年份字串 (如 "1948")
3. 家屬姓名 (familyName): 字串
4. 關係 (familyRel): 字串
5. 家訪日期 (visitDate): 格式為 YYYY-MM-DD
6. 身分別 (statusVal):
   - "1": 第三級 (一般戶)
   - "2": 第二級 (中低收)
   - "3": 第一級 (低收)
7. 居住型態 (livingStr): 必須為以下之一: {json.dumps(LIVING_OPTIONS := ["獨居", "與配偶同住", "與子女同住", "與其他家屬同住", "老老照顧"])}
8. 主要照顧者負荷 (burdenStr): 必須為以下之一: {json.dumps(BURDEN_OPTIONS := ["無明顯負荷", "需輪班工作/無替手", "自身有慢性病/年邁", "照顧技巧不足", "經濟困難", "其他"])}
9. 聘僱外籍看護 (hasF): 布林值 (True 或 False)
10. CMS 等級 (cmsLvl): "2" 到 "8" 的字串
11. 交通地區分類 (trafLvl): "1" 到 "4" 的字串
12. 經濟收入與來源 (selectedIncome): 必須為以下清單的子集（可複選）: {json.dumps(INCOME_LIST)}
13. 疾病史 (selectedConditions): 必須為以下清單的子集: {json.dumps(CONDITIONS_LIST)}
14. 感官異常評估 (selectedSensory): 必須為以下清單的子集: {json.dumps(SENSORY_LIST)}
15. 留置管路與特殊照護 (selectedTubes): 必須為以下清單的子集: {json.dumps(TUBES_LIST)}
16. 認知與行為狀態 (selectedCognition): 必須為以下清單的子集: {json.dumps(COGNITION_LIST)}
17. 跌倒紀錄 (selectedFalls): 必須為以下清單的子集: {json.dumps(FALLS_LIST)}
18. ADL 需協助項目 (adlData):
    - 鍵必須在: {json.dumps(ADL_LIST)} 中。
    - 值為: "獨立", "部分協助", "完全依賴" (若不需協助則為空或不列出)。
    - **備註與細節保留規則 (重要)**：如果個管師輸入時在選項後方帶有括號 `()（）` 以補充額外的生活細節（例如：`洗澡部分協助（大兒子扶）`、`吃飯部分協助（手抖用輔助筷）`），你必須完整保留個管師輸入的整段文字（含括號及備註內容）作為該項目的值，不可裁切為單純的選項。
19. IADL 需協助項目 (iadlData):
    - 鍵必須在: {json.dumps(IADL_LIST)} 中。
    - 值為: "獨立", "部分協助", "完全依賴" (若不需協助則為空或不列出)。
    - **備註與細節保留規則 (重要)**：同 ADL，如果個管師輸入時有括號備註，必須完整保留整段文字（包含括號內容）作為值，不可裁剪。
20. 其他家庭成員 (familyStatusVal): 字串，指除了主要照顧者之外的其他家庭成員（如「無」、「長女」或「次子」等）。請僅列出成員名稱或關係，絕對不可以填寫經濟支持、照顧細節或其他描述性內容。
21. 計畫類型 (planType): 必須為以下之一:
    - "AA01": 當個管師說「AA01」、「家訪」、「定期追蹤」時使用
    - "ReEval": 當個管師說「複評」、「重新評定」時使用
    - "NewCase": 當個管師說「新案」、「新個案」時使用
    - "CoVisit": 當個管師說「共訪」、「一起訪視」時使用
    - "PreNewCase": 當個管師說「出準新案」時使用
    - "PlanChange": 當個管師說「計畫異動」時使用
    - "Private": 當個管師輸入的事情是私人行程、會議、休假、非長照案主訪視等個人活動（例如「去衛生局」、「開會」、「私事」、「下午13:30去衛生局」）時使用。
    若個管師說明計畫類型或輸入個人行程，請務必更新此欄位。
22. 照專姓名 (specialistName): 字串，「照專」或「照顧專員」的姓名，新案/複評/共訪才需要，AA01 可留空。若個管師提供，請記錄。
23. 上次問題清單 (lastProblemList): 字串，用於複評/AA01 格式中的「上次問題清單」，請以「1-洗澡問題、2-走路問題」的格式記錄。
24. 服務項目規劃 (activeServices) 與 數量/月 (serviceTimes):
    - 系統支援服務代碼如: {", ".join([s['code'] for s in LTC_SERVICES[:30]])}... 等。
    - 當使用者提及某種照護需求（如：洗澡、備餐、喘息、就醫交通）時，將對應的服務代碼加入 `activeServices`，並在 `serviceTimes` 設定對應的每月次數（例如：洗澡 BA07 預設 12 次/月，備餐 BA05 預設 20 次/月，除非使用者指定其他次數）。
    - 聘僱外籍看護 (hasF) 為 True 時，BA 碼服務（除了 BA09, BA09a 到宅沐浴車外）應被自動移除（不予核定），且喘息服務 (G碼) 與短照服務 (SC09) 只能在空窗期使用。
25. 性別 (gender): 字串，如 "男"、"女"。
26. 意識狀態 (consciousness): 字串，如 "清楚"、"不清"、"混亂"、"臥床叫喚無反應"。
27. 對談互動 (interaction): 字串，例如 "簡單對話"、"正常與人應答"、"雙向對談"、"無法說出完整詞句"、"叫喚無反應"、"簡單對談"。
28. 人事時地物定向感 (orientation): 字串，例如 "清楚"、"皆清楚"、"模糊"、"無法辨識"、"尚可辨識"。
29. 視力 (vision): 字串，例如 "正常"、"模糊"、"退化"、"左眼幾乎失明"、"可辨別大字"。
30. 聽力 (hearing): 字串，例如 "正常"、"雙耳重聽"、"退化"、"無法判斷"。
31. 近期跌倒住院紀錄 (recentFalls): 字串，例如 "近半年無"、"近期無"、"近一年無"、"有跌倒過"、"無近期"。
32. 情緒 (emotion): 字串，例如 "穩定"、"平穩"、"尚屬穩定"、"波動"、"焦慮"、"憂鬱"。
33. 主要照顧者出生年 (caregiverBirthYear): 字串，例如 "49年次"、"75年次"、"26年次" 等。
34. 主要照顧者工作狀態 (caregiverJob): 字串，例如 "退休"、"在景碩科技上班"、"兼職教育工作"、"無業"。
35. 主要照顧者健康狀況 (caregiverHealth): 字串，例如 "無明顯不適"、"健康狀況佳"、"同為長照個案"、"同為小兒麻痺患者"。
36. 服務使用評值 (serviceUsageStatus): 字串，例如 "服務穩定使用中"、"有長照服務使用需求"、"有復能與輔具使用需求" 等。
37. 訪視時間 (visitTime): 格式為 HH:MM (24小時制，如 "13:30"、"10:00")。若個管師提及具體時間（如「下午一點半」、「13:30」、「下午 13:30」），請轉換為 24 小時制格式更新此欄位。預設為 "09:00"。
38. 個案地址 (address): 字串，個案家中的住家地址（如「桃園市中壢區中山路100號」、「桃園市八德區介壽路一段xx號」）。當個管師在對話中提及個案居住地址或地點時，請精確提取並更新此欄位。

【長照 2.0 額度與標準定義表（重要，若個管師詢問額度或諮詢，務必以此為唯一標準回答）】:
1. B/C 照顧及專業服務額度（每月，一般戶自付額 16%、中低收 5%、低收 0%；聘僱外籍看護或入住機構者，額度折減為 30%）：
   - CMS 第 2 級: 10,020 元
   - CMS 第 3 級: 15,460 元
   - CMS 第 4 級: 18,580 元
   - CMS 第 5 級: 24,100 元
   - CMS 第 6 級: 28,070 元
   - CMS 第 7 級: 32,090 元
   - CMS 第 8 級: 36,180 元
2. G 喘息服務額度（年度）：
   - CMS 第 2 級 ～ 第 6 級: 32,340 元
   - CMS 第 7 級 ～ 第 8 級: 48,510 元
3. D 交通接送額度（每月）：
   - 第 1 類 (一般地區): 1,680 元
   - 第 2 類: 1,840 元
   - 第 3 類: 2,000 元
   - 第 4 類 (偏鄉): 2,400 元
4. EF 輔具及居家無障礙額度（每三年）：
   - 總額度: 40,000 元


【個管師輸入訊息】:
"{user_message}"

【你的任務】:
1. 分析個管師的最新訊息，提取出個案資訊（例如姓名、CMS、疾病史、ADL評估、需要的服務代碼等）。
2. 更新並融合這些資訊到當前的個案狀態 JSON 中（保持現有其他欄位不變，僅更新提及的欄位）。
3. 產生簡短、主動提問的對話回覆，引導個管師填寫下一個欄位。
4. **絕對禁止**的行為：
   - ❌ 不可以問「請確認以下資料是否正確」
   - ❌ 不可以列出所有已收集的資料請個管師確認
   - ❌ 不可以問「資料是否完整」或「是否可以生成計畫書了」
   - ✅ 只要直接告知：「資料已更新，如已就緒請輸入「完成」即可產出計畫書。」
5. 當個管師說「完成」、「出計畫書」、「好了」等詞時，這些指令**不會進到這裡**（已由系統攔截處理），請忽略這類訊息。
6. **學習自訂規則與偏好（重要）**：
   - 當個管師在訊息中明確要求你「學習」、「記住」、「以後預設」、「設定常規」或指正你的行為時（例如：「記住，陳照專的名字是陳美麗」、「以後新案的ADL請預設為獨立」），請從中提取出這條明確的自訂規則，並在回傳的 JSON 中包含一個額外的鍵 `"new_rule": "規則的簡短描述"`。
   - 回覆文字（reply_text）應簡短確認已學習此規則。
   - 如果個管師沒有明確要你學習或記憶規則，請**絕對不要**在回傳的 JSON 中包含 "new_rule" 鍵。
7. **私人行程與個人活動處理規則 (重要)**：
   - 當判斷計畫類型 (planType) 為 "Private" 時，代表這是一個個人活動或非公事家訪行程（例如「去衛生局」、「開會」、「下午請假」等），請將該行程的具體內容直接填入 姓名 (name) 欄位中（例如將 name 設為 "去衛生局"）。
   - 在產生回覆文字 (reply_text) 時，**絕對不要問任何與個案相關的問題**（例如：不要問姓名、身分別、CMS等級、ADL等），也不要詢問這是什麼計畫類型。
   - 只要簡短親切地回覆：「已記錄此行程。如果需要同步到 Google 行事曆，請輸入「建立行事曆」或「同步行事曆」！」或類似的確認即可，並提示如果需要記錄下一個個案，可隨時輸入「重新開始」。
8. **新個案/新行程偵測與重設規則 (重要)**：
   - 當個管師提及一個與目前狀態姓名 (name) 不同的**全新個案姓名**，或是明確表示要安排**另一場新的訪視/私人行程**時（例如：原先已記錄「王小明」，現在突然說「15:00家訪李小華」），你必須判定這是一個新案/新行程。
   - 在此情況下，你必須將回傳的 `updated_state` JSON **重設為預設狀態（清除上一位個案的殘留評估資料）**，特別是必須**清除 `googleEventId`（將其設為 `""`、`null` 或從 JSON 鍵中移除）**，以利後續您輸入「建立行事曆」時為此新預約在日曆上建立**全新**行程（而非修改/覆蓋上一個預約）。新個案的姓名填入 `name`，新時間/日期填入 `visitTime` / `visitDate`，其他評估欄位（如疾病、CMS、ADL、配置服務等）重設為初始/預設值。
   - 回覆文字（reply_text）應簡短確認已為新個案開啟記錄，並主動詢問其基本資訊。
9. **輸出格式規範**：你必須回傳一個合法的 JSON 物件，不能包含額外的 markdown 程式碼區塊（如 ```json ... ```），只能是純 JSON 字串。

JSON 必須包含以下兩個鍵：
- "updated_state": 更新後的完整個案狀態 JSON 物件。
- "reply_text": 你要發送給個管師的繁體中文對話文字（簡短、專業，最多 200 字）。
- "new_rule" (選填): 只有在個管師發出學習指示時才需要此鍵，值為提取出的規則字串。

請開始執行。
"""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Strip code block wrappers if any
        if text.startswith("```"):
            # find first newline
            first_nl = text.find("\n")
            # find last backticks
            last_bt = text.rfind("```")
            if first_nl != -1 and last_bt != -1:
                text = text[first_nl:last_bt].strip()
        
        data = json.loads(text)
        updated_state = data.get("updated_state", state)
        reply_text = data.get("reply_text", "抱歉，系統處理出現了一些問題。請問您是否可以再描述一次個案的狀況？")
        
        # Check and save new rule if extracted
        new_rule = data.get("new_rule")
        if new_rule:
            current_rules = load_rules(user_id)
            if new_rule not in current_rules:
                current_rules.append(new_rule)
                save_rules(user_id, current_rules)
        


        # Check if we should sync to Google Calendar in real-time ONLY IF the event was already created
        old_date = state.get("visitDate")
        new_date = updated_state.get("visitDate")
        old_name = state.get("name")
        new_name = updated_state.get("name")
        has_event = bool(state.get("googleEventId"))
        
        should_sync = False
        if has_event and new_date:
            if new_date != old_date:
                should_sync = True
            elif updated_state.get("visitTime") != state.get("visitTime"):
                should_sync = True
            elif updated_state.get("planType") != state.get("planType"):
                should_sync = True
                
        import database
        import os
        has_oauth = bool(database.get_setting("google_refresh_token"))
        has_service_account = bool(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"))
        if should_sync and (has_oauth or has_service_account):
            try:
                from .calendar_helper import sync_to_calendar
                sync_res = sync_to_calendar(updated_state)
                if sync_res.get("success"):
                    updated_state["googleEventId"] = sync_res.get("event_id")
                    reply_text += "\n\n📅 已為您自動同步更新 Google 行事曆行程！"
            except Exception as se:
                print("Error syncing to calendar during process_chat:", se)

        # Save updated history in state
        history.append({"role": "assistant", "content": reply_text})
        updated_state["_history"] = history
        
        # Save updated state
        save_session(user_id, updated_state)
        return reply_text
    except Exception as e:
        print("Error in process_chat with Gemini:", e)
        # Restore history in state and save
        state["_history"] = history
        save_session(user_id, state)
        return "系統處理對話時發生錯誤，請再試一次。或是您可以輸入「重新開始」以清除目前的紀錄。"
