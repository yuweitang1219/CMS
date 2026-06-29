import logging
from datetime import datetime, timedelta
from typing import Optional
import os
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, Response
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import database
import auth
import line_bot
import requests
import json

# Import Line SDK v3 components
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

# Import CarePlan Chatbot engine
from core.chatbot import process_chat, clear_session, load_session, load_rules, clear_rules
from core.engine import generate_plan

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

app = FastAPI(title="Google Calendar & To-Do Dashboard")

# Auto-populate admin user from environment variables if not present in DB
admin_user = os.environ.get("ADMIN_USERNAME", "yuwei1112")
admin_pass = os.environ.get("ADMIN_PASSWORD")
if admin_pass and not database.has_users():
    import auth
    hashed_pwd = auth.get_password_hash(admin_pass)
    database.create_user(admin_user, hashed_pwd)
    logger.info(f"Auto-populated admin user '{admin_user}' from environment variables.")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication dependency
async def get_current_user(request: Request) -> str:
    # 1. Try to get token from cookie
    token = request.cookies.get("session_token")
    
    # 2. Try to get token from Authorization header if cookie not present
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
        
    payload = auth.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
        
    return payload["sub"]

# Pydantic Schemas
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str

class TodoCreate(BaseModel):
    title: str
    priority: str = "medium"
    due_date: Optional[str] = None

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    completed: Optional[bool] = None

class SettingsGoogle(BaseModel):
    client_id: str
    client_secret: str
    calendar_id: Optional[str] = "primary"

class SettingsLine(BaseModel):
    channel_access_token: str
    channel_secret: str
    authorized_line_user_id: str
    gemini_api_key: Optional[str] = ""

class CalendarEventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: str # Format: "YYYY-MM-DDTHH:MM"
    end_time: str

# Helper: Google Token Manager
def get_valid_google_token() -> Optional[str]:
    client_id = database.get_setting("google_client_id")
    client_secret = database.get_setting("google_client_secret")
    refresh_token = database.get_setting("google_refresh_token")
    access_token = database.get_setting("google_access_token")
    expiry_str = database.get_setting("google_token_expiry")
    
    if not client_id or not client_secret or not refresh_token:
        return None
        
    # Check if expired (or expiring in 60s)
    is_expired = True
    if expiry_str:
        try:
            expiry = float(expiry_str)
            if expiry > datetime.utcnow().timestamp() + 60:
                is_expired = False
        except ValueError:
            pass
            
    if not is_expired:
        return access_token
        
    logger.info("Google access token expired. Attempting refresh...")
    
    # Refresh token request
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            new_access_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            new_expiry = datetime.utcnow().timestamp() + expires_in
            
            database.set_setting("google_access_token", new_access_token)
            database.set_setting("google_token_expiry", str(new_expiry))
            
            if data.get("refresh_token"):
                database.set_setting("google_refresh_token", data.get("refresh_token"))
                
            logger.info("Google access token successfully refreshed.")
            return new_access_token
        else:
            logger.error(f"Failed to refresh Google token. Response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Network error refreshing Google token: {e}")
        return None

def get_calendar_service_from_env():
    import os
    import json
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    # Try Service Account JSON from env (or database fallback)
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not service_account_json:
        service_account_json = database.get_setting("google_service_account_json")
        
    if not service_account_json:
        return None, None
        
    try:
        service_account_info = json.loads(service_account_json)
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=credentials)
        
        calendar_id = os.environ.get("GOOGLE_CALENDAR_ID")
        if not calendar_id:
            calendar_id = database.get_setting("google_calendar_id", "primary")
            
        return service, calendar_id
    except Exception as e:
        logger.error(f"Error building Service Account calendar service: {e}")
        return None, None

# --- AUTH API ENDPOINTS ---

@app.get("/api/auth/status")
def auth_status(request: Request):
    has_users = database.has_users()
    token = request.cookies.get("session_token")
    logged_in = False
    username = None
    if token:
        payload = auth.verify_token(token)
        if payload:
            logged_in = True
            username = payload["sub"]
    return {
        "has_users": has_users,
        "logged_in": logged_in,
        "username": username
    }

@app.post("/api/auth/register")
def register_user(user: UserRegister):
    # Only allow registration if no users exist (first-time setup)
    if database.has_users():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is locked. User already exists."
        )
    
    hashed_pwd = auth.get_password_hash(user.password)
    success = database.create_user(user.username, hashed_pwd)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user."
        )
    return {"message": "User registered successfully"}

@app.post("/api/auth/login")
def login(user: UserLogin):
    db_user = database.get_user(user.username)
    if not db_user or not auth.verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
        
    access_token = auth.create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60, # 7 days
        samesite="lax"
    )
    return response

@app.post("/api/auth/logout")
def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_token")
    return response

# --- TODO API ENDPOINTS (PROTECTED) ---

@app.get("/api/todos")
def list_todos(current_user: str = Depends(get_current_user)):
    return database.get_todos()

@app.post("/api/todos")
def create_todo(todo: TodoCreate, current_user: str = Depends(get_current_user)):
    todo_id = database.add_todo(todo.title, todo.priority, todo.due_date)
    return {"id": todo_id, "message": "Todo created successfully"}

@app.put("/api/todos/{todo_id}")
def update_todo(todo_id: int, todo: TodoUpdate, current_user: str = Depends(get_current_user)):
    success = database.update_todo(
        todo_id,
        title=todo.title,
        priority=todo.priority,
        due_date=todo.due_date,
        completed=todo.completed
    )
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo updated successfully"}

@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int, current_user: str = Depends(get_current_user)):
    success = database.delete_todo(todo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo deleted successfully"}

# --- SETTINGS API ENDPOINTS (PROTECTED) ---

@app.get("/api/settings")
def get_settings(request: Request, current_user: str = Depends(get_current_user)):
    g_client_id = database.get_setting("google_client_id", "")
    g_calendar_id = database.get_setting("google_calendar_id", "primary")
    g_email = database.get_setting("google_user_email", "")
    g_connected = bool(database.get_setting("google_refresh_token"))
    
    l_token = database.get_setting("line_channel_access_token", "")
    l_secret = database.get_setting("line_channel_secret", "")
    l_user_id = database.get_setting("line_authorized_user_id", "")
    l_gemini_key = database.get_setting("gemini_api_key", "")
    
    # Generate webhook URL based on incoming request domain
    base_url = str(request.base_url).rstrip('/')
    webhook_url = f"{base_url}/api/line/webhook"
    
    return {
        "google": {
            "client_id": g_client_id,
            "calendar_id": g_calendar_id,
            "connected": g_connected,
            "email": g_email
        },
        "line": {
            "webhook_url": webhook_url,
            "token_configured": bool(l_token),
            "secret_configured": bool(l_secret),
            "authorized_user_id": l_user_id,
            "gemini_api_key": l_gemini_key
        }
    }

@app.post("/api/settings/google")
def save_google_settings(settings: SettingsGoogle, request: Request, current_user: str = Depends(get_current_user)):
    old_client_id = database.get_setting("google_client_id", "")
    old_client_secret = database.get_setting("google_client_secret", "")
    
    # Only clear tokens if the client credentials themselves changed
    credentials_changed = (old_client_id != settings.client_id) or (old_client_secret != settings.client_secret)
    
    import urllib.parse
    
    raw_cal_id = settings.calendar_id or "primary"
    clean_cal_id = raw_cal_id.strip()
    if clean_cal_id.startswith("http://") or clean_cal_id.startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(clean_cal_id)
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'src' in query_params:
                clean_cal_id = query_params['src'][0]
            else:
                path_parts = parsed.path.strip('/').split('/')
                if 'calendar' in path_parts:
                    idx = path_parts.index('calendar')
                    if idx + 1 < len(path_parts):
                        clean_cal_id = urllib.parse.unquote(path_parts[idx + 1])
        except Exception as e:
            logger.error(f"Error parsing calendar ID from URL: {e}")
            
    logger.info(f"DEBUG SAVE: raw calendar_id from settings: '{settings.calendar_id}'")
    logger.info(f"DEBUG SAVE: clean_cal_id: '{clean_cal_id}'")
    
    database.set_setting("google_client_id", settings.client_id)
    database.set_setting("google_client_secret", settings.client_secret)
    database.set_setting("google_calendar_id", clean_cal_id)
    
    if credentials_changed:
        # Clear old tokens
        database.set_setting("google_access_token", None)
        database.set_setting("google_refresh_token", None)
        database.set_setting("google_token_expiry", None)
        database.set_setting("google_user_email", None)
    
    # Generate Google Authorization URL
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/oauth2callback"
    
    scopes = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scopes}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    return {"auth_url": auth_url}

@app.post("/api/settings/line")
def save_line_settings(settings: SettingsLine, current_user: str = Depends(get_current_user)):
    database.set_setting("line_channel_access_token", settings.channel_access_token)
    database.set_setting("line_channel_secret", settings.channel_secret)
    database.set_setting("line_authorized_user_id", settings.authorized_line_user_id)
    database.set_setting("gemini_api_key", settings.gemini_api_key)
    return {"message": "Line settings saved successfully"}

# --- GOOGLE OAUTH CALLBACK ENDPOINT (PUBLIC) ---

@app.get("/oauth2callback", response_class=HTMLResponse)
def oauth2callback(code: str, request: Request):
    client_id = database.get_setting("google_client_id")
    client_secret = database.get_setting("google_client_secret")
    
    if not client_id or not client_secret:
        return HTMLResponse("Error: Google Calendar settings missing in database.", status_code=400)
        
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/oauth2callback"
    
    # Token exchange request
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            return HTMLResponse(f"OAuth exchange failed: {response.text}", status_code=400)
            
        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)
        expiry = datetime.utcnow().timestamp() + expires_in
        
        database.set_setting("google_access_token", access_token)
        database.set_setting("google_token_expiry", str(expiry))
        if refresh_token:
            database.set_setting("google_refresh_token", refresh_token)
            
        # Get user email
        email = ""
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = requests.get(user_info_url, headers=headers, timeout=10)
        if user_response.status_code == 200:
            email = user_response.json().get("email", "")
            database.set_setting("google_user_email", email)
            
        # Redirect back to home via javascript
        return HTMLResponse("""
            <html>
                <body>
                    <p>Authorization successful! Redirecting to dashboard...</p>
                    <script>
                        window.location.href = '/';
                    </script>
                </body>
            </html>
        """)
        
    except Exception as e:
        logger.error(f"Error during OAuth callback: {e}")
        return HTMLResponse(f"OAuth error: {e}", status_code=500)

# --- GOOGLE CALENDAR PROXY API (PROTECTED) ---

@app.get("/api/calendar/events")
def list_calendar_events(current_user: str = Depends(get_current_user)):
    # 1. Try Service Account first (stateless env mode)
    service, calendar_id = get_calendar_service_from_env()
    if service:
        try:
            time_min = datetime.utcnow().isoformat() + "Z"
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                singleEvents=True,
                orderBy='startTime',
                maxResults=50
            ).execute()
            return events_result
        except Exception as e:
            logger.error(f"Error listing events via Service Account: {e}")
            return {"error": "google_api_error", "details": str(e), "events": []}

    # 2. Fallback to Google OAuth
    token = get_valid_google_token()
    if not token:
        return {"error": "not_authorized", "events": []}
        
    time_min = datetime.utcnow().isoformat() + "Z"
    calendar_id = database.get_setting("google_calendar_id", "primary")
    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "timeMin": time_min,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 50
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {"error": "unauthorized_by_google", "events": []}
        else:
            logger.error(f"Google Calendar API error {response.status_code}: {response.text}")
            return {"error": "google_api_error", "details": response.text, "events": []}
    except Exception as e:
        logger.error(f"Network error calling Google Calendar: {e}")
        return {"error": "network_error", "events": []}

@app.post("/api/calendar/events")
def create_calendar_event(event: CalendarEventCreate, current_user: str = Depends(get_current_user)):
    # Robustly handle datetime-local values that might or might not include seconds
    start_dt = event.start_time
    if len(start_dt.split("T")[-1].split(":")) == 2:
        start_dt = f"{start_dt}:00"
        
    end_dt = event.end_time
    if len(end_dt.split("T")[-1].split(":")) == 2:
        end_dt = f"{end_dt}:00"
        
    payload = {
        "summary": event.summary,
        "description": event.description or "",
        "start": {
            "dateTime": start_dt,
            "timeZone": "Asia/Taipei"
        },
        "end": {
            "dateTime": end_dt,
            "timeZone": "Asia/Taipei"
        }
    }
    
    # 1. Try Service Account first
    service, calendar_id = get_calendar_service_from_env()
    if service:
        try:
            created_event = service.events().insert(calendarId=calendar_id, body=payload).execute()
            return created_event
        except Exception as e:
            logger.error(f"Error creating event via Service Account: {e}")
            raise HTTPException(status_code=500, detail=f"Google API Error: {str(e)}")
            
    # 2. Fallback to Google OAuth
    token = get_valid_google_token()
    if not token:
        raise HTTPException(status_code=400, detail="Google Calendar is not authorized.")
    calendar_id = database.get_setting("google_calendar_id", "primary")
    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Google API Error: {response.text}"
            )
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/calendar/events/{event_id}")
def delete_calendar_event(event_id: str, current_user: str = Depends(get_current_user)):
    # 1. Try Service Account first
    service, calendar_id = get_calendar_service_from_env()
    if service:
        try:
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return {"message": "Event deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting event via Service Account: {e}")
            raise HTTPException(status_code=500, detail=f"Google API Error: {str(e)}")
            
    # 2. Fallback to Google OAuth
    token = get_valid_google_token()
    if not token:
        raise HTTPException(status_code=400, detail="Google Calendar is not authorized.")
    calendar_id = database.get_setting("google_calendar_id", "primary")
    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.delete(url, headers=headers, timeout=10)
        if response.status_code in [200, 204]:
            return {"message": "Event deleted successfully"}
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Google API Error: {response.text}"
            )
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

# --- LINE BOT HELPERS & ENDPOINTS ---

def format_state_summary(state):
    name = state.get("name", "未提供資料")
    age = "未提供"
    if state.get("birthYear") and state.get("birthYear") != "1940" and state.get("birthYear").isdigit():
        try:
            import datetime
            current_year = datetime.datetime.now().year
            age = f"{current_year - int(state['birthYear'])}歲 ({state['birthYear']}年次)"
        except:
            pass
    visit_date = state.get("visitDate", "未提供")
    cms = state.get("cmsLvl", "未提供")
    living = state.get("livingStr", "未提供")
    burden = state.get("burdenStr", "未提供")
    foreign = "有" if state.get("hasF") else "無"
    
    conds = "、".join(state.get("selectedConditions", [])) or "無明顯疾病"
    
    plan_type_map = {
        "AA01": "AA01家訪擬定照顧計畫",
        "ReEval": "單位複評計畫擬定",
        "CoVisit": "共訪",
        "NewCase": "新案",
        "PreNewCase": "出準新案",
        "PlanChange": "計畫異動"
    }
    plan_type = state.get("planType", "AA01")
    plan_type_name = plan_type_map.get(plan_type, plan_type)
    
    services = []
    active_services = state.get("activeServices", [])
    service_times = state.get("serviceTimes", {})
    for code in active_services:
        times = service_times.get(code, 1)
        services.append(f"{code}({times}次/月)")
    services_str = "、".join(services) or "尚未配置"
    
    summary = (
        "📋 【目前已收集個案資料摘要】\n"
        f"• 計畫類型：{plan_type_name}\n"
        f"• 個案姓名：{name}\n"
        f"• 年齡/年次：{age}\n"
        f"• 家訪日期：{visit_date}\n"
        f"• CMS 等級：{cms} 級\n"
        f"• 居住型態：{living}\n"
        f"• 照顧者負荷：{burden}\n"
        f"• 聘僱外籍看護：{foreign}\n"
        f"• 疾病史：{conds}\n"
        f"• 已配置服務：{services_str}\n\n"
        "💡 您可以隨時補充或修改資訊，或輸入「完成」來生成完整的照顧計畫書與費用試算。"
    )
    return summary

@app.get("/download/{user_id}")
def download_care_plan(user_id: str):
    state = load_session(user_id)
    if not state or state.get("name") == "未提供資料":
        raise HTTPException(status_code=404, detail="找不到該個案資料，請先在 LINE 上與 AI 進行對話以建立個案記錄！")
        
    result = generate_plan(state)
    plan_text = result.get("planText", "")
    
    html_content = f"""
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head><meta charset='utf-8'><title>照護計畫書</title></head>
    <body>
        <div style="font-family: 'Microsoft JhengHei', sans-serif; font-size: 14pt; line-height: 1.8;">
            {plan_text.replace("\n", "<br>")}
        </div>
    </body>
    </html>
    """
    
    response_data = '\ufeff' + html_content
    name = state.get("name", "計畫書")
    filename = f"{name}_照顧計畫.doc"
    encoded_filename = urllib.parse.quote(filename)
    
    return Response(
        content=response_data.encode('utf-8'),
        media_type="application/msword",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )

@app.post("/api/line/webhook")
async def line_webhook(request: Request):
    body = await request.body()
    body_str = body.decode('utf-8')
    signature = request.headers.get("x-line-signature", "")
    
    # Retrieve configuration settings: DB first, then env var fallback
    channel_secret = database.get_setting("line_channel_secret") or os.environ.get("LINE_CHANNEL_SECRET")
    channel_access_token = database.get_setting("line_channel_access_token") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    authorized_user_id = database.get_setting("line_authorized_user_id") or os.environ.get("LINE_AUTHORIZED_USER_ID")
    gemini_api_key = database.get_setting("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
    
    if not channel_secret or not channel_access_token:
        logger.warning("Line webhook received, but Line settings are not configured.")
        return {"status": "Line configuration missing"}
        
    handler = WebhookHandler(channel_secret)
    configuration = Configuration(access_token=channel_access_token)
    configuration.verify_ssl = False
    
    # Retrieve host base URL dynamically for the doc download link
    base_url = str(request.base_url).rstrip('/')
    
    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_message(event):
        user_text = event.message.text.strip()
        user_id = event.source.user_id
        
        # Check if user is the authorized supervisor
        if authorized_user_id and user_id != authorized_user_id:
            logger.warning(f"Line message from unauthorized user ID: {user_id}")
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="⚠️ 系統錯誤：此帳號未獲得授權，無法使用本長照 AI 助理。")]
                    )
                )
            return
            
        reply_msg = ""
        
        # Process command keyword matching
        if user_text in ["重新開始", "reset", "清空", "清除", "重新開始擬定"]:
            clear_session(user_id)
            reply_msg = "🧹 已清除目前的紀錄！我們可以開始為新個案填寫資料了。請輸入個案姓名或基本概況開始。"
        elif user_text in ["自訂規則", "學習清單", "記憶", "rules"]:
            rules = load_rules(user_id)
            if rules:
                reply_msg = "🧠 【已學習的自訂規則清單】：\n" + "\n".join([f"• {r}" for r in rules]) + "\n\n💡 提示：輸入「清除記憶」即可清空這些自訂規則。"
            else:
                reply_msg = "🧠 目前暫無自訂學習規則。您可以直接對話告訴我，例如：「記住，陳照專的名字是陳美麗」，我會自動學習並套用。"
        elif user_text in ["清除記憶", "忘記規則", "重新學習", "forget"]:
            clear_rules(user_id)
            reply_msg = "🧹 已成功清除所有已學習的自訂規則與記憶！恢復出廠設定。"
        elif user_text in ["目前資料", "狀態", "資料", "status"]:
            state = load_session(user_id)
            reply_msg = format_state_summary(state)
        elif user_text in ["個案清單", "清單", "list"]:
            from core.chatbot import SESSION_DIR
            import os
            os.makedirs(SESSION_DIR, exist_ok=True)
            files = os.listdir(SESSION_DIR)
            cases = []
            for f in files:
                if f.endswith(".json"):
                    name = f[:-5]
                    if not (name.startswith("U") and len(name) > 30) and name != "test_user_999":
                         cases.append(name)
            if cases:
                reply_msg = "📂 系統中可用的個案資料有：\n" + "\n".join([f"• {c}" for c in cases]) + "\n\n💡 輸入「載入 <個案姓名>」即可載入資料！\n例如：載入 張惠美"
            else:
                reply_msg = "📂 目前沒有已解析的個案資料。"
        elif user_text.startswith("載入") or user_text.lower().startswith("load "):
            from core.chatbot import SESSION_DIR
            import shutil
            case_name = ""
            if user_text.startswith("載入 "):
                case_name = user_text[3:].strip()
            elif user_text.startswith("載入"):
                case_name = user_text[2:].strip()
            elif user_text.lower().startswith("load "):
                case_name = user_text[5:].strip()
                
            if not case_name:
                reply_msg = "⚠️ 請指定要載入的個案姓名，例如「載入 張惠美」。"
            else:
                os.makedirs(SESSION_DIR, exist_ok=True)
                source_path = os.path.join(SESSION_DIR, f"{case_name}.json")
                target_path = os.path.join(SESSION_DIR, f"{user_id}.json")
                if os.path.exists(source_path):
                    try:
                        shutil.copyfile(source_path, target_path)
                        state = load_session(user_id)
                        summary = format_state_summary(state)
                        reply_msg = f"✅ 已成功載入個案「{case_name}」的資料！\n\n{summary}"
                    except Exception as e:
                        reply_msg = f"❌ 載入個案資料時發生錯誤: {str(e)}"
                else:
                    reply_msg = f"❌ 找不到個案「{case_name}」的資料檔。您可輸入「個案清單」查詢可用個案。"
        elif user_text in ["完成", "生成計畫書", "生成", "確認", "出計畫書", "產出", "產出計畫書", "直接生成", "ok", "OK", "好了", "搞定"]:
            state = load_session(user_id)
            if state.get("name") == "未提供資料":
                reply_msg = "⚠️ 尚未開始建立個案，請先輸入個案的姓名（如「個案名字是張三」）以開始建立資料！"
            else:
                try:
                    result = generate_plan(state)
                    fee_preview = result['feeStr']
                    plan_preview = result['planText']
                    download_url = f"{base_url}/download/{user_id}"
                    
                    plan_intro = plan_preview[:800] + "\n...（完整內容請下載 Word 檔）" if len(plan_preview) > 800 else plan_preview
                    reply_msg = (
                        f"{fee_preview}\n\n"
                        "====================\n"
                        f"📄 計畫書預覽（前段）：\n{plan_intro}\n"
                        "====================\n"
                        f"⬇️ 點此下載完整 Word 檔：\n{download_url}"
                    )
                except Exception as e:
                    logger.error(f"Error generating plan: {e}")
                    reply_msg = f"生成計畫書時發生錯誤：{str(e)}\n請確認個案資料是否完整，或輸入「重新開始」重試。"
        elif any(user_text.lower().startswith(prefix) for prefix in [
            "待辦事項：", "待辦事項:", "待辦事項 ",
            "新增待辦：", "新增待辦:", "新增待辦 ",
            "待辦：", "待辦:", "待辦 ",
            "代辦事項：", "代辦事項:", "代辦事項 ",
            "新增代辦：", "新增代辦:", "新增代辦 ",
            "代辦：", "代辦:", "代辦 ",
            "todo:", "todo：", "todo "
        ]):
            import re
            
            # Find the matching prefix to extract content
            todo_title = ""
            for prefix in [
                "待辦事項：", "待辦事項:", "待辦事項 ",
                "新增待辦：", "新增待辦:", "新增待辦 ",
                "待辦：", "待辦:", "待辦 ",
                "代辦事項：", "代辦事項:", "代辦事項 ",
                "新增代辦：", "新增代辦:", "新增代辦 ",
                "代辦：", "代辦:", "代辦 ",
                "todo:", "todo：", "todo "
            ]:
                if user_text.lower().startswith(prefix):
                    todo_title = user_text[len(prefix):].strip()
                    break
            
            if not todo_title:
                reply_msg = "⚠️ 請提供待辦事項的內容！\n例如：\n• 待辦：下午兩點與陳照專開會\n• todo: 買感冒藥"
            else:
                try:
                    priority = 'medium'
                    # Check for priority prefixes
                    if todo_title.startswith("高：") or todo_title.startswith("高:") or todo_title.lower().startswith("high:") or todo_title.lower().startswith("high："):
                        priority = 'high'
                        for p_prefix in ["高：", "高:", "high:", "high："]:
                            if todo_title.lower().startswith(p_prefix):
                                todo_title = todo_title[len(p_prefix):].strip()
                                break
                    elif todo_title.startswith("低：") or todo_title.startswith("低:") or todo_title.lower().startswith("low:") or todo_title.lower().startswith("low："):
                        priority = 'low'
                        for p_prefix in ["低：", "低:", "low:", "low："]:
                            if todo_title.lower().startswith(p_prefix):
                                todo_title = todo_title[len(p_prefix):].strip()
                                break
                    elif todo_title.startswith("中：") or todo_title.startswith("中:") or todo_title.lower().startswith("medium:") or todo_title.lower().startswith("medium："):
                        priority = 'medium'
                        for p_prefix in ["中：", "中:", "medium:", "medium："]:
                            if todo_title.lower().startswith(p_prefix):
                                todo_title = todo_title[len(p_prefix):].strip()
                                break
                    
                    # Parse due date
                    due_date = None
                    # Calculate local date/time (Asia/Taipei UTC+8)
                    local_now = datetime.utcnow() + timedelta(hours=8)
                    
                    if "明天" in todo_title:
                        due_date = (local_now + timedelta(days=1)).strftime("%Y-%m-%d")
                        todo_title = todo_title.replace("明天", "").strip()
                    elif "後天" in todo_title:
                        due_date = (local_now + timedelta(days=2)).strftime("%Y-%m-%d")
                        todo_title = todo_title.replace("後天", "").strip()
                    elif "今天" in todo_title:
                        due_date = local_now.strftime("%Y-%m-%d")
                        todo_title = todo_title.replace("今天", "").strip()
                    
                    if not due_date:
                        # Match YYYY-MM-DD or YYYY/MM/DD
                        full_date_match = re.search(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b', todo_title)
                        if full_date_match:
                            year = int(full_date_match.group(1))
                            month = int(full_date_match.group(2))
                            day = int(full_date_match.group(3))
                            due_date = f"{year:04d}-{month:02d}-{day:02d}"
                            todo_title = todo_title.replace(full_date_match.group(0), "").strip()
                        else:
                            # Match MM-DD or MM/DD (e.g. 6/30 or 06-30)
                            short_date_match = re.search(r'\b(\d{1,2})[-/](\d{1,2})\b', todo_title)
                            if short_date_match:
                                year = local_now.year
                                month = int(short_date_match.group(1))
                                day = int(short_date_match.group(2))
                                due_date = f"{year:04d}-{month:02d}-{day:02d}"
                                todo_title = todo_title.replace(short_date_match.group(0), "").strip()
                    
                    # Clean up trailing/leading helper words, colons, spaces, and punctuation
                    todo_title = re.sub(r'\b(期限|截止)[:：]?\s*$', '', todo_title).strip()
                    todo_title = re.sub(r'^(期限|截止)[:：]?\s*', '', todo_title).strip()
                    todo_title = todo_title.strip(" :：,-_")
                    
                    # If cleaning made it empty, use a default title
                    if not todo_title:
                        todo_title = "未命名任務"
                    
                    # Add to sqlite database
                    todo_id = database.add_todo(todo_title, priority, due_date)
                    
                    priority_zh = {"high": "高", "medium": "中", "low": "低"}.get(priority, "中")
                    date_info = f"\n• 截止日期：{due_date}" if due_date else ""
                    reply_msg = (
                        f"✅ 已成功新增待辦事項：\n"
                        f"• 內容：「{todo_title}」\n"
                        f"• 優先度：{priority_zh}{date_info}"
                    )
                except Exception as e:
                    logger.error(f"Error adding todo from LINE: {e}")
                    reply_msg = f"❌ 新增待辦事項時發生錯誤：{str(e)}"
        else:
            if not gemini_api_key:
                reply_msg = "系統錯誤：未設定 GEMINI_API_KEY，請在網頁設定面板中貼上您的金鑰。"
            else:
                reply_msg = process_chat(user_id, user_text, gemini_api_key)
                
        # Send reply message chunked if > 5000 chars
        try:
            messages_to_send = []
            if len(reply_msg) > 5000:
                for i in range(0, len(reply_msg), 4500):
                    messages_to_send.append(TextMessage(text=reply_msg[i:i+4500]))
            else:
                messages_to_send.append(TextMessage(text=reply_msg))
                
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=messages_to_send[:5]
                    )
                )
        except Exception as se:
            logger.error(f"Error sending Line message: {se}")

    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        logger.warning("Invalid Line webhook signature.")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error handling webhook events: {e}")
        return {"status": "error", "details": str(e)}
        
    return {"status": "ok"}

# --- STATIC FILE ROUTING ---

@app.get("/")
def get_index():
    return FileResponse("static/index.html")

@app.get("/styles.css")
def get_css():
    return FileResponse("static/styles.css")

@app.get("/app.js")
def get_js():
    return FileResponse("static/app.js")

# Mount any other static files at /static
app.mount("/static", StaticFiles(directory="static"), name="static")
