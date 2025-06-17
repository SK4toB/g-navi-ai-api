# advisor.py

from typing import Dict, Any, List
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
import json
import logging
from datetime import datetime

class RecommendationAgent:
    """추천 및 전략 수립 에이전트"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_personalized_recommendation(self,
                                           user_question: str,
                                           user_data: Dict[str, Any],
                                           intent_analysis: Dict[str, Any],
                                           career_cases: List[Document],
                                           external_trends: List[Dict[str, str]]) -> Dict[str, Any]:
        """맞춤형 추천 및 전략 생성"""
        
        self.logger.info("맞춤형 추천 전략 생성 시작")
        
        # LLM 인스턴스 생성
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        
        system_prompt = """당신은 경력 10년 이상의 시니어 커리어 컨설턴트입니다.
사내 구성원들의 실제 커리어 사례와 최신 업계 트렌드를 바탕으로 매우 구체적이고 실행 가능한 맞춤형 커리어 전략을 수립해주세요.

**분석 기준:**
1. 사용자 현재 상황과 유사한 사례 찾기
2. 성공 사례의 핵심 전환점 및 전략 추출  
3. 최신 트렌드와 연결한 미래 지향적 방향 제시
4. 단계별 실행 계획 수립

**제공해야 할 내용:**
1. **상황 진단 및 기회 요소**
2. **맞춤형 커리어 전략** (3-6개월, 1년, 2-3년 단위)
3. **구체적 실행 계획** (학습 로드맵, 프로젝트, 네트워킹 등)
4. **예상 장애물 및 극복 방안**
5. **성공 지표 및 평가 기준**
6. **참고할 만한 사내 롤모델과 사례**

**중요:** 실제 커리어 사례를 반드시 활용하세요. 제공된 사례에서 핵심 전략, 전환 요소, 성장 포인트를 찾아 활용하고, 이를 권장 사항에 명시적으로 통합하세요. 추상적인 조언 대신 실제 사례를 기반으로 한 구체적인 참고 사례와 전략을 포함하세요.

한국어로 친근하면서도 전문적인 톤으로 작성해주세요."""

        # 커리어 사례 요약 - Document와 dict 모두 처리 (상세 정보 포함)
        career_examples = ""
        career_cases_data = []
        
        if career_cases:
            examples = []
            # 최대 6개 사례 사용하여 더 많은 참고 자료 제공
            limited_cases = career_cases[:6]
            
            for i, case in enumerate(limited_cases, 1):
                # 딕셔너리 형태로 변환된 경우
                if isinstance(case, dict):
                    content = case.get('content', '')
                    metadata = case.get('metadata', {})
                # Document 객체인 경우
                elif hasattr(case, 'page_content'):
                    content = case.page_content
                    metadata = case.metadata if hasattr(case, 'metadata') else {}
                else:
                    continue
                
                if content:
                    # 컨텐츠 길이를 500자로 확장하여 더 상세한 정보 제공
                    detailed_content = content[:500] + "..." if len(content) > 500 else content
                    
                    # 더 자세한 사례 정보 구성
                    example = f"""사례 {i}: {metadata.get('name', '익명')} ({metadata.get('current_position', '직책미상')})
- 총 경력: {metadata.get('total_experience', '미상')} | 현재 연차: {metadata.get('experience_years', '미상')}
- 주요 도메인: {metadata.get('primary_domain', '미상')} | 보조 도메인: {metadata.get('secondary_domain', '미상')}
- 핵심 기술: {', '.join(metadata.get('current_skills', [])[:5]) if metadata.get('current_skills') else '미상'}
- 관심 분야: {', '.join(metadata.get('interests', [])[:3]) if metadata.get('interests') else '미상'}
- 커리어 목표: {metadata.get('career_goal', '미상')}
- 전환점/성장 포인트: {metadata.get('transition_point', '미상')}
- 성공 요인: {metadata.get('success_factors', '미상')}
- 현재 프로젝트: {metadata.get('current_project', '미상')}
- 상세 내용: {detailed_content}"""
                    
                    examples.append(example.strip())
                    
                    # 상세한 메타데이터 저장
                    career_cases_data.append({
                        "name": metadata.get('name', '익명'),
                        "position": metadata.get('current_position', ''),
                        "total_experience": metadata.get('total_experience', ''),
                        "experience_years": metadata.get('experience_years', ''),
                        "primary_domain": metadata.get('primary_domain', ''),
                        "secondary_domain": metadata.get('secondary_domain', ''),
                        "current_skills": metadata.get('current_skills', []),
                        "interests": metadata.get('interests', []),
                        "career_goal": metadata.get('career_goal', ''),
                        "transition_point": metadata.get('transition_point', ''),
                        "success_factors": metadata.get('success_factors', ''),
                        "current_project": metadata.get('current_project', ''),
                        "detailed_content": detailed_content
                    })
            
            career_examples = "\n\n".join(examples)
        
        # 외부 트렌드 요약 (컨텍스트 길이 제한)
        trends_summary = ""
        if external_trends:
            trend_items = []
            # 최대 3개 트렌드만 사용
            limited_trends = external_trends[:3]
            for trend in limited_trends:
                # 트렌드 내용도 길이 제한
                snippet = trend.get('snippet', '')[:150] + "..." if len(trend.get('snippet', '')) > 150 else trend.get('snippet', '')
                trend_items.append(f"- {trend.get('title', '')}: {snippet}")
            trends_summary = "\n".join(trend_items)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """
**사용자 질문:** {question}

**사용자 프로필 및 상황:**
{user_profile}

**상황 분석 결과:**
{intent_analysis}

**유사 커리어 사례 (사내):**
{career_examples}

**최신 업계 트렌드:**
{trends_summary}

위 모든 정보를 종합하여 이 사용자에게 가장 적합한 맞춤형 커리어 전략을 수립해주세요.
유사 커리어 사례에서 배울 수 있는 교훈과 전략을 반드시 언급하고, 롤모델 섹션에서 이를 구체적으로 참조해주세요.
구체적이고 실행 가능한 조언을 제공해주세요.
""")
        ])
        
        try:
            # 컨텍스트 길이 제한을 위한 사용자 데이터 압축
            compressed_user_data = self._compress_user_data(user_data)
            compressed_intent = self._compress_intent_analysis(intent_analysis)
            
            # 디버깅을 위한 로그 추가
            self.logger.info(f"사용 가능한 커리어 사례 수: {len(career_cases)} (사용: {min(6, len(career_cases))})")
            self.logger.info(f"외부 트렌드 수: {len(external_trends)} (사용: {min(3, len(external_trends))})")
            
            # 첫 번째 시도 - 압축된 데이터로 시도
            try:
                response = llm.invoke(prompt.format_messages(
                    question=user_question[:500],  # 질문도 길이 제한
                    user_profile=compressed_user_data,
                    intent_analysis=compressed_intent,
                    career_examples=career_examples or "참고할 사내 사례가 없습니다.",
                    trends_summary=trends_summary or "최신 트렌드 정보를 찾을 수 없습니다."
                ))
            except Exception as context_error:
                # 컨텍스트 길이 초과 시 더욱 압축된 데이터로 재시도
                self.logger.warning(f"컨텍스트 길이 초과, 더 압축하여 재시도: {context_error}")
                
                # 더 간단한 프롬프트로 재시도
                simple_prompt = ChatPromptTemplate.from_messages([
                    ("system", "당신은 커리어 컨설턴트입니다. 간결하고 실용적인 조언을 제공해주세요."),
                    ("human", """질문: {question}
                    
현재 상황: {simple_profile}

참고 사례: {simple_examples}

위 정보를 바탕으로 구체적인 커리어 조언을 제공해주세요. (한국어, 1000자 이내)""")
                ])
                
                simple_examples = career_examples[:300] if career_examples else "사례 정보 없음"
                simple_profile = f"경력: {user_data.get('user_profile', {}).get('experience', '미상')}"
                
                response = llm.invoke(simple_prompt.format_messages(
                    question=user_question[:300],
                    simple_profile=simple_profile,
                    simple_examples=simple_examples
                ))
            
            # 응답에 커리어 사례가 포함되었는지 확인
            response_content = response.content if hasattr(response, 'content') else str(response)
            has_career_references = any(keyword in response_content.lower() for keyword in ["사례", "롤모델", "참고할", "경력", "커리어 경로"])
            
            if not has_career_references and career_cases:
                self.logger.warning("응답에 커리어 사례 참조가 누락되었을 수 있습니다. 추가 처리 필요")
                
                # 사례 정보 추가 - 더 상세한 정보 포함
                career_info_section = "\n\n### 📋 참고할 만한 커리어 사례 및 롤모델\n\n"
                for i, doc in enumerate(career_cases[:4], 1):  # 최대 4개 사례 표시
                    if isinstance(doc, dict):
                        metadata = doc.get('metadata', {})
                        content = doc.get('content', '')
                    else:
                        metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                        content = doc.page_content if hasattr(doc, 'page_content') else ''
                    
                    career_info_section += f"**🎯 사례 {i}: {metadata.get('name', 'Unknown')}**\n"
                    career_info_section += f"- **현재 포지션**: {metadata.get('current_position', 'Unknown')}\n"
                    career_info_section += f"- **총 경력**: {metadata.get('total_experience', 'Unknown')} ({metadata.get('experience_years', 'Unknown')}년)\n"
                    career_info_section += f"- **주요 도메인**: {metadata.get('primary_domain', 'Unknown')}\n"
                    career_info_section += f"- **핵심 기술**: {', '.join(metadata.get('current_skills', [])[:5]) if metadata.get('current_skills') else 'Unknown'}\n"
                    career_info_section += f"- **관심 분야**: {', '.join(metadata.get('interests', [])[:3]) if metadata.get('interests') else 'Unknown'}\n"
                    career_info_section += f"- **커리어 목표**: {metadata.get('career_goal', 'Unknown')}\n"
                    career_info_section += f"- **커리어 전환점**: {metadata.get('transition_point', 'Unknown')}\n"
                    career_info_section += f"- **핵심 성공 요소**: {metadata.get('success_factors', 'Unknown')}\n"
                    if content:
                        # 내용이 있으면 요약하여 추가
                        summary = content[:300] + "..." if len(content) > 300 else content
                        career_info_section += f"- **경험 요약**: {summary}\n"
                    career_info_section += "\n"
                
                # 원래 응답에 사례 정보 추가
                if "결론" in response_content or "마무리" in response_content:
                    split_point = max(response_content.rfind("결론"), response_content.rfind("마무리"))
                    if split_point > 0:
                        response_content = response_content[:split_point] + career_info_section + response_content[split_point:]
                    else:
                        response_content += career_info_section
                else:
                    response_content += career_info_section
            
            # 커리어 사례 정보를 recommendation에 추가 - 더 상세한 정보 포함
            career_cases_summary = []
            if career_cases:
                for doc in career_cases[:5]:  # 최대 5개 사례 저장
                    if isinstance(doc, dict):
                        metadata = doc.get('metadata', {})
                        content = doc.get('content', '')
                    else:
                        metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                        content = doc.page_content if hasattr(doc, 'page_content') else ''
                    
                    career_cases_summary.append({
                        "name": metadata.get('name', ''),
                        "position": metadata.get('current_position', ''),
                        "total_experience": metadata.get('total_experience', ''),
                        "experience_years": metadata.get('experience_years', ''),
                        "primary_domain": metadata.get('primary_domain', ''),
                        "secondary_domain": metadata.get('secondary_domain', ''),
                        "current_skills": metadata.get('current_skills', []),
                        "interests": metadata.get('interests', []),
                        "career_goal": metadata.get('career_goal', ''),
                        "transition_point": metadata.get('transition_point', ''),
                        "success_factors": metadata.get('success_factors', ''),
                        "current_project": metadata.get('current_project', ''),
                        "content_summary": content[:200] + "..." if len(content) > 200 else content,
                        "full_content": content  # 전체 내용도 저장
                    })
            
            recommendation = {
                "model_used": "gpt-4o",
                "timestamp": datetime.now().isoformat(),
                "recommendation_content": response_content,
                "career_cases_summary": career_cases_summary,
                "source_trends": len(external_trends),
                "confidence_score": self._calculate_confidence_score(career_cases, external_trends),
                "has_career_references": has_career_references
            }
            
            self.logger.info("맞춤형 추천 전략 생성 완료")
            self.logger.info(f"커리어 사례 참조 포함: {has_career_references}")
            return recommendation
            
        except Exception as e:
            self.logger.error(f"추천 생성 실패: {e}")
            return {
                "error": str(e),
                "fallback_recommendation": "일반적인 커리어 개발 조언을 제공해드릴 수 없어 죄송합니다. 더 구체적인 질문을 해주시면 도움을 드릴 수 있습니다."
            }
    
    def _compress_user_data(self, user_data: Dict[str, Any]) -> str:
        """사용자 데이터를 압축하여 컨텍스트 길이 절약"""
        try:
            # 새로운 user_info 구조에 맞게 수정
            name = user_data.get('name', '미상')
            projects = user_data.get('projects', [])
            
            compressed = f"""이름: {name}"""
            
            if projects:
                latest_project = projects[0]
                project_name = latest_project.get('project_name', '미상')
                role = latest_project.get('role', '미상')
                domain = latest_project.get('domain', '미상')
                
                compressed += f"""
현재 역할: {role}
도메인: {domain}
주요 프로젝트: {project_name}"""
                
                # 프로젝트가 여러 개인 경우
                if len(projects) > 1:
                    compressed += f"\n총 프로젝트 경험: {len(projects)}개"
            else:
                compressed += "\n경력: 신규 또는 정보 없음"
                
            return compressed
        except Exception:
            return "사용자 프로필 정보 압축 실패"
    
    def _compress_intent_analysis(self, intent_analysis: Dict[str, Any]) -> str:
        """의도 분석 결과를 압축"""
        try:
            return f"""질문 유형: {intent_analysis.get('question_type', '미상')}
분석 필요도: {intent_analysis.get('requires_full_analysis', False)}
키워드: {', '.join(intent_analysis.get('career_history', [])[:3])}"""
        except Exception:
            return "의도 분석 결과 압축 실패"
    
    def _calculate_confidence_score(self, career_cases: List[Document], external_trends: List[Dict]) -> float:
        """추천 신뢰도 점수 계산"""
        score = 0.5  # 기본 점수
        
        # 커리어 사례 수에 따른 가산점
        if len(career_cases) >= 3:
            score += 0.3
        elif len(career_cases) >= 1:
            score += 0.2
        
        # 외부 트렌드 정보에 따른 가산점
        if len(external_trends) >= 2:
            score += 0.2
        elif len(external_trends) >= 1:
            score += 0.1
        
        return min(score, 1.0)
