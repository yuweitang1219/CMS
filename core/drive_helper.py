import io
import os
import json
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google.oauth2 import service_account

def upload_plan_to_drive(state, plan_text):
    """
    Uploads the generated care plan to a shared Google Drive folder.
    Tries Google OAuth first, then falls back to GOOGLE_SERVICE_ACCOUNT_JSON.
    Automatically converts the uploaded file into a native, editable Google Doc.
    Returns a dict with 'success', 'file_id', and 'link'.
    """
    import database
    
    # 1. Retrieve the Google Drive Shared Folder ID from database settings or env var
    folder_id = database.get_setting("google_drive_folder_id") or os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        print("Google Drive Folder ID not configured in settings. Skipping upload.")
        return {"success": False, "error": "Folder ID not configured in database settings"}
        
    # 2. Try Google OAuth first
    service = None
    auth_error = None
    has_oauth_token = bool(database.get_setting("google_refresh_token") or os.environ.get("GOOGLE_REFRESH_TOKEN"))
    
    try:
        from core.calendar_helper import get_oauth_drive_service
        service = get_oauth_drive_service()
    except Exception as oe:
        print(f"Error building Google OAuth Drive service: {oe}")
        auth_error = str(oe)
        
    # 3. Fallback to Service Account JSON if OAuth not configured/available
    if not service:
        if has_oauth_token:
            print("Google OAuth token exists but failed to refresh (likely invalid_grant). Guiding user to re-authenticate.")
            return {
                "success": False, 
                "error": "Google 帳號授權憑證已過期 (invalid_grant)。請前往系統面板重新點選「連結 Google 帳號」即可修復！"
            }
            
        service_account_json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not service_account_json_str:
            service_account_json_str = database.get_setting("google_service_account_json")
            
        if not service_account_json_str:
            print("Google credentials (OAuth and Service Account) not configured. Skipping upload.")
            return {"success": False, "error": "Google 帳號未連結，且未設定服務帳號 (Service Account) 金鑰憑證。"}
            
        try:
            service_account_info = json.loads(service_account_json_str)
            SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
            service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error authenticating with Service Account for Google Drive: {e}")
            return {"success": False, "error": f"服務帳號驗證失敗: {str(e)}"}
        
    name = state.get("name", "計畫書")
    visit_date = state.get("visitDate")
    
    plan_type_map = {
        "AA01": "AA01",
        "ReEval": "複評",
        "CoVisit": "共訪",
        "NewCase": "新案",
        "PreNewCase": "準新案",
        "PlanChange": "異動",
        "Private": "私人"
    }
    plan_type = state.get("planType", "AA01")
    plan_type_name = plan_type_map.get(plan_type, plan_type)
    
    if visit_date:
        try:
            parts = visit_date.split("-")
            roc_year = int(parts[0]) - 1911
            roc_str = f"{roc_year}{parts[1]}{parts[2]}"
        except Exception:
            roc_str = visit_date
    else:
        import datetime
        today = datetime.date.today()
        roc_year = today.year - 1911
        roc_str = f"{roc_year}{today.month:02d}{today.day:02d}"
        
    doc_title = f"{roc_str} {name}({plan_type_name})"
    
    # 4. Generate HTML content formatted for Microsoft Word / Google Docs
    html_content = f"""
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head><meta charset='utf-8'><title>{doc_title}</title></head>
    <body>
        <div style="font-family: 'Microsoft JhengHei', sans-serif; font-size: 14pt; line-height: 1.8;">
            {plan_text.replace("\n", "<br>")}
        </div>
    </body>
    </html>
    """
    
    # 5. Define Google Drive file metadata
    file_metadata = {
        'name': doc_title,
        'mimeType': 'application/vnd.google-apps.document',  # Directs Google Drive to convert HTML to Google Doc format
        'parents': [folder_id]
    }
    
    try:
        # 6. Upload the file to Google Drive
        fh = io.BytesIO(html_content.encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/html', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        file_id = file.get('id')
        web_link = file.get('webViewLink')
        
        print(f"File uploaded successfully to Google Drive. ID: {file_id}, Link: {web_link}")
        
        # 7. Transfer ownership to the user's primary email if configured (to prevent service account quota issues)
        user_email = database.get_setting("google_user_email") or os.environ.get("GOOGLE_USER_EMAIL")
        if user_email:
            try:
                # Grant owner permission (requires transferOwnership=True)
                service.permissions().create(
                    fileId=file_id,
                    body={
                        'role': 'owner',
                        'type': 'user',
                        'emailAddress': user_email
                    },
                    transferOwnership=True
                ).execute()
                print(f"File ownership transferred to {user_email}")
            except Exception as pe:
                print(f"Warning: Failed to transfer file ownership to {user_email}: {pe}")
                # Fallback: grant writer permission so the user can still edit it
                try:
                    service.permissions().create(
                        fileId=file_id,
                        body={
                            'role': 'writer',
                            'type': 'user',
                            'emailAddress': user_email
                        }
                    ).execute()
                    print(f"Granted fallback writer permission to {user_email}")
                except Exception as fe:
                    print(f"Warning: Failed to grant writer permission to {user_email}: {fe}")
                    
        return {"success": True, "file_id": file_id, "link": web_link}
    except Exception as e:
        print(f"Error executing file creation on Google Drive API: {e}")
        err_msg = str(e)
        err_msg_lower = err_msg.lower()
        if "storagequotaexceeded" in err_msg_lower or "storage quota" in err_msg_lower or "quotaexceeded" in err_msg_lower:
            return {
                "success": False, 
                "error": "Google 雲端硬碟容量已滿 (storageQuotaExceeded)。\n👉 若您使用的是服務帳號 (Service Account)，因服務帳號無容量配額，請前往後台設定頁面重新「連結 Google 帳號」；若已連結個人帳號，請至 Google 雲端硬碟清理空間。"
            }
        if "insufficient" in err_msg_lower or "permission" in err_msg_lower:
            return {
                "success": False, 
                "error": "Google 雲端硬碟寫入權限不足。請前往後台設定頁面，重新點選「連結 Google 帳號」，並在授權畫面中勾選「儲存與編輯您已透過此應用程式建立或開啟的 Google 雲端硬碟檔案 (drive.file)」權限。"
            }
        return {"success": False, "error": err_msg}

def get_latest_case_plan_from_drive(case_name):
    """
    Searches for the most recent previous care plan file matching `case_name` STRICTLY WITHIN
    the authorized Google Drive folder.
    Exports and returns the plain text of the document, or None if not found/error.
    """
    import database
    folder_id = database.get_setting("google_drive_folder_id") or os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id or not case_name or case_name == "未提供資料":
        return None
        
    service = None
    try:
        from core.calendar_helper import get_oauth_drive_service
        service = get_oauth_drive_service()
    except Exception as oe:
        print(f"Error getting OAuth Drive service for reading: {oe}")
        
    if not service:
        service_account_json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or database.get_setting("google_service_account_json")
        if service_account_json_str:
            try:
                service_account_info = json.loads(service_account_json_str)
                SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=SCOPES
                )
                service = build('drive', 'v3', credentials=credentials)
            except Exception:
                pass
                
    if not service:
        return None
        
    try:
        # Escape single quotes in case_name for Drive API query
        safe_name = case_name.replace("'", "\\'")
        query = f"'{folder_id}' in parents and name contains '{safe_name}' and trashed = false"
        
        results = service.files().list(
            q=query,
            orderBy="name desc, createdTime desc",
            pageSize=5,
            fields="files(id, name, mimeType, createdTime)"
        ).execute()
        
        files = results.get("files", [])
        if not files:
            print(f"No previous Drive files found for case '{case_name}' in folder {folder_id}.")
            return None
            
        latest_file = files[0]
        file_id = latest_file["id"]
        mime_type = latest_file.get("mimeType", "")
        print(f"Found latest previous Drive file for '{case_name}': {latest_file.get('name')} (ID: {file_id})")
        
        # Export Google Doc to plain text, or download text
        if "vnd.google-apps.document" in mime_type:
            request = service.files().export_media(fileId=file_id, mimeType='text/plain')
            file_content = request.execute().decode('utf-8', errors='ignore')
            return file_content
        else:
            request = service.files().get_media(fileId=file_id)
            file_content = request.execute().decode('utf-8', errors='ignore')
            return file_content
    except Exception as e:
        print(f"Error reading case plan from Drive: {e}")
        return None

import re

def extract_exact_last_problems(prev_plan_text):
    """
    Extracts the exact '本次問題清單' from previous plan text to use as '上次問題清單' for the new plan.
    """
    if not prev_plan_text:
        return ""
    match = re.search(r"本次問題清單\s*[:：]\s*([^\n\r]+)", prev_plan_text)
    if match:
        extracted = match.group(1).strip()
        if extracted:
            return extracted
    match2 = re.search(r"問題清單\s*[:：]\s*([^\n\r]+)", prev_plan_text)
    if match2:
        extracted = match2.group(1).strip()
        if extracted:
            return extracted
    return ""

def analyze_case_delta_with_ai(prev_plan_text, current_state):
    """
    Uses Gemini AI to compare the previous plan text downloaded from Drive with the current case state.
    Returns a dict with 'last_problems' (string) and 'delta_analysis' (string).
    """
    if not prev_plan_text:
        return {"last_problems": "", "delta_analysis": "（無前次雲端檔案紀錄，視為新案或初次紀錄）"}
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        import database
        api_key = database.get_setting("gemini_api_key")
        
    regex_last = extract_exact_last_problems(prev_plan_text)
        
    if not api_key:
        return {"last_problems": regex_last, "delta_analysis": "（未設定 Gemini API 金鑰，無法進行自動 AI 比對）"}
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        prompt = f"""
你是一位專業的長照個案管理師助手。請比對【前次雲端硬碟照顧計畫書內容】與【本次家訪最新個案狀況】，進行簡潔、專業的差異比對分析。

【前次雲端照顧計畫書內文】
{prev_plan_text[:2500]}

【本次最新個案資料】
- 個案姓名：{current_state.get('name')}
- CMS等級：第{current_state.get('cmsLvl')}級
- 意識：{current_state.get('consciousness')}，對談：{current_state.get('interaction')}
- 疾病史：{', '.join(current_state.get('selectedConditions', []))}
- 特殊管路：{', '.join(current_state.get('selectedTubes', []))}
- 認知行為：{', '.join(current_state.get('selectedCognition', []))}
- 跌倒紀錄：{', '.join(current_state.get('selectedFalls', []))}，近半年跌倒：{current_state.get('recentFalls')}
- 主要照顧者狀況：{current_state.get('caregiverHealth')}，負荷：{current_state.get('burdenStr')}
- 現有服務：{', '.join(current_state.get('activeServices', []))}

請輸出繁體中文 JSON 格式：
{{
  "last_problems": "精簡列出從前次檔案中提取的『上次問題清單』（若無則摘要前次核心問題）",
  "delta_analysis": "以條列式精簡摘要『兩次紀錄的主要差異』與『本次重點關注/問題點提醒』（約100-200字）"
}}
JSON 必須格式正確，不要加上 Markdown 程式碼區塊標記。
"""
        response = None
        MODELS_TO_TRY = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash-latest', 'gemini-flash-latest']
        for model_name in MODELS_TO_TRY:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    break
            except Exception as me:
                print(f"Model {model_name} failed in analyze_case_delta_with_ai: {me}")
                
        if not response:
            return {"last_problems": "", "delta_analysis": "（無法調用 Gemini AI 模型進行差異分析）"}

        res_text = response.text.strip()
        if res_text.startswith("```"):
            res_text = res_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        res_json = json.loads(res_text)
        return {
            "last_problems": regex_last or res_json.get("last_problems", ""),
            "delta_analysis": res_json.get("delta_analysis", "")
        }
    except Exception as e:
        print(f"Error in analyze_case_delta_with_ai: {e}")
        return {"last_problems": "", "delta_analysis": f"（前次紀錄比對解析完成，但 AI 分析略過：{e}）"}


