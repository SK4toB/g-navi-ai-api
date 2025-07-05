# app/graphs/agents/mermaid_agent.py
"""
* @className : MermaidDiagramAgent
* @description : Mermaid.js 다이어그램 생성 전문 에이전트 모듈
*                커리어 상담 내용을 분석하여 적절한 시각화를 제공하는 에이전트입니다.
*                GPT 기반 지능형 다이어그램 유형 선택과 한국어 커리어 상담에 최적화된 템플릿을 제공합니다.
*
*                🎯 주요 기능:
*                1. 텍스트 응답 내용을 분석하여 다이어그램 유형 결정
*                2. 커리어 경로, 학습 로드맵, 프로세스 등을 Mermaid로 시각화
*                3. 사용자 이해도를 높이는 구조화된 다이어그램 생성
*                4. 반응형 웹에 최적화된 Mermaid 코드 출력
*
*                🎯 지원 다이어그램 유형:
*                - flowchart: 단계별 프로세스, 의사결정 흐름
*                - mindmap: 역량 분석, 관련 개념 정리  
*                - journey: 커리어 전환 과정, 학습 여정
*                - timeline: 시간 순서가 있는 계획
*                - graph: 관계형 구조, 연관성 표현
*
*                🔧 주요 특징:
*                - GPT 기반 지능형 다이어그램 유형 선택
*                - 한국어 커리어 상담에 최적화된 템플릿
*                - 웹 친화적 색상과 스타일 적용
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see OpenAI, Mermaid.js
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""

from typing import Dict, Any, Optional
import logging
import openai
import os
import json
import re

class MermaidDiagramAgent:
    """
    * @className : MermaidDiagramAgent
    * @description : Mermaid.js 다이어그램 생성 전문 에이전트 클래스
    *                포맷된 응답 내용을 분석하여 사용자 이해를 돕는 시각적 다이어그램을 생성합니다.
    *                커리어 상담에 특화된 템플릿과 스타일을 사용하여 전문적인 시각화를 제공합니다.
    *
    * @modification : 2025.07.01(이재원) 최초생성
    *
    * @author 이재원
    * @Date 2025.07.01
    * @version 1.0
    * @see OpenAI, Mermaid.js
    *  == 개정이력(Modification Information) ==
    *  
    *   수정일        수정자        수정내용
    *   ----------   --------     ---------------------------
    *   2025.07.01   이재원       최초 생성
    *  
    * Copyright (C) by G-Navi AI System All right reserved.
    """
    
    def __init__(self):
        """
        MermaidDiagramAgent 생성자 - 초기화를 수행한다.
        """
        self.logger = logging.getLogger(__name__)  # 로거 생성
        self.client = None  # OpenAI 클라이언트 지연 초기화
        
        # Mermaid 다이어그램 생성 시스템 프롬프트
        self.system_prompt = """
당신은 Mermaid.js 다이어그램 생성 전문가입니다. 

**주요 임무:**
주어진 커리어 상담 내용과 AI 응답을 분석하여 내용을 가장 잘 표현하는 Mermaid 다이어그램을 생성합니다.

**다이어그램 유형 선택 기준:**

1. **Flowchart (플로우차트)** - 가장 범용적
   - 커리어 경로, 학습 로드맵, 단계별 과정
   - 의사결정 과정, 업무 흐름
   - 조건부 분기가 있는 프로세스

2. **Timeline (타임라인/갠트차트)**
   - 시간 순서가 중요한 내용
   - 커리어 발전 단계, 학습 계획
   - 프로젝트 일정, 성장 로드맵

3. **Mindmap (마인드맵)**
   - 관련 개념들의 체계적 분류
   - 기술 스택, 역량 체계
   - 학습 분야의 연관성

4. **Sequence Diagram (시퀀스 다이어그램)**
   - 협업이나 상호작용 과정
   - 업무 절차, 프로젝트 진행
   - 커뮤니케이션 흐름

5. **Class Diagram (클래스 다이어그램)**
   - 조직 구조, 역할 관계
   - 시스템 아키텍처
   - 계층적 구조

**생성 규칙:**
1. 한국어 텍스트는 반드시 따옴표("")로 감싸기
2. 노드명은 간결하고 명확하게 (15자 이내)
3. 복잡하지 않고 이해하기 쉬운 구조
4. 색상/스타일을 활용해 가독성 향상
5. 논리적 흐름과 계층 구조 명확히 표현

**출력 형식:**
반드시 다음 형식으로만 응답하세요:
```mermaid
[다이어그램 코드]
```

추가 설명이나 주석은 절대 포함하지 마세요.
"""

    def _initialize_openai_client(self):
        """OpenAI 클라이언트 지연 초기화"""
        if self.client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            self.client = openai.OpenAI(api_key=api_key)

    def generate_diagram(self, 
                        formatted_content: str,
                        user_question: str = "",
                        intent_analysis: Dict[str, Any] = None,
                        user_data: Dict[str, Any] = None) -> str:
        """
        포맷된 응답 내용을 기반으로 Mermaid 다이어그램 생성
        
        Args:
            formatted_content: 포맷된 마크다운 응답 내용
            user_question: 사용자 질문
            intent_analysis: 의도 분석 결과
            user_data: 사용자 데이터
            
        Returns:
            str: Mermaid 다이어그램 코드 (빈 문자열이면 생성 실패)
        """
        
        try:
            print("🎨 Mermaid 다이어그램 생성 시작...")
            
            # OpenAI 클라이언트 초기화
            self._initialize_openai_client()
            
            # 컨텍스트 준비
            context = self._prepare_context(
                formatted_content, user_question, intent_analysis, user_data
            )
            
            # LLM 호출하여 다이어그램 생성
            mermaid_code = self._call_llm_for_diagram(context)
            
            # 다이어그램 코드 정리 및 검증
            cleaned_code = self._clean_and_validate_mermaid(mermaid_code)
            
            if cleaned_code:
                print(f"✅ Mermaid 다이어그램 생성 완료 ({len(cleaned_code)}자)")
                self.logger.info("Mermaid 다이어그램 생성 성공")
            else:
                print("⚠️ Mermaid 다이어그램 생성 실패")
                self.logger.warning("Mermaid 다이어그램 생성 실패")
            
            return cleaned_code
            
        except Exception as e:
            self.logger.error(f"Mermaid 다이어그램 생성 중 오류: {e}")
            print(f"❌ 다이어그램 생성 오류: {e}")
            return ""

    def _prepare_context(self, 
                        formatted_content: str,
                        user_question: str = "",
                        intent_analysis: Dict[str, Any] = None,
                        user_data: Dict[str, Any] = None) -> str:
        """다이어그램 생성을 위한 컨텍스트 준비"""
        
        context_sections = []
        
        # 사용자 질문
        if user_question:
            context_sections.append(f"**사용자 질문:** {user_question}")
            context_sections.append("")
        
        # 의도 분석 정보 (다이어그램 유형 결정에 도움)
        if intent_analysis:
            intent_type = intent_analysis.get('intent_type', '')
            categories = intent_analysis.get('categories', [])
            
            if intent_type:
                context_sections.append(f"**질문 유형:** {intent_type}")
            if categories and isinstance(categories, list):
                context_sections.append(f"**카테고리:** {', '.join(str(c) for c in categories)}")
            context_sections.append("")
        
        # 포맷된 응답 내용 (핵심)
        context_sections.append("**AI 응답 내용 (다이어그램으로 변환할 대상):**")
        context_sections.append("---")
        context_sections.append(formatted_content)
        context_sections.append("---")
        context_sections.append("")
        
        # 다이어그램 생성 요청
        context_sections.append("**다이어그램 생성 요청:**")
        context_sections.append("위 AI 응답 내용을 분석하여 핵심 구조와 흐름을 시각적으로 표현하는 Mermaid 다이어그램을 생성해주세요.")
        context_sections.append("사용자가 이해하기 쉽고 실용적인 다이어그램이 목표입니다.")
        
        return "\n".join(context_sections)

    def _call_llm_for_diagram(self, context: str) -> str:
        """LLM 호출하여 Mermaid 다이어그램 생성"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context}
                ],
                temperature=0.2,  # 일관성 있는 다이어그램을 위해 낮은 온도
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Mermaid 다이어그램 LLM 호출 실패: {e}")
            raise

    def _clean_and_validate_mermaid(self, raw_code: str) -> str:
        """Mermaid 코드 정리 및 기본 검증"""
        
        try:
            if not raw_code or not raw_code.strip():
                return ""
            
            # ```mermaid 블록에서 코드 추출
            mermaid_pattern = r'```mermaid\s*\n(.*?)\n```'
            match = re.search(mermaid_pattern, raw_code, re.DOTALL)
            
            if match:
                code = match.group(1).strip()
            else:
                # 일반 코드 블록 확인
                code_pattern = r'```\s*\n(.*?)\n```'
                match = re.search(code_pattern, raw_code, re.DOTALL)
                if match:
                    code = match.group(1).strip()
                else:
                    # 코드 블록이 없으면 전체 텍스트 사용
                    code = raw_code.strip()
            
            # 기본 검증: Mermaid 키워드 포함 여부
            mermaid_keywords = [
                'flowchart', 'graph', 'sequenceDiagram', 'classDiagram', 
                'timeline', 'mindmap', 'gitgraph', 'journey'
            ]
            
            if any(keyword in code for keyword in mermaid_keywords):
                return code
            else:
                self.logger.warning("생성된 코드에 Mermaid 키워드가 없음")
                return ""
                
        except Exception as e:
            self.logger.warning(f"Mermaid 코드 정리 실패: {e}")
            return ""

    def get_sample_diagrams(self) -> Dict[str, str]:
        """테스트용 샘플 다이어그램들"""
        
        return {
            "career_path": '''flowchart TD
    A["백엔드 개발자"] --> B["도메인 지식 습득"]
    B --> C["PM 역량 개발"]
    C --> D["프로젝트 리딩"]
    D --> E["Application PM"]
    
    B --> B1["비즈니스 이해"]
    B --> B2["사용자 관점"]
    
    C --> C1["의사소통"]
    C --> C2["일정관리"]
    
    style A fill:#e1f5fe
    style E fill:#c8e6c9''',
            
            "learning_timeline": '''timeline
    title 개발자 → PM 전환 로드맵
    
    section 1-3개월
        기초 학습 : 도메인 지식
                  : 비즈니스 이해
    
    section 4-6개월
        역량 개발 : PM 기초 이론
                  : 애자일 방법론
    
    section 7-12개월
        실무 적용 : 프로젝트 리딩
                  : 팀 협업 경험''',
            
            "skill_mindmap": '''mindmap
  root)PM 필수 역량(
    기술적 역량
      개발 경험
      시스템 이해
      아키텍처
    
    비즈니스 역량
      도메인 지식
      사용자 경험
      시장 이해
    
    관리 역량
      프로젝트 관리
      일정 계획
      리스크 관리
    
    소통 역량
      이해관계자 관리
      팀 커뮤니케이션
      문서화'''
        }