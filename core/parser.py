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
    
    If the user mentions "洗澡", activeServices should include "BA07" and serviceTimes should have {{"BA07": 12}} (default 12 times a month, roughly 3 times a week, unless specified otherwise).

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
        model = genai.GenerativeModel('gemini-3.5-flash')
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
    
    If the user mentions "洗澡", activeServices should include "BA07" and serviceTimes should have {{"BA07": 12}} (default 12 times a month, roughly 3 times a week, unless specified otherwise).

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
