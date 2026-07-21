import os
import datetime
from .constants import (LTC_SERVICES, COPAY_RATES, PROBLEM_LIST, CMS_QUOTA_MAP,
                        TRAFFIC_QUOTA_MAP, RESPITE_QUOTA_MAP, EF_QUOTA, KEYWORD_SERVICE_MAP)

def generate_plan(state):
    """
    state expects a dictionary:
    {
      "name": "OOO",
      "birthYear": "1940",
      "familyName": "OOO",
      "familyRel": "OO",
      "visitDate": "2026-04-17",
      "statusVal": "1", # 1=一般, 2=中低收, 3=低收
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
      "activeServices": [], # e.g. ["BA07", "BA05"]
      "serviceTimes": {},   # e.g. {"BA07": 12, "BA05": 20}
      "customPrices": {}
    }
    """
    # 預設值與資料解析 (加上防呆型態轉換以防 AI 提取非數字內容崩潰)
    try:
        cmsLvl = int(state.get('cmsLvl', 4))
    except (ValueError, TypeError):
        cmsLvl = 4
        
    try:
        trafLvl = int(state.get('trafLvl', 2))
    except (ValueError, TypeError):
        trafLvl = 2
        
    statusVal = str(state.get('statusVal', '1'))
    if statusVal not in ['1', '2', '3']:
        statusVal = '1'
        
    hasF = bool(state.get('hasF', False))
    
    # 確保 activeServices 為可迭代的 list
    active_services_raw = state.get('activeServices')
    if not isinstance(active_services_raw, list):
        active_services_raw = [active_services_raw] if isinstance(active_services_raw, str) else []
    active_services = set(active_services_raw)
    
    # 確保 serviceTimes 與 customPrices 為 dict
    service_times = state.get('serviceTimes')
    if not isinstance(service_times, dict):
        service_times = {}
        
    custom_prices = state.get('customPrices')
    if not isinstance(custom_prices, dict):
        custom_prices = {}

    if statusVal == '3':
        custom_prices['OT'] = 0
    elif statusVal == '2':
        custom_prices['OT'] = 10
    elif statusVal == '1':
        custom_prices['OT'] = 80

    # ----------------額度計算----------------
    bcCost = dCost = gCost = efCost = zCost = scCost = otCost = 0
    planDetails = []

    for code in active_services:
        svc = next((s for s in LTC_SERVICES if s['code'] == code), None)
        if not svc:
            continue
            
        # 安全轉型服務次數與自付價，避免 ValueError (例如空字串) 或 TypeError (例如 None)
        try:
            times = int(float(service_times.get(code, 1)))
        except (ValueError, TypeError):
            times = 1
            
        try:
            price = int(float(custom_prices.get(code, svc['price'])))
        except (ValueError, TypeError):
            price = svc['price']
            
        cost = price * times
        
        detail = {'code': code, 'desc': svc['desc'], 'times': times, 'price': price, 'cost': cost, 'type': svc['type'], 'evalReq': svc.get('evalReq', False)}
        planDetails.append(detail)
        
        t = svc['type']
        if t == 'BC': bcCost += cost
        elif t == 'D': dCost += cost
        elif t == 'G': gCost += cost
        elif t == 'EF': efCost += cost
        elif t == 'Z': zCost += cost
        elif t == 'SC': scCost += cost
        elif t == 'OT': otCost += cost

    maxBC = CMS_QUOTA_MAP.get(cmsLvl, 0)
    if hasF:
        maxBC = round(maxBC * 0.3)

    maxD = TRAFFIC_QUOTA_MAP.get(trafLvl, 0)
    maxG = RESPITE_QUOTA_MAP.get(cmsLvl, 0)
    maxSC = (71610 if cmsLvl >= 7 else 87780) if hasF else 0

    bcRem = maxBC - bcCost
    dRem = maxD - dCost
    gRem = maxG - gCost
    efRem = EF_QUOTA - efCost
    scRem = maxSC - scCost

    # ----------------問題清單推導----------------
    active_problems = set()
    for code in active_services:
        matched = [p for p in PROBLEM_LIST if p.get('baCode') == code or (p.get('baCode') and p.get('baCode').startswith(code))]
        for mp in matched:
            active_problems.add(mp['id'])

    activeProbNames = [p['name'] for p in PROBLEM_LIST if p['id'] in active_problems]
    currentProblemsStr = "、".join(activeProbNames) if activeProbNames else "無"

    goalsStr = ""
    goalIndex = 1
    if active_problems:
        for p in PROBLEM_LIST:
            if p['id'] in active_problems:
                baCode = p.get('baCode', '')
                baDesc = p.get('baDesc', '')
                isMissingService = bool(baCode) and baCode not in active_services and not any(baCode.split('-')[0] in s for s in active_services)
                
                text_part = p.get('text', '').split('，')
                text_part = text_part[1] if len(text_part) > 1 else '提供相關照護服務。'
                
                lineText = f"{goalIndex}. {p['name']}:核定[{baCode}{baDesc}]，{text_part}"
                if isMissingService:
                    goalsStr += f"{lineText} (此服務尚未核定)\\n"
                else:
                    goalsStr += f"{lineText}\\n"
                goalIndex += 1
    else:
        goalsStr = "1. 維持生活功能，防止失能退化。\\n"

    # ----------------組裝字串與文字----------------
    name = state.get('name', 'ＯＯＯ')
    birthYear = state.get('birthYear', '')
    familyName = state.get('familyName', 'ＯＯＯ')
    familyRel = state.get('familyRel', 'ＯＯ')
    
    try:
        age_num = datetime.datetime.now().year - int(birthYear)
        roc_year = int(birthYear) - 1911
        age = str(age_num)
        rocYear = str(roc_year)
    except:
        age = 'Ｏ'
        rocYear = 'ＯＯ'

    visitDateRaw = state.get('visitDate', '')
    try:
        parts = visitDateRaw.split('-')
        visitDateRoc = f"{int(parts[0])-1911}年{parts[1]}月{parts[2]}日"
    except:
        visitDateRoc = "ＯＯＯ年ＯＯ月ＯＯ日"

    copayIdx = int(statusVal) - 1

    feeStr = f"【費用與額度試算】\\n"
    feeStr += f"(B/C照顧額度：${maxBC:,}/月{ ' *受外看影響，降至30%額度*' if hasF else ''})\\n"
    feeStr += f"(D交通接送額度：${maxD:,}/月)\\n"
    if hasF: feeStr += f"(SC短照額度：${maxSC:,}/年)\\n"

    bCodeStr = cCodeStr = dCodeStr = efCodeStr = gCodeStr = scCodeStr = zCodeStr = otCodeStr = ""
    totalPlanSelfPay = 0

    if planDetails:
        for t in ['BC', 'D', 'G', 'EF', 'SC', 'Z', 'OT']:
            tItems = [d for d in planDetails if d['type'] == t]
            if tItems:
                catName = {'BC':'照顧及專業服務 (每月額度)', 'D':'交通接送服務 (每月額度)', 'G':'喘息服務 (年度額度)', 'EF':'輔具/無障礙 (三年額度)', 'SC':'短期替代照顧 (年度額度)', 'OT':'營養餐飲服務', 'Z':'縣市自辦項目'}.get(t)
                feeStr += f"\\n[{catName}]\\n"
                tCost = 0
                for s in tItems:
                    eTag = ' *(需要輔具中心老師評估)*' if s.get('evalReq') else ''
                    serviceLine = f"{s['code']}[{s['desc']}] *{s['times']}{'次/月' if t not in ['EF', 'G', 'SC', 'Z'] else ('組' if t=='EF' else '次/年' if t in ['G', 'SC'] else '次')}{eTag}"
                    
                    if t == 'BC':
                        if s['code'].startswith('C'): cCodeStr += f"{serviceLine}\\n"
                        else: bCodeStr += f"{serviceLine}\\n"
                    elif t == 'D': dCodeStr += f"{serviceLine}\\n"
                    elif t == 'EF': efCodeStr += f"1. {serviceLine}\\n"
                    elif t == 'G': gCodeStr += f"{serviceLine}\\n"
                    elif t == 'SC': scCodeStr += f"{serviceLine}\\n"
                    elif t == 'Z': zCodeStr += f"{serviceLine}\\n"
                    elif t == 'OT': otCodeStr += f"{serviceLine}\\n"

                    feeStr += f"- {s['code']} [{s['desc']}]{eTag}： {s['times']} 次，估算：${s['cost']:,} 元\\n"
                    tCost += s['cost']

                tLimit = {'BC':maxBC, 'D':maxD, 'G':maxG, 'EF':EF_QUOTA, 'SC':maxSC}.get(t, 0)
                r = COPAY_RATES.get(t, [0,0,0])[copayIdx]

                if t == 'Z':
                    feeStr += f"(本類別總費用：${tCost:,} 元，目前設定全額自費)\\n"
                    totalPlanSelfPay += tCost
                elif t == 'OT':
                    feeStr += f"(本類別總自付額：${tCost:,} 元)\\n"
                    totalPlanSelfPay += tCost
                else:
                    tRem = tLimit - tCost
                    overLimit = tCost - tLimit if tCost > tLimit else 0
                    withinLimit = tLimit if tCost > tLimit else tCost
                    copayAmount = round(withinLimit * r)
                    selfPayForType = copayAmount + overLimit
                    totalPlanSelfPay += selfPayForType

                    feeStr += f"▶ 本類別總額度：${tLimit:,}，剩餘額度：${tRem:,}\\n"
                    feeStr += f"▶ 經試算本分類預估自付額：${selfPayForType:,} 元{f' (內含超額自費：${overLimit:,})' if overLimit > 0 else ''}\\n"
        feeStr += f"\\n=========================\n💰 【本計畫預估總自付費用】：${totalPlanSelfPay:,} 元\n========================="
    else:
        feeStr += "\\n(目前尚未配置任何服務項目)"

    # ----------------計畫書文字----------------
    def genStr(lst, def_msg):
        if not lst:
            return def_msg
        if isinstance(lst, str):
            return lst
        if isinstance(lst, (list, tuple, set)):
            return "、".join(str(x) for x in lst if x is not None)
        return str(lst)

    condStr = genStr(state.get('selectedConditions', []), '無明顯重大慢性病史')
    senStr = genStr(state.get('selectedSensory', []), '感官均無明顯異常')
    tubesStr = genStr(state.get('selectedTubes', []), '無')
    cogStr = genStr(state.get('selectedCognition', []), '無明顯異常')
    fallStr = genStr(state.get('selectedFalls', []), '無')
    
    def format_adl_grouped(data_dict):
        if not data_dict:
            return "無"
        if not isinstance(data_dict, dict):
            return str(data_dict)
            
        groups = {}
        for k, v in data_dict.items():
            if not v:
                continue
            groups.setdefault(str(v), []).append(str(k))
            
        parts = []
        ordered_levels = ["完全協助", "部分協助", "需要協助", "需協助", "獨立"]
        seen_levels = set()
        
        for level in ordered_levels:
            if level in groups:
                items = groups[level]
                seen_levels.add(level)
                items_str = "、".join(items)
                
                if level == "部分協助":
                    suffix = "皆需部分協助" if len(items) > 1 else "需部分協助"
                elif level == "完全協助":
                    suffix = "皆需完全協助" if len(items) > 1 else "需完全協助"
                elif level == "獨立":
                    suffix = "皆可獨立" if len(items) > 1 else "可獨立"
                elif level in ["需要協助", "需協助"]:
                    suffix = "皆需協助" if len(items) > 1 else "需協助"
                else:
                    suffix = f"皆{level}" if len(items) > 1 else level
                    
                parts.append(f"{items_str}{suffix}")
                
        for level, items in groups.items():
            if level not in seen_levels:
                items_str = "、".join(items)
                suffix = f"皆{level}" if len(items) > 1 else level
                parts.append(f"{items_str}{suffix}")
                
        return "、".join(parts) if parts else "無"

    adlVal = format_adl_grouped(state.get('adlData', {}))
    iadlVal = format_adl_grouped(state.get('iadlData', {}))

    incomeVal = genStr(state.get('selectedIncome', []), '無明顯收入來源')
    livingStr = state.get('livingStr', '無')

    planType = state.get('planType', 'AA01')
    lastProblemList = state.get('lastProblemList', '')
    
    # 自動調取指定 Google Drive 資料夾內的該個案前次歷史檔案，進行差異比對
    delta_analysis_text = ""
    if name and name != "未提供資料":
        try:
            database.update_case_record(
                name=name,
                last_visit_date=state.get("visitDate"),
                address=state.get("address"),
                plan_type=state.get("planType")
            )
        except Exception as ce:
            print(f"Error updating case record in DB: {ce}")

        try:
            from core.drive_helper import get_latest_case_plan_from_drive, analyze_case_delta_with_ai
            prev_plan_text = get_latest_case_plan_from_drive(name)
            if prev_plan_text:
                delta_info = analyze_case_delta_with_ai(prev_plan_text, state)
                if not lastProblemList and delta_info.get("last_problems"):
                    lastProblemList = delta_info["last_problems"]
                if delta_info.get("delta_analysis"):
                    delta_analysis_text = f"\n\n====================\n🔍 【前後次紀錄 AI 差異比對與問題點分析】\n{delta_info['delta_analysis']}\n===================="
        except Exception as de_err:
            print(f"Error fetching/analyzing case history from Drive: {de_err}")

    planTypeMap = {
        "AA01": "AA01家訪擬定照顧計畫",
        "ReEval": "單位複評計畫擬定",
        "CoVisit": "共訪",
        "NewCase": "新案",
        "PreNewCase": "出準新案",
        "PlanChange": "計畫異動"
    }
    planTypeText = planTypeMap.get(planType, planType)

    # 提取身心概況及主要照顧者之細部資料變數

    # 防呆轉換性別欄位型態，避免非字串物件（例如 None 或 1）引發 TypeError
    gender = state.get('gender')
    if gender is not None:
        gender_str = str(gender)
        if gender_str not in ['男', '女']:
            if '男' in gender_str: gender = '男'
            elif '女' in gender_str: gender = '女'
            else: gender = '女'
        else:
            gender = gender_str
    else:
        gender = '女'

    consciousness = state.get('consciousness', '清楚')
    interaction = state.get('interaction', '簡單對談')
    orientation = state.get('orientation', '清楚')
    vision = state.get('vision', '正常')
    hearing = state.get('hearing', '正常')
    recentFalls = state.get('recentFalls', '近半年無')
    emotion = state.get('emotion', '穩定')
    
    # 確保主要照顧者出生年份轉為字串後處理，預防整數格式崩潰
    caregiverBirthYear = state.get('caregiverBirthYear')
    if caregiverBirthYear is not None:
        caregiverBirthYear = str(caregiverBirthYear).replace('年次', '').replace('年', '')
    else:
        caregiverBirthYear = 'ＯＯ'
        
    caregiverJob = state.get('caregiverJob', '退休')
    caregiverHealth = state.get('caregiverHealth', '無明顯不適')
    serviceUsageStatus = state.get('serviceUsageStatus', '服務穩定使用中')

    if planType == 'ReEval':
        planText = f"""複評後重新擬定照顧計畫
一、電聯日期: 專員協助約訪
二、家訪日期: {visitDateRoc}
三、偕同訪視者: 個管師-湯育維、家屬-{familyName}、個案-{name}
四、個案狀況: 
(一)身心概況：個案為{age}歲({rocYear}年次){gender}性，意識{consciousness}，{interaction}; 對於人事時地物{orientation}; 視力{vision}; 聽力{hearing}; {recentFalls}跌倒及住院紀錄; 情緒{emotion}; 疾病史：{condStr}。
管路與特殊照護：{tubesStr}
認知與行為狀態：{cogStr}
跌倒紀錄(過去一年)：{fallStr}
ADLs: {adlVal}
IADLs: {iadlVal}
(二)經濟收入：{incomeVal}
(三)居住環境：居住型態-{livingStr}
(四)社會支持: 
(1)社會資源:
(2)醫療資源:
(3)家庭支持系統:
主要照顧者: {familyRel}-{familyName}({caregiverBirthYear}年次)，{caregiverJob}，{caregiverHealth}。
照顧負荷情形: {state.get('burdenStr', '無明顯負荷')}
次要照顧者：無
其他家庭成員: {state.get('familyStatusVal', '無')}
(4)家庭支持動力狀況:
(五)其他: 無
(六)評值: 家訪後，CMS等級維持{cmsLvl}級，個案{serviceUsageStatus}。
五、照顧目標: 
(一)問題清單
上次問題清單: {lastProblemList}
本次問題清單: {currentProblemsStr}
(二)照顧目標
{goalsStr.strip()}
六、與照專建議服務項目、問題清單不一致原因說明及未來規劃、後續追蹤計畫: 
1. 
2. 


一、長照服務核定項目、頻率：
(一)B 碼：
{bCodeStr.strip() or '暫無使用需求。'}
(二)C 碼：
{cCodeStr.strip() or '暫無使用需求。'}
(三)D 碼：
{dCodeStr.strip() or '暫無使用需求。'}
(四)E.F 碼：
{efCodeStr.strip() or '暫無其他添購需求。'}
輔具額度區間：
輔具剩餘額度：
(五)G 碼：
喘息服務項目：{gCodeStr.strip() or '暫無使用需求。'}
喘息服務期間：
(六)SC 碼：
{scCodeStr.strip() or '暫無使用需求。'}
(七)營養餐飲服務：{otCodeStr.strip() or '不符合資格，未核定。'}
(八)緊急救援服務：不符合資格，未核定。
二、轉介其他資源連結：無。

上述計畫均與 {familyRel}({familyName}) 討論核定其了解計畫內容同意服務使用，並簽訂服務使用確認單。
個案管理員：湯育維"""

    elif planType == 'NewCase':
        planText = f"""新案居家訪視擬定照顧計畫
一、電聯日期：照專協助約訪
二、家訪日期：{visitDateRoc}
三、偕同訪視者：個管師-湯育維、家屬-{familyName}、個案-{name}
四、個案概況
(一)身心概況：個案為{age}歲({rocYear}年次){gender}性，意識{consciousness}，{interaction}; 對於人事時地物{orientation}; 視力{vision}; 聽力{hearing}; {recentFalls}跌倒及住院紀錄; 疾病史：{condStr}。
管路與特殊照護：{tubesStr}
認知與行為狀態：{cogStr}
跌倒紀錄(過去一年)：{fallStr}
ADLs: {adlVal}
IADLs: {iadlVal}
(二)經濟收入：{incomeVal}
(三)居住環境：居住型態-{livingStr}
(四)社會支持：
1.社會資源：
2.醫療資源：
3.家庭支持狀況：
主要照顧者：{familyRel}-{familyName}({caregiverBirthYear}年次)，{caregiverJob}，{caregiverHealth}。
照顧負荷情形：{state.get('burdenStr', '無明顯負荷')}
次要照顧者：無
其他家庭成員：{state.get('familyStatusVal', '無')}
家庭支持動力狀況：
(五)其他: 無
(六)評值：新案，CMS 第{cmsLvl}級，個案{serviceUsageStatus}。
五、問題清單及照顧目標
(一)本次問題清單: {currentProblemsStr}
(二)服務目標：
{goalsStr.strip()}
六、與照專建議服務項目、問題清單不一致原因說明及未來規劃、後續追蹤計劃等
1. 
2. 


一、長照服務核定項目、頻率：
(一)B 碼：
{bCodeStr.strip() or '暫無使用需求。'}
(二)C 碼：
{cCodeStr.strip() or '針對個案中風後站立平衡、行走訓練、肌耐力提升，避免跌倒，案家屬表示暫無需求。'}
(三)D 碼：
{dCodeStr.strip() or '暫無需求，未核定。'}
(四)E.F 碼：
{efCodeStr.strip() or '暫無其他添購需求。'}
輔具額度區間：
輔具剩餘額度：
(五)G 碼：
{gCodeStr.strip() or '暫無需求，未核定。'}
(六)SC 碼：
{scCodeStr.strip() or '不符合資格，未核定。'}
(七)營養餐飲服務：{otCodeStr.strip() or '不符合資格，未核定。'}
(八)緊急救援服務：不符合資格，未核定。
二、轉介其他服務資源：無。

上述計畫均與 {familyRel}({familyName}) 討論核定其了解計畫內容同意服務使用，並簽訂服務使用確認單。
個案管理員：湯育維"""

    else:
        planText = f"""{planTypeText}
一、電聯日期: 
二、家訪日期: {visitDateRoc} 
三、偕同訪視者: 個管師-湯育維、家屬-{familyName}、個案-{name}
四、個案狀況: 
(一)身心概況：個案為{age}歲({rocYear}年次){gender}性，意識{consciousness}，{interaction}; 對於人事時地物{orientation}; 視力{vision}; 聽力{hearing}; {recentFalls}跌倒及住院紀錄; 情緒{emotion}; 疾病史：{condStr}。
管路與特殊照護：{tubesStr}
認知與行為狀態：{cogStr}
跌倒紀錄(過去一年)：{fallStr}
ADLs: {adlVal}
IADLs: {iadlVal}
(二)經濟收入：{incomeVal}
(三)居住環境：居住型態-{livingStr}
(四)社會支持: 
(1)社會資源:
(2)醫療資源:
(3)家庭支持系統:
主要照顧者: {familyRel}-{familyName}({caregiverBirthYear}年次)，{caregiverJob}，{caregiverHealth}。
照顧負荷情形: {state.get('burdenStr', '無明顯負荷')}
次要照顧者：無
其他家庭成員: {state.get('familyStatusVal', '無')}
(4)家庭支持動力狀況：
(五)其他：無。
(六)評值：家訪後，CMS等級維持{cmsLvl}級，個案{serviceUsageStatus}。
5、照顧目標: 
(一)問題清單
上次問題清單: {lastProblemList}
本次問題清單: {currentProblemsStr}
(二)照顧目標
{goalsStr.strip()}
六、與照專建議服務項目、問題清單不一致原因說明及未來規劃、後續追蹤計畫: 
1. 
2. 


一、長照服務核定項目及頻率：
(一)B 碼：
{bCodeStr.strip() or '暫無使用需求。'}
(二)C 碼：
{cCodeStr.strip() or '暫無使用需求。'}
(三)D 碼：
{dCodeStr.strip() or '暫無使用需求。'}
(四)E.F 碼：
{efCodeStr.strip() or '暫無其他添購需求。'}
輔具額度區間：
輔具剩餘額度：
(五)G 碼：
喘息服務項目：{gCodeStr.strip() or '暫無使用需求。'}
喘息服務期間：
(六)SC 碼：
{scCodeStr.strip() or '暫無使用需求。'}
(七)營養餐飲服務：{otCodeStr.strip() or '不符合資格，未核定。'}
(八)緊急救援服務：不符合資格，未核定。
二、轉介其他資源連結：無。

上述計畫均與{familyRel}({familyName})討論核定其了解計畫內容同意服務使用，並簽訂服務使用確認單。
個案管理員：湯育維"""

    return {
        "feeStr": feeStr.replace("\\n", "\n"),
        "planText": (planText + delta_analysis_text).replace("\\n", "\n"),
        "isError": False
    }

