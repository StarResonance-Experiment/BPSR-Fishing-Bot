import time

_log_callback = None

def set_log_callback(callback):
    global _log_callback
    _log_callback = callback

def log(message):
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    if _log_callback:
        try:
            _log_callback(formatted)
        except Exception:
            pass