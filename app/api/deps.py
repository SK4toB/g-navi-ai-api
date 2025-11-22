# app/api/deps.py
"""
* @className : API Dependencies
* @description : API 의존성 모듈
*                FastAPI 의존성 주입을 관리하는 모듈입니다.
*                서비스 인스턴스와 공통 의존성을 제공합니다.
"""

# app/api/deps.py
# 
# 이 파일은 하위 호환성을 위해 유지


from app.core.dependencies import get_chat_service, get_history_manager

# 하위 호환성을 위한 re-export
__all__ = ["get_chat_service", "get_history_manager"]

def common_parameters():
    """공통 파라미터들"""
    pass