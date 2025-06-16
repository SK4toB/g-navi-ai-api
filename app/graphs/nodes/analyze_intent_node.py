# G.Navi 2단계: 의도 분석

from app.graphs.state import ChatState

async def process(state: ChatState) -> ChatState:
    """G.Navi 2단계: 의도 분석"""
    print("=== G.Navi 2단계: 의도 분석 ===")
    
    # TODO: 의도 분석 로직 구현
    state["intent_analysis"] = {}
    
    return state