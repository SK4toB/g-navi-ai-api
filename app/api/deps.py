# app/api/deps.py
"""
* @className : API Dependencies
* @description : API 의존성 모듈
*                FastAPI 의존성 주입을 관리하는 모듈입니다.
*                서비스 인스턴스와 공통 의존성을 제공합니다.
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see FastAPI, Depends
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
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