#!/bin/bash

# Exit on any error
set -e

echo "=== 正在啟動個人智能生活儀表板 ==="

# 1. 檢查並建立 Python 虛擬環境
if [ ! -d ".venv" ]; then
    echo "正在建立 Python 虛擬環境 (.venv)..."
    python3 -m venv .venv
fi

# 2. 啟用虛擬環境
source .venv/bin/activate

# 3. 安裝/更新依賴套件
echo "正在安裝/更新 Python 依賴套件..."
pip install -U pip
pip install -r requirements.txt

# 4. 偵測本機區域網路 IP
echo "正在偵測本機區域網路 IP..."
LOCAL_IP=$(python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    s.close()
    print(ip)
except Exception:
    print('127.0.0.1')
")

# 5. 提示使用者連線資訊
echo ""
echo "=========================================================="
echo "🎉 伺服器設定完成，即將啟動！"
echo ""
echo "💻 本機端網址：http://localhost:8000"
echo "📱 區域網路網址 (同 Wi-Fi 下手機可連)：http://$LOCAL_IP:8000"
echo ""

# 6. 偵測 ngrok 提供外網存取建議
if command -v ngrok &> /dev/null; then
    echo "🔍 偵測到本機已安裝 ngrok！"
    echo "🌐 若要開啟外網存取，您可以在啟動後，於另一個終端機視窗執行："
    echo "   👉 ngrok http 8000"
    echo "   這會產生一個公網的 HTTPS 網址，您就可以跨網存取，並且將該網址"
    echo "   設定為 LINE Webhook 網址！"
else
    echo "🌐 跨外網存取提示："
    echo "   本伺服器已支援 LINE Webhook 及外網連線。"
    echo "   若要開啟外網存取，建議安裝 ngrok (https://ngrok.com) 或 Cloudflare Tunnel (cloudflared)"
    echo "   並將對外的 HTTPS 網址設定在系統設定面板中。"
fi
echo "=========================================================="
echo ""

# 7. 啟動 Uvicorn 伺服器 (綁定 0.0.0.0 以供區域網路其他裝置連線)
# 檢查 Port 8000 是否被舊程式佔用，如果是則自動清除，以載入最新程式碼
PORT_PID=$(lsof -t -i :8000 || true)
if [ ! -z "$PORT_PID" ]; then
    echo "⚠️ 偵測到 Port 8000 已被舊程式 (PID: $PORT_PID) 佔用，正在自動關閉並載入新版程式碼..."
    kill -9 $PORT_PID || true
    sleep 1.5
fi

echo "正在啟動 Web 伺服器..."
uvicorn main:app --host 0.0.0.0 --port 8000
