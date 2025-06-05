# services/rag_service.py
from typing import List, Dict, Any
from services.openai_service import OpenAIService
from services.vector_db_service import query_vector  # ChromaDB 검색 함수 사용

class RAGService:
    """구성원 성장 이력 기반 RAG 서비스"""
    
    def __init__(self):
        self.openai_service = OpenAIService()
    
    async def generate_answer(
        self, 
        user_question: str, 
        top_k: int = 5
    ) -> Dict[str, Any]:
        """사용자 질문에 대한 답변 생성"""
        
        try:
            # 1. ChromaDB에서 유사한 성장 사례 검색
            search_results = query_vector(user_question, top_k=top_k)
            
            # 2. 검색 결과를 구조화된 형태로 변환
            similar_cases = self.format_search_results(search_results)
            
            if not similar_cases:
                return {
                    "answer": "죄송합니다. 관련된 성장 사례를 찾을 수 없습니다. 다른 방식으로 질문해주시거나 더 구체적인 정보를 제공해주세요.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # 3. 검색된 사례를 바탕으로 답변 생성
            answer = await self.generate_contextual_answer(user_question, similar_cases)
            
            # 4. 신뢰도 계산 (거리 기반)
            confidence = self.calculate_confidence(search_results)
            
            return {
                "answer": answer,
                "sources": similar_cases,
                "confidence": confidence,
                "question": user_question
            }
            
        except Exception as e:
            print(f"RAG service error: {e}")
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                "sources": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    def format_search_results(self, search_results: Dict) -> List[Dict[str, Any]]:
        """ChromaDB 검색 결과를 구조화된 형태로 변환"""
        
        formatted_cases = []
        
        if not search_results or not search_results.get('documents'):
            return formatted_cases
        
        documents = search_results['documents'][0]  # 첫 번째 쿼리 결과
        metadatas = search_results.get('metadatas', [[]])[0]
        distances = search_results.get('distances', [[]])[0]
        ids = search_results.get('ids', [[]])[0]
        
        for i, doc in enumerate(documents):
            case = {
                "id": ids[i] if i < len(ids) else f"case_{i}",
                "content": doc,
                "distance": distances[i] if i < len(distances) else 1.0,
                "similarity": 1 - (distances[i] if i < len(distances) else 1.0),  # 거리를 유사도로 변환
                "metadata": metadatas[i] if i < len(metadatas) else {}
            }
            formatted_cases.append(case)
        
        return formatted_cases
    
    async def generate_contextual_answer(
        self, 
        user_question: str, 
        similar_cases: List[Dict[str, Any]]
    ) -> str:
        """검색된 성장 사례를 바탕으로 맥락적 답변 생성"""
        
        # 상위 3개 사례만 사용하여 컨텍스트 구성
        top_cases = similar_cases[:3]
        
        context_text = self.build_context_from_cases(top_cases)
        
        system_prompt = """당신은 지나비 프로젝트의 커리어 성장 상담 AI입니다.
회사 구성원들의 실제 성장 사례를 바탕으로 개인화된 조언을 제공합니다.

**응답 가이드라인:**
1. 제공된 성장 사례들을 참고하여 구체적이고 실용적인 조언을 하세요
2. 실제 사례의 연차, 역할, 도메인, 스킬 정보를 활용하세요
3. 친근하고 격려하는 톤으로 작성하세요
4. 구체적인 실행 방안이나 다음 단계를 제시하세요
5. 응답은 2-3문단으로 구성하고, 한국어로 작성하세요"""

        user_prompt = f"""
**사용자 질문:** {user_question}

**관련 성장 사례들:**
{context_text}

위 사례들을 참고하여 사용자의 질문에 대한 맞춤형 조언을 제공해주세요.
"""

        # OpenAI 순수 SDK 형태로 메시지 구성
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # chat_completion 메서드 호출 (문자열 반환)
        response = await self.openai_service.chat_completion(messages, temperature=0.7)
        return response  # 이미 문자열이므로 .content 불필요
    
    def build_context_from_cases(self, cases: List[Dict[str, Any]]) -> str:
        """성장 사례들로부터 컨텍스트 텍스트 구성"""
        
        context_parts = []
        
        for i, case in enumerate(cases, 1):
            metadata = case.get('metadata', {})
            
            case_text = f"""
**사례 {i}:**
- 내용: {case['content']}
- 연차: {metadata.get('year', 'N/A')}년차
- 역할: {metadata.get('role', 'N/A')}
- 도메인: {metadata.get('domain', 'N/A')}
- 활용 스킬: {metadata.get('skills', 'N/A')}
- 유사도: {case['similarity']:.2f}
"""
            context_parts.append(case_text.strip())
        
        return "\n\n".join(context_parts)
    
    def calculate_confidence(self, search_results: Dict) -> float:
        """검색 결과의 신뢰도 계산"""
        
        if not search_results or not search_results.get('distances'):
            return 0.0
        
        distances = search_results['distances'][0]
        
        if not distances:
            return 0.0
        
        # 평균 거리를 유사도로 변환 (거리가 작을수록 신뢰도 높음)
        avg_distance = sum(distances) / len(distances)
        confidence = max(0.0, 1.0 - avg_distance)
        
        # 최고 유사도가 0.7 이상이면 추가 보너스
        max_similarity = 1 - min(distances)
        if max_similarity > 0.7:
            confidence = min(1.0, confidence + 0.1)
        
        return round(confidence, 3)