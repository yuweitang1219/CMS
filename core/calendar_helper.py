import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_oauth_service(calendar_id):
    import database
    from datetime import datetime, timezone
    import requests
    from google.oauth2.credentials import Credentials
    
    client_id = database.get_setting("google_client_id")
    client_secret = database.get_setting("google_client_secret")
    refresh_token = database.get_setting("google_refresh_token")
    access_token = database.get_setting("google_access_token")
    expiry_str = database.get_setting("google_token_expiry")
    
    if not client_id or not client_secret or not refresh_token:
        return None
        
    is_expired = True
    if expiry_str:
        try:
            expiry = float(expiry_str)
            # Add 60s buffer
            if expiry > datetime.now(timezone.utc).timestamp() + 60:
                is_expired = False
        except ValueError:
            pass
            
    if is_expired:
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
                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                new_expiry = datetime.now(timezone.utc).timestamp() + expires_in
                database.set_setting("google_access_token", access_token)
                database.set_setting("google_token_expiry", str(new_expiry))
                if data.get("refresh_token"):
                    database.set_setting("google_refresh_token", data.get("refresh_token"))
            else:
                return None
        except Exception:
            return None
            
    try:
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building OAuth service: {e}")
        return None

def get_travel_time(start_addr, end_addr):
    if not start_addr or not end_addr:
        return None
    import requests
    import urllib.parse
    try:
        headers = {'User-Agent': 'CarePlan-Dashboard/1.0 (contact: yuwei@example.com)'}
        url_start = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(start_addr)}&format=json&limit=1"
        res_start = requests.get(url_start, headers=headers, timeout=5).json()
        if not res_start:
            return None
        lat_start, lon_start = res_start[0]['lat'], res_start[0]['lon']
        
        url_end = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(end_addr)}&format=json&limit=1"
        res_end = requests.get(url_end, headers=headers, timeout=5).json()
        if not res_end:
            return None
        lat_end, lon_end = res_end[0]['lat'], res_end[0]['lon']
        
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{lon_start},{lat_start};{lon_end},{lat_end}?overview=false"
        res_route = requests.get(osrm_url, timeout=5).json()
        if res_route.get("code") == "Ok" and res_route.get("routes"):
            duration_sec = res_route["routes"][0]["duration"]
            duration_min = round(duration_sec / 60)
            distance_km = round(res_route["routes"][0]["distance"] / 1000, 1)
            return {"minutes": duration_min, "distance": distance_km}
    except Exception as e:
        print(f"Error calculating travel time: {e}")
    return None

def get_travel_time_coords(lat_start, lon_start, end_addr):
    if not lat_start or not lon_start or not end_addr:
        return None
    import requests
    import urllib.parse
    try:
        headers = {'User-Agent': 'CarePlan-Dashboard/1.0 (contact: yuwei@example.com)'}
        url_end = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(end_addr)}&format=json&limit=1"
        res_end = requests.get(url_end, headers=headers, timeout=5).json()
        if not res_end:
            return None
        lat_end, lon_end = res_end[0]['lat'], res_end[0]['lon']
        
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{lon_start},{lat_start};{lon_end},{lat_end}?overview=false"
        res_route = requests.get(osrm_url, timeout=5).json()
        if res_route.get("code") == "Ok" and res_route.get("routes"):
            duration_sec = res_route["routes"][0]["duration"]
            duration_min = round(duration_sec / 60)
            distance_km = round(res_route["routes"][0]["distance"] / 1000, 1)
            return {"minutes": duration_min, "distance": distance_km}
    except Exception as e:
        print(f"Error calculating travel time from coordinates: {e}")
    return None

def sync_to_calendar(state, override_start_address=None, override_source_name=None):
    """
    Syncs the case visit date to Google Calendar.
    Tries Google OAuth first, then falls back to GOOGLE_SERVICE_ACCOUNT_JSON.
    """
    import database
    oauth_calendar_id = database.get_setting("google_calendar_id", "primary")
    service = get_oauth_service(oauth_calendar_id)
    
    if service:
        calendar_id = oauth_calendar_id
    else:
        service_account_json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
    
        if not service_account_json_str:
            print("Warning: Google Calendar OAuth not configured and service account JSON not found. Calendar sync skipped.")
            return {"success": False, "error": "No calendar credentials configured"}
    
        try:
            service_account_info = json.loads(service_account_json_str)
            SCOPES = ['https://www.googleapis.com/auth/calendar.events']
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
            service = build('calendar', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error authenticating with Service Account: {e}")
            return {"success": False, "error": f"Auth failed: {str(e)}"}
            
    visit_date = state.get("visitDate")
    if not visit_date:
        print("Warning: No visitDate found in state. Calendar sync skipped.")
        return {"success": False, "error": "Missing visitDate"}
        
    # Format fields
    name = state.get("name", "未提供資料")
    cms_lvl = state.get("cmsLvl", "未提供")
    
    plan_type_map = {
        "AA01": "AA01家訪擬定照顧計畫",
        "ReEval": "單位複評計畫擬定",
        "CoVisit": "共訪",
        "NewCase": "新案",
        "PreNewCase": "出準新案",
        "PlanChange": "計畫異動",
        "Private": "私人行程"
    }
    plan_type = state.get("planType", "AA01")
    plan_type_name = plan_type_map.get(plan_type, plan_type)
    
    conds = "、".join(state.get("selectedConditions", [])) or "無明顯疾病"
    
    services = []
    active_services = state.get("activeServices", [])
    service_times = state.get("serviceTimes", {})
    for code in active_services:
        times = service_times.get(code, 1)
        services.append(f"{code}({times}次/月)")
    services_str = "、".join(services) or "尚未配置"

    # Define event start and end time dynamically
    visit_time = state.get("visitTime", "09:00")
    try:
        from datetime import datetime, timedelta
        start_dt = datetime.fromisoformat(f"{visit_date}T{visit_time}:00")
        end_dt = start_dt + timedelta(hours=1)
        start_str = start_dt.isoformat()
        end_str = end_dt.isoformat()
    except Exception as te:
        print(f"Error parsing date/time for calendar: {te}")
        start_str = f"{visit_date}T{visit_time}:00"
        try:
            h, m = map(int, visit_time.split(":"))
            end_str = f"{visit_date}T{h+1:02d}:{m:02d}:00"
        except:
            end_str = f"{visit_date}T10:00:00"
            
    # Calculate travel time if start and end addresses are configured
    address = state.get("address", "")
    event_id = state.get("googleEventId")
    
    travel_time_str = ""
    travel_info = ""
    if address:
        start_addr = None
        source_name = ""
        
        if override_start_address:
            start_addr = override_start_address
            source_name = override_source_name or "選定起點"
        else:
            # Query calendar events on the same day to find preceding events within 1.5h
            try:
                time_min = f"{visit_date}T00:00:00Z"
                time_max = f"{visit_date}T23:59:59Z"
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                events = events_result.get('items', [])
                
                closest_event = None
                min_diff = None
                current_dt = start_dt.replace(tzinfo=None) if hasattr(start_dt, 'tzinfo') else start_dt
                
                for ev in events:
                    if ev.get("id") == event_id:
                        continue
                    ev_start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
                    if not ev_start:
                        continue
                    try:
                        if ev_start.endswith("Z"):
                            ev_dt = datetime.fromisoformat(ev_start[:-1])
                        else:
                            ev_dt = datetime.fromisoformat(ev_start)
                        ev_dt = ev_dt.replace(tzinfo=None)
                        
                        # Diff in seconds (current start - preceding start)
                        diff_sec = (current_dt - ev_dt).total_seconds()
                        if 0 <= diff_sec <= 90 * 60:  # Within 90 minutes (1.5 hours)
                            if min_diff is None or diff_sec < min_diff:
                                min_diff = diff_sec
                                closest_event = ev
                    except Exception as pe:
                        print(f"Error parsing event time during preceding search: {pe}")
                
                if closest_event and closest_event.get("location"):
                    start_addr = closest_event.get("location")
                    closest_summary = closest_event.get("summary", "")
                    if closest_summary:
                        parts = closest_summary.strip().split()
                        if len(parts) >= 2 and not closest_summary.startswith("📋"):
                            source_name = f"個案「{parts[0]}」家"
                        elif "家訪：" in closest_summary:
                            source_name = f"個案「{closest_summary.split('家訪：')[1].split(' ')[0].split('(')[0]}」家"
                        elif "家訪:" in closest_summary:
                            source_name = f"個案「{closest_summary.split('家訪:')[1].split(' ')[0].split('(')[0]}」家"
                        else:
                            source_name = f"「{closest_summary}」"
                    else:
                        source_name = "前置行程"
            except Exception as se:
                print(f"Error listing calendar events for travel calculation: {se}")
                
            if not start_addr:
                start_addr = database.get_setting("google_starting_address", "")
                source_name = "服務起點"
                
        if start_addr:
            travel_res = get_travel_time(start_addr, address)
            if travel_res:
                min_val = travel_res["minutes"]
                km_val = travel_res["distance"]
                travel_info = f"\n🚗 預估交通車程：約 {min_val} 分鐘 (距離 {km_val} 公里，自{source_name}出發)\n"
                travel_time_str = f"約 {min_val} 分鐘 (自{source_name}出發)"

    # Define summary and description based on planType
    brief_type_map = {
        "AA01": "AA01",
        "ReEval": "複評",
        "CoVisit": "共訪",
        "NewCase": "新案",
        "PreNewCase": "準新案",
        "PlanChange": "異動",
        "Private": "私人"
    }
    brief_type = brief_type_map.get(plan_type, plan_type)

    if plan_type == "Private":
        loc_str = f" ({address})" if address else ""
        summary = f"私人 {name}{loc_str}"
        description = f"私人行程/會議：{name}\n地點：{address or '無'}\n\n此活動由長照 CarePlan LINE 機器人自動同步。"
    else:
        summary = f"{name} {brief_type}"
        description = (
            f"長照照顧計畫家訪排程：\n"
            f"- 個案姓名：{name}\n"
            f"- 計畫類型：{plan_type_name}\n"
            f"- CMS 等級：{cms_lvl} 級\n"
            f"- 疾病史：{conds}\n"
            f"- 配置服務：{services_str}\n"
        )
        if travel_info:
            description += travel_info
        description += f"\n此活動由長照 CarePlan LINE 機器人自動同步。"

    event_body = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_str,
            'timeZone': 'Asia/Taipei',
        },
        'end': {
            'dateTime': end_str,
            'timeZone': 'Asia/Taipei',
        },
        'reminders': {
            'useDefault': True,
        },
    }
    
    if address:
        event_body['location'] = address

    try:
        if event_id:
            try:
                event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()
                print(f"Event updated successfully: {event.get('htmlLink')}")
            except Exception as ue:
                # If update fails (e.g. event was deleted on Google Calendar), recreate it
                print(f"Update failed ({ue}), creating new event instead...")
                event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        else:
            event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
            print(f"Event created successfully: {event.get('htmlLink')}")
            
        event_link = event.get('htmlLink')
        new_event_id = event.get('id')
        return {"success": True, "link": event_link, "event_id": new_event_id, "travel_time": travel_time_str}
    except Exception as e:
        print(f"Error syncing Google Calendar event: {e}")
        return {"success": False, "error": f"API sync failed: {str(e)}"}
