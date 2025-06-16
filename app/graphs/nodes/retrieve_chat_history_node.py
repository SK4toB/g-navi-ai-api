# G.Navi 1단계: 대화이력 검색

from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """G.Navi 1단계: 대화이력 검색"""
    print("=== G.Navi 1단계: 대화이력 검색 ===")
    
    # TODO: 대화이력 검색 로직 구현
    state["chat_history_results"] = []
    
    return state