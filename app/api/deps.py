# 의존성 주입 (DEPRECATED - app/core/dependencies.py 사용)

# app/api/deps.py
# 
# 이 파일은 하위 호환성을 위해 유지


from app.core.dependencies import get_chat_service, get_history_manager

# 하위 호환성을 위한 re-export
__all__ = ["get_chat_service", "get_history_manager"]

def common_parameters():
    """공통 파라미터들"""
    pass