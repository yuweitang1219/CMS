#!/usr/bin/env python3
"""
長照個案管理智能助理 - 純原生桌面 App 啟動器 & Cloudflare 隧道 (無 Render/0延遲)
Pure Native Desktop App & Cloudflare Tunnel Manager
"""

import sys
import os
import time
import socket
import re
import threading
import subprocess
import webbrowser

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    venv_python = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
else:
    venv_python = os.path.join(PROJECT_ROOT, ".venv", "bin", "python3")

if os.path.exists(venv_python) and "VIRTUAL_ENV" not in os.environ:
    os.environ["VIRTUAL_ENV"] = os.path.dirname(os.path.dirname(venv_python))
    if sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)

def is_server_healthy(host="127.0.0.1", port=8000):
    import urllib.request
    try:
        req = urllib.request.Request(f"http://{host}:{port}/api/calendar/events", headers={'User-Agent': 'HealthCheck'})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def kill_stale_port_process(port=8000):
    try:
        if sys.platform == "win32":
            subprocess.run(f"for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{port}') do taskkill /f /pid %a", shell=True, capture_output=True)
        else:
            pids = subprocess.check_output(["lsof", "-t", "-i", f":{port}"]).decode().strip().split()
            for pid in pids:
                if pid:
                    subprocess.run(["kill", "-9", pid], capture_output=True)
    except Exception as e:
        pass

def start_cloudflare_tunnel():
    cloudflared_bin = "/opt/homebrew/bin/cloudflared"
    if not os.path.exists(cloudflared_bin):
        cloudflared_bin = "cloudflared"
        
    try:
        proc = subprocess.Popen(
            [cloudflared_bin, "tunnel", "--url", "http://127.0.0.1:8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        tunnel_url = None
        for line in proc.stdout:
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                tunnel_url = match.group(0)
                print(f"\n✨ 【Cloudflare 直連通道已建立】 (廢除 Render / 0 秒延遲！)")
                print(f"👉 平板專用 App 網址: {tunnel_url}/tablet")
                print(f"👉 LINE 機器人直連網址: {tunnel_url}/api/line/webhook\n")
                
                # Save to database
                try:
                    import database
                    database.set_setting("public_tunnel_url", tunnel_url)
                except Exception:
                    pass
                break
    except Exception as e:
        print(f"Cloudflare Tunnel 啟動提示: {e}")

def ensure_dependencies():
    missing = []
    for mod, pip_name in [("fastapi", "fastapi"), ("uvicorn", "uvicorn"), ("requests", "requests")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pip_name)
    if missing:
        print(f"📦 偵測到缺少必要套件: {missing}，正在自動下載安裝，請稍候...")
        req_file = os.path.join(PROJECT_ROOT, "requirements.txt")
        if os.path.exists(req_file):
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file])
        else:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing)

def main():
    import multiprocessing
    multiprocessing.freeze_support()

    print("==========================================================")
    print("🚀 正在啟動 長照個案管理智能助理 (純 App 模式)...")
    print("==========================================================")
    
    # 確保核心套件齊全
    ensure_dependencies()
    
    url = "http://127.0.0.1:8000"
    
    # 1. 整理 Port 8000 環境並啟動最新後端伺服器引擎
    print("⏳ 正在整理 Port 8000 環境並啟動最新後端伺服器引擎...")
    kill_stale_port_process(8000)
    time.sleep(0.5)
    
    server_error = []
    def run_server():
        try:
            import uvicorn
            import main as app_module
            uvicorn.run(app_module.app, host="0.0.0.0", port=8000, log_level="error")
        except Exception as e:
            server_error.append(str(e))
            print(f"❌ Uvicorn 伺服器啟動失敗: {e}")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    server_ok = False
    for _ in range(60):
        if is_server_healthy("127.0.0.1", 8000):
            server_ok = True
            break
        time.sleep(0.2)
        
    if not server_ok:
        print("\n⚠️ 伺服器啟動檢測超時，請檢查上述錯誤訊息。")
        if server_error:
            print(f"詳細錯誤: {server_error[0]}")
    else:
        print("✅ 後端伺服器引擎啟動成功！ (http://127.0.0.1:8000)")
            
    # 2. 背景啟動 Cloudflare Tunnel 直連通道 (廢除 Render / 免費 0 延遲)
    tunnel_thread = threading.Thread(target=start_cloudflare_tunnel, daemon=True)
    tunnel_thread.start()

    # 3. 開啟純原生視窗 (PyWebView WebKit / Cocoa Window)
    try:
        import webview
        print("💡 載入純 App 原生視窗...")
        webview.create_window(
            title="長照個案管理智能助理",
            url=url,
            width=1400,
            height=900,
            resizable=True,
            text_select=True
        )
        webview.start()
    except Exception as e:
        print(f"純 App 視窗開啟提示: {e}")
        import webbrowser
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
