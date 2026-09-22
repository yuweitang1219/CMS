import re
import json
import os

def parse_user_input(text):
    """
    Parse the raw LINE message into the state dictionary expected by the engine.
    If OPENAI_API_KEY is available, use GPT-4 to parse. Otherwise, use a simple regex fallback.
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if gemini_key:
        return _parse_with_gemini(gemini_key, text)
    elif openai_key:
        return _parse_with_openai(openai_key, text)
    else:
        return _parse_with_regex(text)

def _parse_with_gemini(api_key, text):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    prompt = f"""
    You are an expert care case parser. Given the user's natural language input, you must extract the variables to form this JSON state. 
    Infer the necessary services implicitly if mentioned (e.g. 洗澡 means BA07). Use the following mappings:
    - BA07: 洗澡
    - BA04: 進食/管灌
    - BA05: 備餐
    - BA16: 買東西
    - BA15: 家務
    - BA14: 就醫
    - BA13: 外出
    - BA12: 上下樓
    - BA11: 關節活動
    - DA01: 交通
    
    DO NOT infer service codes implicitly from physical conditions, symptoms, or ADL notes (e.g., needing help with bathing or incontinence in ADL notes DOES NOT mean activeServices gets BA07 or BA24). 
    Extract activeServices ONLY from explicit service requests or care plan section 3 (照護計畫/照顧服務需求) where the user/family explicitly requests or agrees to use the service code.

    Return ONLY raw JSON formatting, no explanation. Do not include markdown code blocks.

    Schema:
    {{
      "name": "string",
      "birthYear": "string (eg. 1940)",
      "familyName": "string",
      "familyRel": "string",
      "visitDate": "YYYY-MM-DD",
      "statusVal": "1 or 2 or 3",
      "livingStr": "與子女同住 or 獨居 etc",
      "burdenStr": "無明顯負荷",
      "hasF": boolean (外勞=True),
      "cmsLvl": "number as string",
      "trafLvl": "2",
      "selectedIncome": ["案子提供"],
      "selectedConditions": ["高血壓" etc],
      "activeServices": ["BA07", "BA05"],
      "serviceTimes": {{"BA07": 12, "BA05": 20}}
    }}
    
    User Input:
    {text}
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        data = response.text
        data = data.replace('```json', '').replace('```', '').strip()
        state = json.loads(data)
        return state
    except Exception as e:
        print("Gemini parsing error:", e)
        return _parse_with_regex(text)

def _parse_with_openai(api_key, text):
    import openai
    client = openai.OpenAI(api_key=api_key)
    
    prompt = f"""
    You are an expert care case parser. Given the user's natural language input, you must extract the variables to form this JSON state. 
    DO NOT infer service codes implicitly from physical conditions, symptoms, or ADL notes (e.g., needing help with bathing or incontinence in ADL notes DOES NOT mean activeServices gets BA07 or BA24). 
    Extract activeServices ONLY from explicit service requests or care plan section 3 (照護計畫/照顧服務需求) where the user/family explicitly requests or agrees to use the service code.

    Return ONLY raw JSON formatting, no explanation.

    Schema:
    {{
      "name": "string",
      "birthYear": "string (eg. 1940)",
      "familyName": "string",
      "familyRel": "string",
      "visitDate": "YYYY-MM-DD",
      "statusVal": "1 or 2 or 3",
      "livingStr": "與子女同住 or 獨居 etc",
      "burdenStr": "無明顯負荷",
      "hasF": boolean (外勞=True),
      "cmsLvl": "number as string",
      "trafLvl": "2",
      "selectedIncome": ["案子提供"],
      "selectedConditions": ["高血壓" etc],
      "activeServices": ["BA07", "BA05"],
      "serviceTimes": {{"BA07": 12, "BA05": 20}}
    }}
    
    User Input:
    {text}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        data = response.choices[0].message.content
        data = data.replace('```json', '').replace('```', '').strip()
        state = json.loads(data)
        return state
    except Exception as e:
        print("OpenAI parsing error:", e)
        return _parse_with_regex(text)


def _parse_with_regex(text):
    """
    Fallback dummy parser that uses minimal regex to find info.
    Format expected: 姓名:王大明, 年齡:80, CMS:4, 服務: 洗澡, 備餐
    """
    state = {
      "name": "未提供資料",
      "birthYear": "1940",
      "cmsLvl": "4",
      "activeServices": [],
      "serviceTimes": {}
    }
    
    name_m = re.search(r'(姓名|名字)[:：\s]+([^\s,，]+)', text)
    if name_m: state['name'] = name_m.group(2)
        
    age_m = re.search(r'(年紀|年齡|幾歲)[:：\s]+(\d+)', text)
    if age_m: 
        state['birthYear'] = str(2026 - int(age_m.group(2)))
        
    cms_m = re.search(r'CMS[:：\s]*(\d)', text, flags=re.IGNORECASE)
    if cms_m: state['cmsLvl'] = str(cms_m.group(1))

    # Basic keyword mapping
    mappings = {
        '洗澡': 'BA07', '洗頭': 'BA23', '備餐': 'BA05', '管灌': 'BA04', 
        '餵食': 'BA04', '就醫': 'BA14', '外出': 'BA13', '買': 'BA16', 
        '打掃': 'BA15', '家務': 'BA15', '交通': 'DA01'
    }
    for kw, code in mappings.items():
        if kw in text:
            state['activeServices'].append(code)
            state['serviceTimes'][code] = 12 if code == 'BA07' else 4
            
    return state


def parse_calendar_event_input(text, client_now_str=None):
    """
    Parse natural language text into structured calendar event objects.
    Uses Fast-Path pattern matching first: if both explicit date and explicit time
    are cleanly identified with high confidence, returns immediately without Gemini API call (0 Token cost).
    Otherwise, falls through to Gemini AI for deep natural language understanding.
    """
    import database
    from datetime import datetime
    
    if client_now_str:
        try:
            now = datetime.fromisoformat(client_now_str.replace("Z", ""))
        except Exception:
            now = datetime.now()
    else:
        now = datetime.now()
        
    # 1. Fast-Path Pre-Check (正則快軌)
    regex_res = _parse_calendar_with_regex(text, now)
    if isinstance(regex_res, dict) and not regex_res.get("needs_confirmation", True):
        # High confidence match with explicit date & time: bypass Gemini API call
        result = regex_res
    else:
        gemini_key = database.get_setting("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                result = _parse_calendar_with_gemini(gemini_key, text, now)
            except Exception as e:
                print(f"Gemini calendar parsing error: {e}, using regex fallback")
                result = regex_res
        else:
            result = regex_res

    # Normalize result format: guarantee both 'events' list and top-level single event fields
    if isinstance(result, list):
        events_list = result
    elif isinstance(result, dict) and "events" in result:
        events_list = result["events"]
    elif isinstance(result, dict):
        events_list = [result]
    else:
        events_list = []

    # Enforce strict length limits on summary (max 30 chars) and move excess to description
    for ev in events_list:
        summary = (ev.get("summary") or "行程").strip()
        desc = (ev.get("description") or "").strip()
        
        if len(summary) > 30 or "\n" in summary:
            first_line = summary.split("\n")[0].strip()
            clean_summary = first_line[:30].strip() or "行程"
            if summary != clean_summary:
                desc = f"{summary}\n\n{desc}".strip() if desc else summary
            ev["summary"] = clean_summary
            ev["description"] = desc

    if not events_list:
        events_list = [{
            "summary": "行程",
            "start_time": now.strftime("%Y-%m-%dT09:00:00"),
            "end_time": now.strftime("%Y-%m-%dT10:00:00"),
            "description": "",
            "location": "",
            "plan_type": "AA01"
        }]

    first_ev = events_list[0]
    needs_conf = result.get("needs_confirmation", False) if isinstance(result, dict) else False
    conf_reason = result.get("confirmation_reason", "") if isinstance(result, dict) else ""

    return {
        "needs_confirmation": needs_conf,
        "confirmation_reason": conf_reason,
        "events": events_list,
        "summary": first_ev.get("summary", "行程"),
        "start_time": first_ev.get("start_time"),
        "end_time": first_ev.get("end_time"),
        "description": first_ev.get("description", ""),
        "location": first_ev.get("location", ""),
        "plan_type": first_ev.get("plan_type", "AA01")
    }

def _parse_calendar_with_gemini(api_key_str, text, now):
    from datetime import timedelta
    from core.gemini_helper import generate_content_with_rotation
    
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday_str = weekday_names[now.weekday()]
    
    prompt = f"""
你是一個專門解析台灣中文行事曆/行程的 AI 助手。
請分析使用者的自然語言輸入，依據基準時間與規則，抽取出行程，並將其自動「分開拆解」為一或多筆獨立行程記錄。

【基準時間參考資訊】：
- 現在日期時間：{now.strftime("%Y-%m-%d %H:%M:%S")} ({weekday_str})
- 今年年份：{now.year}
- 今天日期：{now.strftime("%Y-%m-%d")}
- 明天日期：{(now + timedelta(days=1)).strftime("%Y-%m-%d")}
- 後天日期：{(now + timedelta(days=2)).strftime("%Y-%m-%d")}
- 大後天日期：{(now + timedelta(days=3)).strftime("%Y-%m-%d")}

【日期與時間拆解規則（極度重要）】：
1. **多天/連續日期拆分**：
   - 當使用者提到多天日期範圍（例如：「8/20到8/22 每天下午2點開會」、「8/20、8/21、8/22 下午2點家訪」），你必須**為每一天分別建立一筆獨立的行程**！
   - 例如：「8/20至8/22 每天下午2點到4點開會」➔ 產生 3 筆獨立行程：
     * 8/20 14:00~16:00 開會
     * 8/21 14:00~16:00 開會
     * 8/22 14:00~16:00 開會
2. **多筆不同行程拆分**：
   - 當使用者在同一句輸入中提及多個不同的時間或事件（例如：「8/20 下午2點 訪視張阿公，8/21 上午10點 督導會議」），你必須將其拆分為 2 筆獨立行程！
3. **模糊與不確定性確認機制 (極重要)**：
   - 若使用者輸入的內容缺乏明確日期（如僅說「開會」）、缺乏明確時間（如僅說「下週家訪」）、時間模糊（如「改天」）或行程名稱不明確，請將 `"needs_confirmation"` 設為 `true`，並填寫 `"confirmation_reason"` 說明不清楚之處。
   - 若日期時間名稱皆清晰明確，`"needs_confirmation"` 設為 `false`，`"confirmation_reason"` 為空字串 `""`。
4. 相對日期解析：
   - 「今天」-> {now.strftime("%Y-%m-%d")}
   - 「明天」-> {(now + timedelta(days=1)).strftime("%Y-%m-%d")}
   - 「後天」-> {(now + timedelta(days=2)).strftime("%Y-%m-%d")}
   - 「大後天」-> {(now + timedelta(days=3)).strftime("%Y-%m-%d")}
   - 「週X / 星期X / 下週X」請計算出正確的對應西元日期 (YYYY-MM-DD)。
   - 若僅輸入「8/20」或「8月20日」，請優先將年份補齊為今年 {now.year} 年。
5. 時間解析：
   - 區分上午/下午/晚上/中午 (例如「下午2點」= 14:00，「上午9:30」= 09:30，「晚上7點」= 19:00)。
   - 「2點到4點」/「14:00~16:00」/「下午2點至4點」 -> 開始 14:00，結束 16:00。
   - 若未指定結束時間（例如：「8/20 下午2點 個案訪視」），預設結束時間為開始時間往後推算 1 小時（14:00 到 15:00）。
6. 標題 (summary) 與備註 (description) 規範（極度重要）：
   - 行程標題 `summary` 必須保持極簡短（控制在 15 字以內，例如「張阿公家訪」、「督導會議」、「齒科診診」），請去除時間、日期與指令贅字（如「幫我排」、「新增」、「行事曆」）。
   - 絕不可以將使用者輸入的長篇敘述、數百字文章、詳細個案資料或完整備註直接當作 `summary`！
   - 所有長篇文字、詳細說明、聯絡電話、地址等請一律放入 `description` 欄位。

請嚴格僅回傳 JSON 格式（不要包含 markdown ```json 標籤或任何解說文字）：
{{
  "needs_confirmation": false,
  "confirmation_reason": "",
  "events": [
    {{
      "summary": "行程標題",
      "start_time": "YYYY-MM-DDTHH:MM:00",
      "end_time": "YYYY-MM-DDTHH:MM:00",
      "description": "備註說明 (若無則為空字串)",
      "location": "地點 (若無則為空字串)"
    }}
  ]
}}

使用者輸入內容：
{text}
"""
    models_to_try = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-1.5-flash", "gemini-2.0-flash"]
    last_err = None
    for model_name in models_to_try:
        try:
            response = generate_content_with_rotation(api_key_str, model_name, prompt)
            data_str = response.text.replace('```json', '').replace('```', '').strip()
            parsed = json.loads(data_str)
            if isinstance(parsed, list):
                return {"events": parsed}
            elif isinstance(parsed, dict) and "events" in parsed:
                return parsed
            elif isinstance(parsed, dict):
                return {"events": [parsed]}
        except Exception as e:
            last_err = e
    raise last_err

def _parse_calendar_with_regex(text, now):
    import re
    from datetime import datetime, timedelta

    # Plan type classification (家訪四分法: 複評, AA01, 出準, 新案, plus Private)
    plan_type = "AA01"
    if "複評" in text or "ReEval" in text:
        plan_type = "ReEval"
    elif "出準" in text or "出院準備" in text or "ChuZhun" in text:
        plan_type = "ChuZhun"
    elif "新案" in text or "NewCase" in text:
        plan_type = "NewCase"
    elif "AA01" in text:
        plan_type = "AA01"
    elif any(kw in text for kw in ["開會", "值班", "請假", "休假", "私人", "衛生局", "督導"]):
        plan_type = "Private"

    # Check date range like 8/20~8/22 or 8/20到8/22
    m_multi_date = re.search(r'(\d{1,2})[月/.\-](\d{1,2})[日號]?\s*(?:[~\-到至~]+)\s*(\d{1,2})[月/.\-](\d{1,2})[日號]?', text)
    m_single_dates = re.findall(r'(\d{1,2})[月/.\-](\d{1,2})[日號]?', text)
    
    target_dates = []
    if m_multi_date:
        m1, d1, m2, d2 = map(int, m_multi_date.groups())
        y = now.year
        try:
            dt1 = datetime(y, m1, d1).date()
            dt2 = datetime(y, m2, d2).date()
            curr = dt1
            while curr <= dt2 and len(target_dates) < 31:
                target_dates.append(curr)
                curr += timedelta(days=1)
        except ValueError:
            pass
    elif m_single_dates:
        y = now.year
        for sm, sd in m_single_dates:
            try:
                dt = datetime(y, int(sm), int(sd)).date()
                if dt not in target_dates:
                    target_dates.append(dt)
            except ValueError:
                pass

    if not target_dates:
        if "大後天" in text:
            target_dates.append(now.date() + timedelta(days=3))
        elif "後天" in text:
            target_dates.append(now.date() + timedelta(days=2))
        elif "明天" in text:
            target_dates.append(now.date() + timedelta(days=1))
        elif "今天" in text:
            target_dates.append(now.date())

    # Check time range or single time after stripping date string
    text_time_search = text
    if m_multi_date:
        text_time_search = text_time_search.replace(m_multi_date.group(0), '')
    for sm, sd in m_single_dates:
        text_time_search = re.sub(r'\b' + str(sm) + r'[月/.\-]' + str(sd) + r'[日號]?\b', '', text_time_search)

    start_hour, start_min = 9, 0
    end_hour, end_min = 10, 0
    
    m_range = re.search(r'(上午|早上|下午|晚上|中午)?\s*(\d{1,2})(?::(\d{2}))?\s*(?:點|時)?\s*(半)?\s*(?:[~\-到至~]+)\s*(上午|早上|下午|晚上|中午)?\s*(\d{1,2})(?::(\d{2}))?\s*(?:點|時)?\s*(半)?', text_time_search)
    if m_range and (":" in m_range.group(0) or "點" in m_range.group(0) or "時" in m_range.group(0) or m_range.group(1) or m_range.group(5)):
        p1, h1, min1, half1, p2, h2, min2, half2 = m_range.groups()
        h1, h2 = int(h1), int(h2)
        m1 = 30 if half1 else (int(min1) if min1 else 0)
        m2 = 30 if half2 else (int(min2) if min2 else 0)
        
        if (p1 and ("下午" in p1 or "晚上" in p1)) or ("下午" in text and h1 < 12):
            if h1 < 12: h1 += 12
        if (p2 and ("下午" in p2 or "晚上" in p2)) or ("下午" in text and h2 < 12):
            if h2 < 12: h2 += 12
        if h2 < h1 and h2 < 12:
            h2 += 12

        start_hour, start_min = h1, m1
        end_hour, end_min = h2, m2
    else:
        # Match single time: colon (15:00), unit (15點), 4-digit (1430), or time prefix (下午2點)
        m_single = re.search(r'(?:(上午|早上|下午|晚上|中午)\s*)?(\d{1,2})(?::(\d{2}))\s*(半)?|(?:(上午|早上|下午|晚上|中午)\s*)?(\d{1,2})\s*(?:點|時)\s*(半)?|(?:(上午|早上|下午|晚上|中午)\s*)?\b(0[0-9]|1[0-9]|2[0-3])([0-5][0-9])\b', text_time_search)
        if m_single:
            groups = m_single.groups()
            if groups[1] is not None:
                p1, h1, min1, half1 = groups[0], groups[1], groups[2], groups[3]
            elif groups[5] is not None:
                p1, h1, min1, half1 = groups[4], groups[5], None, groups[6]
            else:
                p1, h1, min1, half1 = groups[7], groups[8], groups[9], None
            
            h1 = int(h1)
            m1 = 30 if half1 else (int(min1) if min1 else 0)
            if (p1 and ("下午" in p1 or "晚上" in p1)) or ("下午" in text and h1 < 12):
                if h1 < 12: h1 += 12
            start_hour, start_min = h1, m1
            end_hour, end_min = h1 + 1, m1
            if end_hour >= 24: end_hour = 23

    # Extract case name if present in long text (e.g., "個案姓名：葉武井", "個案：葉武井")
    extracted_name = None
    m_name = re.search(r'個案(?:姓名)?[：:]\s*([^\s\n\r,，\(（]+)', text)
    if m_name:
        extracted_name = m_name.group(1).strip()

    if extracted_name:
        clean_title = f"{extracted_name}家訪" if plan_type != "Private" else extracted_name
    elif len(clean_title) > 20 or "\n" in clean_title:
        first_line = clean_title.split("\n")[0].strip()
        if len(first_line) > 20 or len(clean_title) > 30:
            clean_title = "家訪" if plan_type != "Private" else "行程"
        else:
            clean_title = first_line

    if not clean_title:
        clean_title = "家訪" if plan_type != "Private" else "行程"

    has_explicit_date = bool(target_dates and (m_multi_date or m_single_dates or any(kw in text for kw in ["今天", "明天", "後天", "大後天", "週", "星期"])))
    has_explicit_time = bool(m_range or m_single)
    needs_conf = not (has_explicit_date and has_explicit_time)
    conf_reason = "未指定具體日期與時間，請確認" if (not has_explicit_date and not has_explicit_time) else ("未指定具體時間，請確認" if not has_explicit_time else ("未指定具體日期，請確認" if not has_explicit_date else ""))

    events = []
    for d in target_dates:
        s_dt = datetime(d.year, d.month, d.day, start_hour, start_min)
        e_dt = datetime(d.year, d.month, d.day, end_hour, end_min)
        events.append({
            "summary": clean_title,
            "start_time": s_dt.strftime("%Y-%m-%dT%H:%M:00"),
            "end_time": e_dt.strftime("%Y-%m-%dT%H:%M:00"),
            "description": "",
            "location": "",
            "plan_type": plan_type,
            "needs_confirmation": needs_conf,
            "confirmation_reason": conf_reason
        })

    return {
        "needs_confirmation": needs_conf,
        "confirmation_reason": conf_reason,
        "events": events
    }


