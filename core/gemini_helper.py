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

def generate_content_with_rotation(api_key_str, model_name, prompt):
    """
    Call Gemini API with automatic rotation of API keys if a 429 rate limit or quota error occurs.
    """
    keys = get_api_key_list(api_key_str)
    if not keys:
        raise ValueError("未設定任何 Gemini API 金鑰。")
        
    last_err = None
    for idx, key in enumerate(keys):
        # Mask key for safety in logs
        masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "Invalid Key"
        try:
            logger.info(f"嘗試使用第 {idx+1}/{len(keys)} 組 API Key ({masked_key}) 呼叫 {model_name}...")
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            # Success!
            logger.info(f"API Key ({masked_key}) 呼叫成功。")
            return response
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"API Key ({masked_key}) 呼叫失敗，錯誤資訊: {err_msg}")
            
            # Check if this is a rate limit or quota exceeded error
            # We also check for general resource exhausted (429) errors
            if "429" in err_msg or "Quota" in err_msg or "quota" in err_msg or "ResourceExhausted" in err_msg or "limit" in err_msg:
                logger.warning(f"API Key ({masked_key}) 超過配額/頻率限制 (429)，將自動輪替至下一組金鑰。")
                last_err = e
                continue
            else:
                # For other errors (e.g. invalid key, authentication error), we also try the next key
                last_err = e
                continue
                
    # If we reached here, all keys failed
    logger.error("所有已設定的 Gemini API 金鑰均呼叫失敗！")
    raise last_err
