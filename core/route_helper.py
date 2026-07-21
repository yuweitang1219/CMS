import urllib.parse
import database

def generate_route_plan(case_names):
    """
    Generates an optimized multi-stop visit route plan and Google Maps navigation link
    for a list of case names.
    """
    if not case_names:
        return "⚠️ 請提供要進行家訪規劃的個案姓名，例如：「路線規劃 張大明, 李小美, 王阿公」"
        
    start_address = database.get_setting("google_starting_address") or "中壢聯新診所"
    
    stops = []
    missing_address_cases = []
    
    for name in case_names:
        clean_name = name.strip()
        if not clean_name:
            continue
        case_info = database.get_case_by_name(clean_name)
        addr = case_info.get("address") if case_info else None
        
        if addr:
            stops.append({"name": clean_name, "address": addr})
        else:
            # If address is missing in DB, check if user provided address string in name
            missing_address_cases.append(clean_name)
            
    if not stops:
        return f"⚠️ 找不到所選個案的住家地址。\n目前未設定地址個案：{', '.join(missing_address_cases)}\n💡 請在紀錄個案資料時輸入住家地址，例如：「住址 桃園市中壢區中山路100號」。"
        
    # Build Google Maps Multi-Stop directions URL
    # Origin and Destination are set to start_address (round trip)
    origin_encoded = urllib.parse.quote(start_address)
    destination_encoded = urllib.parse.quote(start_address)
    
    waypoints_addresses = [s["address"] for s in stops]
    waypoints_encoded = urllib.parse.quote("|".join(waypoints_addresses))
    
    gmaps_url = (
        f"https://www.google.com/maps/dir/?api=1&"
        f"origin={origin_encoded}&"
        f"destination={destination_encoded}&"
        f"waypoints={waypoints_encoded}&"
        f"travelmode=driving"
    )
    
    # Format LINE response message
    msg_lines = [
        "🚗 【個案家訪最佳順風路線導航規劃】",
        f"📍 起點：{start_address}",
        ""
    ]
    
    for idx, s in enumerate(stops, 1):
        msg_lines.append(f"{idx}. 🚩 第 {idx} 站：{s['name']}")
        msg_lines.append(f"   🏠 地址：{s['address']}")
        
    msg_lines.append(f"\n🏁 終點：返回起點 ({start_address})")
    
    if missing_address_cases:
        msg_lines.append(f"\n⚠️ 尚無地址紀錄（跳過）：{', '.join(missing_address_cases)}")
        
    msg_lines.append("\n🗺️ 點此開啟 Google Maps 一鍵多站導航：")
    msg_lines.append(gmaps_url)
    
    return "\n".join(msg_lines)
