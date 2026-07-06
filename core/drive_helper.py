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
    
    # 1. Retrieve the Google Drive Shared Folder ID from database settings
    folder_id = database.get_setting("google_drive_folder_id")
    if not folder_id:
        print("Google Drive Folder ID not configured in settings. Skipping upload.")
        return {"success": False, "error": "Folder ID not configured in database settings"}
        
    # 2. Try Google OAuth first
    service = None
    auth_error = None
    try:
        from core.calendar_helper import get_oauth_drive_service
        service = get_oauth_drive_service()
    except Exception as oe:
        print(f"Error building Google OAuth Drive service: {oe}")
        auth_error = str(oe)
        
    # 3. Fallback to Service Account JSON if OAuth not configured/available
    if not service:
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
        return {"success": True, "file_id": file_id, "link": web_link}
    except Exception as e:
        print(f"Error executing file creation on Google Drive API: {e}")
        err_msg = str(e)
        if "insufficient" in err_msg.lower() or "permission" in err_msg.lower():
            return {
                "success": False, 
                "error": "Google 雲端硬碟寫入權限不足。請前往後台設定頁面，重新點選「連結 Google 帳號」，並在授權畫面中勾選「儲存與編輯您已透過此應用程式建立或開啟的 Google 雲端硬碟檔案 (drive.file)」權限。"
            }
        return {"success": False, "error": err_msg}
