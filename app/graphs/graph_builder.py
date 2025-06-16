# app/graphs/graph_builder.py
# G.Navi AgentRAG 시스템의 그래프 빌더

import json
import logging
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any, List
import os
import markdown

from app.graphs.state import ChatState
from app.graphs.nodes.retriever import CareerEnsembleRetrieverAgent as Retriever
from app.graphs.nodes.analyzer import IntentAnalysisAgent as Analyzer
from app.graphs.nodes.advisor import RecommendationAgent as Advisor
from app.graphs.nodes.formatter import ResponseFormattingAgent as Formatter


class ChatGraphBuilder:
    """
    G.Navi AgentRAG 시스템의 LangGraph 빌더
    """
    
    def __init__(self):
        print("ChatGraphBuilder 초기화 (G.Navi AgentRAG)")
        self.logger = logging.getLogger(__name__)
        self.memory_saver = MemorySaver()
        
        # 세션별 정보 저장소 추가
        self.session_store = {}  # conversation_id -> {"user_info": ..., "metadata": ...}
        
        # G.Navi 에이전트들 초기화
        self.career_retriever_agent = Retriever()
        self.intent_analysis_agent = Analyzer()
        self.recommendation_agent = Advisor()
        self.response_formatting_agent = Formatter()
    
    def _should_process_message(self, state: ChatState) -> str:
        """메시지 처리 여부 결정"""
        user_question = state.get("user_question", "")
        
        if user_question and user_question.strip():
            print(f"메시지 있음 → 처리 시작: {user_question[:30]}...")
            return "process"
        else:
            print("메시지 없음 → 대기")
            return "wait"
    
    def get_session_info(self, conversation_id: str) -> Dict[str, Any]:
        """세션 정보 조회"""
        return self.session_store.get(conversation_id, {})
    
    def get_user_info_from_session(self, state: ChatState) -> Dict[str, Any]:
        """상태에서 사용자 정보 추출 (우선순위: state > session_store)"""
        # 1. state에서 user_data 확인
        user_data = state.get("user_data", {})
        if user_data:
            return user_data
        
        # 2. session_id로 session_store에서 조회
        session_id = state.get("session_id", "")
        if session_id:
            session_info = self.get_session_info(session_id)
            return session_info.get("user_info", {})
        
        # 3. 기본값 반환
        return {}
    
    def close_session(self, conversation_id: str):
        """세션 정보 정리"""
        if conversation_id in self.session_store:
            del self.session_store[conversation_id]
            print(f"📝 GraphBuilder 세션 정보 삭제: {conversation_id}")
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """모든 세션 정보 조회 (디버깅용)"""
        return self.session_store.copy()
    
    async def build_persistent_chat_graph(self, conversation_id: str, user_info: Dict[str, Any]):
        """G.Navi AgentRAG LangGraph 빌드"""
        print(f"🔧 G.Navi AgentRAG LangGraph 빌드 시작: {conversation_id}")
        
        # 세션 정보 저장
        self.session_store[conversation_id] = {
            "user_info": user_info,
            "created_at": datetime.now(),
            "conversation_id": conversation_id
        }
        print(f"📝 세션 정보 저장 완료: {user_info.get('name', 'Unknown')} (대화방: {conversation_id})")
        
        # StateGraph 생성
        workflow = StateGraph(ChatState)
        
        # G.Navi 5단계 노드들 추가
        workflow.add_node("message_check", self._create_message_check_node())
        workflow.add_node("retrieve_chat_history", self._retrieve_chat_history_node)
        workflow.add_node("analyze_intent", self._analyze_intent_node)
        workflow.add_node("retrieve_additional_data", self._retrieve_additional_data_node)
        workflow.add_node("generate_recommendation", self._generate_recommendation_node)
        workflow.add_node("format_response", self._format_response_node)
        workflow.add_node("wait_state", self._create_wait_node())
        
        # 시작점
        workflow.set_entry_point("message_check")
        
        # 조건부 분기
        workflow.add_conditional_edges(
            "message_check",
            self._should_process_message,
            {
                "process": "retrieve_chat_history",
                "wait": "wait_state"
            }
        )
        
        # G.Navi 5단계 워크플로우
        workflow.add_edge("retrieve_chat_history", "analyze_intent")
        workflow.add_edge("analyze_intent", "retrieve_additional_data")
        workflow.add_edge("retrieve_additional_data", "generate_recommendation")
        workflow.add_edge("generate_recommendation", "format_response")
        
        # 처리 완료 후 종료
        workflow.add_edge("format_response", END)
        workflow.add_edge("wait_state", END)
        
        # 컴파일
        compiled_graph = workflow.compile(
            checkpointer=self.memory_saver
        )
        
        print(f"✅ G.Navi AgentRAG LangGraph 컴파일 완료: {conversation_id}")
        return compiled_graph
    
    def _create_message_check_node(self):
        """메시지 확인 및 상태 초기화 노드"""
        async def message_check_node(state: ChatState) -> ChatState:
            print("📝 메시지 확인 및 상태 초기화")
            
            # 상태 초기화
            state.setdefault("chat_history_results", [])
            state.setdefault("intent_analysis", {})
            state.setdefault("career_cases", [])
            state.setdefault("external_trends", [])
            state.setdefault("recommendation", {})
            state.setdefault("final_response", {})
            state.setdefault("processing_log", [])
            state.setdefault("error_messages", [])
            state.setdefault("total_processing_time", 0.0)
            
            return state
        
        return message_check_node
    
    def _retrieve_chat_history_node(self, state: ChatState) -> ChatState:
        """1단계: 과거 대화내역 검색"""
        start_time = datetime.now()
        try:
            self.logger.info("=== 1단계: 과거 대화내역 검색 ===")
            
            # 세션 정보에서 사용자 데이터 가져오기
            user_data = self.get_user_info_from_session(state)
            user_id = user_data.get("memberId") if "memberId" in user_data else user_data.get("name")
            
            if user_id:
                self.logger.info(f"사용자 {user_id}의 과거 대화내역 검색 중...")
                chat_results = self.career_retriever_agent.load_chat_history(user_id=user_id)
            else:
                self.logger.warning("사용자 ID가 없어 전체 대화내역을 로드합니다")
                chat_results = self.career_retriever_agent.load_chat_history()
            
            state["chat_history_results"] = chat_results
            state["processing_log"].append(f"과거 대화내역 검색 완료: {len(chat_results)}개 (사용자: {user_id or 'ALL'})")
            self.logger.info(f"과거 대화내역 검색 완료: {len(chat_results)}개")
            
        except Exception as e:
            error_msg = f"과거 대화내역 검색 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["chat_history_results"] = []
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"1단계 처리 시간: {processing_time:.2f}초")
        return state
    
    def _analyze_intent_node(self, state: ChatState) -> ChatState:
        """2단계: 의도 분석 및 상황 이해"""
        start_time = datetime.now()
        
        try:
            self.logger.info("=== 2단계: 의도 분석 및 상황 이해 ===")
            
            # 세션 정보에서 사용자 데이터 가져오기
            user_data = self.get_user_info_from_session(state)
            
            intent_analysis = self.intent_analysis_agent.analyze_intent_and_context(
                user_question=state.get("user_question", ""),
                user_data=user_data,
                chat_history=state.get("chat_history_results", [])
            )
            
            state["intent_analysis"] = intent_analysis
            state["processing_log"].append("의도 분석 및 상황 이해 완료")
            
            self.logger.info("의도 분석 및 상황 이해 완료")
            
        except Exception as e:
            error_msg = f"의도 분석 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["intent_analysis"] = {
                "error": str(e),
                "question_type": "professional",
                "requires_full_analysis": True,
                "simple_response": False
            }
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"2단계 처리 시간: {processing_time:.2f}초")
        
        return state
    
    def _retrieve_additional_data_node(self, state: ChatState) -> ChatState:
        """3단계: 추가 데이터 검색 (커리어 사례 + 외부 트렌드)"""
        start_time = datetime.now()
        try:
            self.logger.info("=== 3단계: 추가 데이터 검색 ===")
            
            intent_analysis = state.get("intent_analysis", {})
            user_question = state.get("user_question", "")
            
            # 커리어 히스토리 검색
            career_keywords = intent_analysis.get("career_history", [])
            if not career_keywords:
                career_keywords = [user_question]
            career_query = " ".join(career_keywords[:2])
            career_cases = self.career_retriever_agent.retrieve(career_query, k=3)
            
            # 외부 트렌드 검색
            trend_keywords = intent_analysis.get("external_trends", [])
            if not trend_keywords:
                trend_keywords = [user_question]
            external_trends = self.career_retriever_agent.search_external_trends_with_tavily(trend_keywords[:2])
            
            if len(external_trends) > 3:
                external_trends = external_trends[:3]
            
            state["career_cases"] = career_cases
            state["external_trends"] = external_trends
            state["processing_log"].append(
                f"추가 데이터 검색 완료: 커리어 사례 {len(career_cases)}개, 트렌드 정보 {len(external_trends)}개"
            )
            self.logger.info(f"커리어 사례 {len(career_cases)}개, 트렌드 정보 {len(external_trends)}개 검색 완료")
            
        except Exception as e:
            error_msg = f"추가 데이터 검색 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["career_cases"] = []
            state["external_trends"] = []
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"3단계 처리 시간: {processing_time:.2f}초")
        return state
    
    def _generate_recommendation_node(self, state: ChatState) -> ChatState:
        """4단계: 맞춤형 추천 생성"""
        start_time = datetime.now()
        
        try:
            self.logger.info("=== 4단계: 맞춤형 추천 생성 ===")
            
            # 세션 정보에서 사용자 데이터 가져오기
            user_data = self.get_user_info_from_session(state)
            
            recommendation = self.recommendation_agent.generate_personalized_recommendation(
                user_question=state.get("user_question", ""),
                user_data=user_data,
                intent_analysis=state.get("intent_analysis", {}),
                career_cases=state.get("career_cases", []),
                external_trends=state.get("external_trends", [])
            )
            
            state["recommendation"] = recommendation
            state["processing_log"].append("맞춤형 추천 생성 완료")
            
            self.logger.info("맞춤형 추천 생성 완료")
            
        except Exception as e:
            error_msg = f"추천 생성 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["recommendation"] = {"error": str(e)}
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"4단계 처리 시간: {processing_time:.2f}초")
        
        return state
    
    def _format_response_node(self, state: ChatState) -> ChatState:
        """5단계: 적응적 응답 포맷팅"""
        start_time = datetime.now()
        try:
            self.logger.info("=== 5단계: 적응적 응답 포맷팅 ===")
            
            final_response = self.response_formatting_agent.format_adaptive_response(
                user_question=state.get("user_question", ""),
                state=state
            )
            
            # HTML 변환
            final_response["html_content"] = self._convert_markdown_to_html(final_response["formatted_content"])
            self.logger.info("마크다운 HTML 변환 완료")
            
            # HTML 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # 세션 정보에서 사용자 데이터 가져오기
            user_data = self.get_user_info_from_session(state)
            user_name = user_data.get("name", "user")
            user_name = user_name.replace(" ", "_") if user_name else "user"
            file_name = f"{user_name}_{timestamp}"
            html_path = os.path.join(output_dir, f"{file_name}.html")
            
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(final_response["html_content"])
            
            final_response["html_path"] = html_path
            final_response["format_type"] = final_response.get("format_type", "adaptive")
            
            # bot_message 설정 (기본 출력 형식)
            state["final_response"] = final_response
            state["processing_log"].append(f"적응적 응답 포맷팅 완료 (유형: {final_response['format_type']})")
            
            self.logger.info(f"HTML 파일 저장 완료: {html_path}")
            self.logger.info("적응적 응답 포맷팅 완료")
            
        except Exception as e:
            error_msg = f"응답 포맷팅 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["final_response"] = {"error": str(e)}
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"5단계 처리 시간: {processing_time:.2f}초")
        
        # 총 처리 시간 계산
        total_time = sum(
            float(log.split(": ")[-1].replace("초", ""))
            for log in state.get("processing_log", [])
            if "처리 시간" in log
        )
        state["total_processing_time"] = total_time
        
        return state
    
    def _convert_markdown_to_html(self, content) -> str:
        """마크다운 콘텐츠를 HTML로 변환"""
        try:
            if isinstance(content, str):
                markdown_content = content
            elif isinstance(content, (dict, list)):
                markdown_content = self._convert_json_to_markdown(content)
            else:
                markdown_content = str(content)
            
            extensions = [
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code',
                'markdown.extensions.nl2br',
                'markdown.extensions.toc',
                'markdown.extensions.attr_list',
            ]
            
            md = markdown.Markdown(extensions=extensions)
            html_content = md.convert(markdown_content)
            
            styled_html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>G.Navi AI 커리어 컨설팅 보고서</title>
    <style>
        body {{
            font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        h1 {{
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            color: #2980b9;
        }}
        h2 {{
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 5px;
        }}
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    {html_content}
    <div class="footer">
        <p>Generated by G.Navi AI Career Consulting System</p>
        <p>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
            return styled_html
            
        except Exception as e:
            self.logger.error(f"마크다운 HTML 변환 실패: {e}")
            content_str = str(content) if not isinstance(content, str) else content
            return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>G.Navi AI 커리어 컨설팅 보고서</title>
</head>
<body>
    <h1>G.Navi AI 커리어 컨설팅 보고서</h1>
    <div style="color: #d32f2f; background: #ffebee; padding: 15px; border-radius: 5px;">
        <p>마크다운 변환 오류: {str(e)}</p>
    </div>
    <pre>{content_str}</pre>
</body>
</html>
"""
    
    def _convert_json_to_markdown(self, data) -> str:
        """JSON 데이터를 마크다운으로 변환"""
        try:
            if isinstance(data, dict):
                return self._dict_to_markdown(data)
            elif isinstance(data, list):
                return self._list_to_markdown(data)
            else:
                return str(data)
        except Exception as e:
            self.logger.error(f"JSON을 마크다운으로 변환 실패: {e}")
            return f"```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"
    
    def _dict_to_markdown(self, data: dict, level: int = 1) -> str:
        """딕셔너리를 마크다운으로 변환"""
        markdown_lines = []
        
        for key, value in data.items():
            header_prefix = "#" * min(level + 1, 6)
            
            if isinstance(value, dict):
                markdown_lines.append(f"{header_prefix} {key}")
                markdown_lines.append(self._dict_to_markdown(value, level + 1))
            elif isinstance(value, list):
                markdown_lines.append(f"{header_prefix} {key}")
                markdown_lines.append(self._list_to_markdown(value))
            else:
                if level == 1:
                    markdown_lines.append(f"**{key}:** {value}")
                else:
                    markdown_lines.append(f"- **{key}:** {value}")
        
        return "\n\n".join(markdown_lines)
    
    def _list_to_markdown(self, data: list) -> str:
        """리스트를 마크다운으로 변환"""
        markdown_lines = []
        
        for i, item in enumerate(data):
            if isinstance(item, dict):
                markdown_lines.append(f"### 항목 {i + 1}")
                markdown_lines.append(self._dict_to_markdown(item, 2))
            elif isinstance(item, list):
                markdown_lines.append(f"### 항목 {i + 1}")
                markdown_lines.append(self._list_to_markdown(item))
            else:
                markdown_lines.append(f"- {item}")
        
        return "\n\n".join(markdown_lines)
    
    def _create_wait_node(self):
        """대기 상태 노드 생성"""
        async def wait_node(state: ChatState) -> ChatState:
            print("⏳ 대기 상태 - 메시지 입력 필요")
            return state
        
        return wait_node