import logging
try:
    import google.generativeai as genai
except Exception:
    genai = None

logger = logging.getLogger("app.gemini_helper")

def get_api_key_list(api_key_str):
    """
    Parse a comma-separated or semicolon-separated string of API keys.
    """
    if not api_key_str:
        return []
    keys = []
    for k in api_key_str.replace(";", ",").split(","):
        k_stripped = k.strip()
        if k_stripped:
            keys.append(k_stripped)
    return keys

_active_key_index = 0  # Global cache to remember the last successful key index

def generate_content_with_rotation(api_key_str, model_name, prompt, generation_config=None):
    """
    Call Gemini API with automatic rotation of API keys if a 429 rate limit or quota error occurs.
    Includes 1.5s automatic retry backoff on 429 rate limits.
    """
    import database
    import time
    keys = get_api_key_list(api_key_str)
    if not keys:
        raise ValueError("未設定任何 Gemini API 金鑰。")
        
    num_keys = len(keys)
    
    try:
        active_idx = int(database.get_setting("active_gemini_key_index", 0))
    except Exception:
        active_idx = 0
        
    if active_idx >= num_keys:
        active_idx = 0
        
    start_idx = active_idx
    last_err = None
    
    max_attempts = max(num_keys * 2, 4)
    for attempt in range(max_attempts):
        idx = (start_idx + attempt) % num_keys
        key = keys[idx]
        masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "Invalid Key"
        try:
            logger.info(f"嘗試使用第 {idx+1}/{num_keys} 組 API Key ({masked_key}) 呼叫 {model_name} (嘗試 {attempt+1}/{max_attempts})...")
            use_rest = (genai is None) or key.startswith("AQ.")
            try:
                if use_rest:
                    raise ImportError("Bypass SDK for AQ key or missing genai")
                genai.configure(api_key=key)
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config
                )
                response = model.generate_content(prompt)
            except Exception as sdk_err:
                sdk_err_msg = str(sdk_err)
                # Fallback to direct REST API with x-goog-api-key header
                if use_rest or "401" in sdk_err_msg or "ACCESS_TOKEN_TYPE" in sdk_err_msg or "API_KEY" in sdk_err_msg or key.startswith("AQ."):
                    import urllib.request
                    import json
                    rest_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                    headers = {
                        "Content-Type": "application/json",
                        "x-goog-api-key": key
                    }
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}]
                    }
                    if generation_config:
                        cfg = {}
                        if "temperature" in generation_config:
                            cfg["temperature"] = generation_config["temperature"]
                        if "max_output_tokens" in generation_config:
                            cfg["maxOutputTokens"] = generation_config["max_output_tokens"]
                        elif "maxOutputTokens" in generation_config:
                            cfg["maxOutputTokens"] = generation_config["maxOutputTokens"]
                        # Disable thinking process token consumption for JSON extraction to ensure speed and completeness
                        cfg["thinkingConfig"] = {"thinkingBudget": 0}
                        if cfg:
                            payload["generationConfig"] = cfg
                            
                    req = urllib.request.Request(
                        rest_url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers=headers,
                        method="POST"
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=30) as http_res:
                            res_data = json.loads(http_res.read().decode("utf-8"))
                            class RestResponseWrapper:
                                def __init__(self, data):
                                    self.data = data
                                    self.text = ""
                                    try:
                                        candidates = data.get("candidates", [])
                                        if candidates:
                                            parts = candidates[0].get("content", {}).get("parts", [])
                                            # Filter out thoughts if thinking model is enabled
                                            text_parts = [p.get("text", "") for p in parts if not p.get("thought")]
                                            if not text_parts:
                                                text_parts = [p.get("text", "") for p in parts]
                                            self.text = "".join(text_parts)
                                    except Exception:
                                        pass
                            response = RestResponseWrapper(res_data)
                    except urllib.error.HTTPError as he:
                        err_body = he.read().decode('utf-8', errors='ignore')
                        raise RuntimeError(f"REST API 呼叫失敗 ({he.code}): {err_body}")
                    except Exception as req_err:
                        raise RuntimeError(f"REST API 連線失敗: {req_err}")
                else:
                    raise sdk_err
            
            if idx != active_idx:
                try:
                    database.set_setting("active_gemini_key_index", idx)
                    logger.info(f"已更新持久化 API 金鑰索引至: {idx}")
                except Exception as dbe:
                    logger.warning(f"無法寫入 API 金鑰索引至資料庫: {dbe}")
            
            logger.info(f"API Key ({masked_key}) 呼叫成功。")
            return response
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"API Key ({masked_key}) 呼叫失敗，錯誤資訊: {err_msg}")
            last_err = e
            
            # If invalid API key format or unauthorized
            if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg or "API_KEY" in err_msg:
                logger.warning(f"API 金鑰無效或權限不足: {masked_key}")
                
            # If 404 / 503 (model temporarily high demand or unavailable), break key loop to let caller switch to next model immediately
            if "503" in err_msg or "high demand" in err_msg.lower() or "404" in err_msg or "not found" in err_msg.lower():
                raise e

            # If 429 / Rate limit, backoff before next retry
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Quota" in err_msg:
                sleep_sec = 2.0 if num_keys == 1 else 1.0
                time.sleep(sleep_sec)
            
            # If 404 / not found / model not supported on this endpoint, try other keys first, but record it
            next_idx = (idx + 1) % num_keys
            try:
                database.set_setting("active_gemini_key_index", next_idx)
            except Exception:
                pass
            
    logger.error("所有已設定的 Gemini API 金鑰均呼叫失敗！")
    raise last_err
