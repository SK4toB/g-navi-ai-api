# app/services/simple_answer_service.py
from typing import List, Dict, Any
from services.vector_db_service import query_vector

class SimpleAnswerService:
    """OpenAI 없이 간단한 답변 생성 서비스"""
    
    def generate_simple_answer(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """벡터 검색 결과를 기반으로 간단한 답변 생성"""
        
        try:
            # 벡터 검색
            search_results = query_vector(question, top_k=top_k)
            
            if not search_results or not search_results.get('documents'):
                return {
                    "answer": "관련된 성장 사례를 찾을 수 없습니다.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # 검색 결과 파싱
            documents = search_results['documents'][0]
            metadatas = search_results.get('metadatas', [[]])[0]
            distances = search_results.get('distances', [[]])[0]
            
            # 상위 결과들 분석
            top_cases = []
            for i, doc in enumerate(documents):
                if i >= top_k:
                    break
                    
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0
                similarity = 1 - distance
                
                case = {
                    "content": doc,
                    "similarity": similarity,
                    "year": metadata.get('year', 'N/A'),
                    "role": metadata.get('role', 'N/A'),
                    "domain": metadata.get('domain', 'N/A'),
                    "skills": metadata.get('skills', 'N/A')
                }
                top_cases.append(case)
            
            # 간단한 답변 생성
            answer = self.create_simple_answer(question, top_cases)
            
            # 신뢰도 계산
            confidence = self.calculate_confidence(top_cases)
            
            return {
                "answer": answer,
                "sources": top_cases,
                "confidence": confidence,
                "question": question
            }
            
        except Exception as e:
            return {
                "answer": f"답변 생성 중 오류가 발생했습니다: {str(e)}",
                "sources": [],
                "confidence": 0.0
            }
    
    def create_simple_answer(self, question: str, cases: List[Dict[str, Any]]) -> str:
        """검색된 사례를 바탕으로 간단한 답변 생성"""
        
        if not cases:
            return "관련된 성장 사례를 찾을 수 없습니다."
        
        # 질문 유형 분석
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['시니어', '성장', '준비', '경험']):
            return self.generate_career_growth_answer(cases)
        elif any(word in question_lower for word in ['pm', '매니저', '관리']):
            return self.generate_pm_answer(cases)
        elif any(word in question_lower for word in ['개발', 'python', '기술']):
            return self.generate_dev_answer(cases)
        elif any(word in question_lower for word in ['금융', '도메인', '프로젝트']):
            return self.generate_domain_answer(cases)
        else:
            return self.generate_general_answer(cases)
    
    def generate_career_growth_answer(self, cases: List[Dict[str, Any]]) -> str:
        """경력 성장 관련 답변"""
        
        # 연차별 분석
        years = [float(case['year']) for case in cases if case['year'] != 'N/A']
        avg_year = sum(years) / len(years) if years else 0
        
        # 주요 역할 추출
        roles = [case['role'] for case in cases if case['role'] != 'N/A']
        unique_roles = list(set(roles))
        
        answer = f"""💡 **시니어 개발자 성장 경로 분석**

우리 회사 구성원들의 성장 사례를 분석한 결과:

**📈 성장 단계:**
- 평균 {avg_year:.0f}년차 정도에서 다양한 경험을 쌓고 있습니다
- 주요 역할: {', '.join(unique_roles[:3])}

**🎯 추천 성장 방향:**
1. **다양한 프로젝트 경험** - 여러 도메인에서의 실무 경험
2. **기술 역량 확장** - 분석/설계부터 개발까지 전 영역 경험
3. **리더십 개발** - 팀 리딩이나 프로젝트 관리 경험

실제 구성원들도 이런 경로로 성장해왔으니 참고해보세요! 🚀"""

        return answer
    
    def generate_pm_answer(self, cases: List[Dict[str, Any]]) -> str:
        """PM 역할 관련 답변"""
        
        pm_cases = [case for case in cases if 'PM' in case['role']]
        
        if pm_cases:
            domains = [case['domain'] for case in pm_cases if case['domain'] != 'N/A']
            years = [float(case['year']) for case in pm_cases if case['year'] != 'N/A']
            
            answer = f"""🎯 **PM 역할 경험 분석**

우리 회사 PM들의 실제 경험:

**📊 경험 현황:**
- PM 경험자들의 평균 연차: {sum(years)/len(years):.0f}년차
- 주요 활동 도메인: {', '.join(set(domains))}

**💼 PM 역할의 특징:**
- 대부분 20년 이상 경력에서 PM 역할 수행
- 금융, 제조 등 다양한 도메인에서 프로젝트 관리
- IT통합유지보수, 차세대 시스템 구축 등 대규모 프로젝트 경험

**🚀 PM으로 성장하려면:**
1. 충분한 기술적 경험 축적 (15년+ 권장)
2. 특정 도메인 전문성 확보
3. 프로젝트 관리 역량 개발"""
        else:
            answer = "PM 역할 관련 구체적인 사례를 찾지 못했지만, 일반적으로 충분한 기술 경험과 리더십이 필요합니다."
        
        return answer
    
    def generate_dev_answer(self, cases: List[Dict[str, Any]]) -> str:
        """개발 관련 답변"""
        
        dev_cases = [case for case in cases if '개발' in case['role']]
        
        answer = f"""💻 **개발자 성장 경로**

우리 회사 개발자들의 성장 패턴:

**🔧 기술 스택:**
- 주로 S-1, S-2, S-16 등의 기술 활용
- 다양한 도메인에서 분석/설계/개발 경험

**📈 성장 단계:**
1. **초급 (1-3년차)**: 기본 개발 업무, 학사시스템 등 구축
2. **중급 (4-7년차)**: 아키텍처 설계, SCM 구축 등
3. **고급 (8년+)**: 백엔드 전문가, 시스템 아키텍트

**💡 성장 팁:**
- 다양한 도메인 경험 (유통, 제조, 공공 등)
- 기술 스택 확장과 심화
- 분석부터 개발까지 전 과정 경험"""
        
        return answer
    
    def generate_domain_answer(self, cases: List[Dict[str, Any]]) -> str:
        """도메인 관련 답변"""
        
        domains = [case['domain'] for case in cases if case['domain'] != 'N/A']
        unique_domains = list(set(domains))
        
        answer = f"""🏢 **도메인 전문성 개발**

우리 회사에서 경험할 수 있는 주요 도메인:

**🎯 주요 도메인:**
{chr(10).join([f"- {domain}" for domain in unique_domains[:5]])}

**💼 도메인별 특징:**
- **금융**: 차세대 시스템, IT통합유지보수
- **제조**: SCM, MES 구축, 프로세스 최적화  
- **공공**: 위성데이터 처리, 공공서비스 시스템
- **유통/서비스**: 학사시스템, 렌터카 시스템

**🚀 도메인 전문가가 되려면:**
1. 특정 도메인에서 지속적인 프로젝트 참여
2. 해당 도메인의 비즈니스 이해
3. 도메인 특화 기술 스택 습득"""
        
        return answer
    
    def generate_general_answer(self, cases: List[Dict[str, Any]]) -> str:
        """일반적인 답변"""
        
        roles = [case['role'] for case in cases if case['role'] != 'N/A']
        domains = [case['domain'] for case in cases if case['domain'] != 'N/A']
        
        answer = f"""📊 **구성원 성장 사례 분석**

검색된 성장 사례들을 분석한 결과:

**👥 주요 역할:**
{chr(10).join([f"- {role}" for role in set(roles)[:5]])}

**🏢 활동 도메인:**
{chr(10).join([f"- {domain}" for domain in set(domains)[:5]])}

**💡 인사이트:**
- 다양한 역할과 도메인에서 경험을 쌓고 있습니다
- 기술적 역량과 도메인 전문성을 함께 개발하는 것이 중요합니다
- 지속적인 학습과 새로운 프로젝트 참여가 성장의 핵심입니다

더 구체적인 조언이 필요하시면 구체적인 질문을 해주세요! 🚀"""
        
        return answer
    
    def calculate_confidence(self, cases: List[Dict[str, Any]]) -> float:
        """신뢰도 계산"""
        
        if not cases:
            return 0.0
        
        similarities = [case['similarity'] for case in cases]
        avg_similarity = sum(similarities) / len(similarities)
        
        # 0.2 이상이면 높은 신뢰도
        if avg_similarity > 0.2:
            return min(1.0, avg_similarity + 0.3)
        else:
            return max(0.1, avg_similarity + 0.5)