import hmac
import hashlib
import base64
import json
import requests
import logging

logger = logging.getLogger("line_bot")

def verify_signature(body: bytes, channel_secret: str, signature: str) -> bool:
    """
    Verify that the webhook request came from Line.
    """
    if not channel_secret or not signature:
        return False
    
    hash_val = hmac.new(
        channel_secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    
    calculated_signature = base64.b64encode(hash_val).decode('utf-8')
    return hmac.compare_digest(calculated_signature, signature)

def send_line_reply(reply_token: str, text: str, channel_access_token: str) -> bool:
    """
    Send a reply message back to the user via Line Messaging API.
    """
    if not channel_access_token or not reply_token:
        return False
        
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Line reply error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Line reply network exception: {e}")
        return False
