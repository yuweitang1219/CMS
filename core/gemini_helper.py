import logging
import google.generativeai as genai

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

def generate_content_with_rotation(api_key_str, model_name, prompt):
    """
    Call Gemini API with automatic rotation of API keys if a 429 rate limit or quota error occurs.
    Persists the last successful key index in the database to prevent latency from retrying dead keys sequentially across server restarts.
    """
    import database
    keys = get_api_key_list(api_key_str)
    if not keys:
        raise ValueError("未設定任何 Gemini API 金鑰。")
        
    num_keys = len(keys)
    
    # Load persistent active key index from database
    try:
        active_idx = int(database.get_setting("active_gemini_key_index", 0))
    except Exception:
        active_idx = 0
        
    if active_idx >= num_keys:
        active_idx = 0
        
    start_idx = active_idx
    last_err = None
    # Try up to num_keys times, starting from the persistent active index
    for attempt in range(num_keys):
        idx = (start_idx + attempt) % num_keys
        key = keys[idx]
        masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "Invalid Key"
        try:
            logger.info(f"嘗試使用第 {idx+1}/{num_keys} 組 API Key ({masked_key}) 呼叫 {model_name}...")
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # Success! Save this working key index to database if it changed
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
            
            # Rotate active index to the next one to skip this failed key in future calls
            next_idx = (idx + 1) % num_keys
            try:
                database.set_setting("active_gemini_key_index", next_idx)
            except Exception:
                pass
            last_err = e
            
    logger.error("所有已設定的 Gemini API 金鑰均呼叫失敗！")
    raise last_err
