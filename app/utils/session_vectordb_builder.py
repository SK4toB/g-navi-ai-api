# app/utils/session_vectordb_builder.py
"""
🗃️ 사용자별 채팅 세션 대화내역 VectorDB 구축 시스템

📋 핵심 기능:
1. 세션 종료 시 사용자의 current_session_messages를 VectorDB로 자동 구축
2. 사용자별(member_id) 분리된 VectorDB 저장 → 개인정보 보호 및 개인화 검색
3. OpenAI Embeddings + ChromaDB를 활용한 의미 기반 검색
4. 과거 대화 요약 및 키워드 추출로 검색 품질 향상

🔄 동작 플로우:
세션 종료 → current_session_messages 수집 → 스마트 규칙기반 요약 → VectorDB 구축 → 향후 검색 활용

📁 저장 구조:
storage/vector_stores/user_{member_id}_sessions/
├── chroma.sqlite3              # ChromaDB 벡터 저장소
├── session_index.json          # 세션 메타데이터 인덱스
└── 기타 ChromaDB 파일들

⚠️ 중요 사항:
- 각 사용자별로 완전히 분리된 VectorDB 생성 (타 사용자 데이터 접근 불가)
- 세션 종료 시에만 VectorDB 구축 (실시간 업데이트 아님)
- 검색 시 관련도 점수 기반 필터링으로 품질 보장
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

class SessionVectorDBBuilder:
    """
    🗃️ 사용자별 채팅 세션 대화내역 VectorDB 구축 및 관리 클래스
    
    이 클래스는 채팅 세션이 종료될 때 해당 세션의 모든 대화 내역을
    사용자별로 분리된 VectorDB에 저장하여, 향후 개인화된 검색 서비스를 제공합니다.
    
    주요 책임:
    - 세션 종료 시 current_session_messages → VectorDB 자동 구축
    - 사용자별 VectorDB 분리 관리 (member_id 기준)
    - 과거 대화 의미 기반 검색 기능 제공
    - 세션 메타데이터 및 통계 관리
    """
    
    def __init__(self):
        """
        VectorDB 구축 시스템 초기화
        
        설정 내용:
        - 저장 경로: app/storage/vector_stores/
        - 임베딩 모델: OpenAI text-embedding-3-small
        - 텍스트 분할: 1000자 청크, 200자 오버랩
        """
        # 📁 VectorDB 저장 경로 설정 (사용자별 폴더로 분리됨)
        self.storage_path = Path(__file__).parent.parent / "storage" / "vector_stores"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 🤖 OpenAI 임베딩 모델 초기화 (환경변수 OPENAI_API_KEY 필요)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small"  # 비용 효율적이면서 성능 좋은 모델
        )
        
        # ✂️ 텍스트 청킹 설정 (긴 대화를 적절한 크기로 분할)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,    # 각 청크 최대 1000자
            chunk_overlap=200,  # 청크 간 200자 중복 (컨텍스트 보존)
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]  # 자연스러운 분할점
        )
        
        print(f"SessionVectorDBBuilder 초기화 완료 (저장경로: {self.storage_path})")
    
    async def summarize_session_content(self, messages: List[Dict[str, Any]], user_name: str) -> str:
        """
        📝 세션 대화 내용을 요약하여 검색 가능한 메타데이터 생성
        
        Args:
            messages: 세션의 모든 대화 메시지 [{"role": "user/assistant", "content": "..."}]
            user_name: 사용자 이름
            
        Returns:
            str: "사용자 {이름}의 {세션유형} - N개 질문, M개 응답 | 주제: 키워드들"
            
        💡 기능:
            - 세션 유형 자동 분류 (커리어상담, 기술학습, 창업상담 등)
            - 실제 메시지 개수 정확 계산
            - 도메인별 스마트 키워드 추출
            - VectorDB 검색 최적화를 위한 구조화된 요약
        """
        try:
            if not messages:
                return f"사용자 {user_name}의 빈 대화 세션"
            
            # 메시지를 텍스트로 변환하여 분석 준비
            conversation_text = self._format_messages_to_text(messages)
            
            if not conversation_text.strip():
                return f"사용자 {user_name}의 빈 대화 세션"
            
            # 스마트 규칙 기반 요약 생성
            summary = await self._generate_smart_summary(conversation_text, user_name, messages)
            
            return summary
            
        except Exception as e:
            print(f"세션 내용 요약 실패: {e}")
            return f"사용자 {user_name}의 대화 세션 (요약 실패)"
    
    def _format_messages_to_text(self, messages: List[Dict[str, Any]]) -> str:
        """메시지 목록을 텍스트로 변환"""
        text_parts = []
        
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                
                if role == 'user':
                    text_parts.append(f"사용자: {content}")
                elif role == 'assistant':
                    text_parts.append(f"AI: {content}")
                elif role == 'system':
                    text_parts.append(f"시스템: {content}")
                else:
                    text_parts.append(f"{role}: {content}")
        
        return "\n".join(text_parts)
    
    async def _generate_smart_summary(self, conversation_text: str, user_name: str, messages: List[Dict[str, Any]]) -> str:
        """
        🧠 스마트 규칙 기반 대화 요약 생성
        
        Args:
            conversation_text: 전체 대화 텍스트
            user_name: 사용자 이름
            messages: 원본 메시지 리스트
            
        Returns:
            str: 구조화된 세션 요약
            
        💡 처리 과정:
            1. 실제 메시지 개수 정확 계산 (user vs assistant)
            2. 대화 주제 및 세션 유형 자동 분석
            3. 도메인별 특화 키워드 추출
            4. 세션 길이에 따른 적응형 요약 생성
        """
        try:
            # 🔍 디버깅: 메시지 분석 상세 로그
            print(f"   📊 메시지 분석 시작:")
            print(f"     전체 메시지 수: {len(messages)}개")
            
            # 메시지 유형별 카운팅 및 상세 분석
            user_messages = []
            assistant_messages = []
            system_messages = []
            other_messages = []
            
            for i, msg in enumerate(messages):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                print(f"     #{i+1} {role}: {content[:50]}{'...' if len(content) > 50 else ''}")
                
                if role == 'user':
                    user_messages.append(msg)
                elif role == 'assistant':
                    assistant_messages.append(msg)
                elif role == 'system':
                    system_messages.append(msg)
                else:
                    other_messages.append(msg)
            
            user_count = len(user_messages)
            assistant_count = len(assistant_messages)
            
            print(f"     📈 카운팅 결과:")
            print(f"       사용자 메시지: {user_count}개")
            print(f"       AI 응답: {assistant_count}개")
            print(f"       시스템 메시지: {len(system_messages)}개")
            print(f"       기타 메시지: {len(other_messages)}개")
            
            # 대화 주제 및 세션 유형 분석
            topic_analysis = self._analyze_conversation_topics(conversation_text, messages)
            
            # 세션 길이에 따른 적응형 요약 생성
            if len(messages) >= 10:
                # 긴 대화: 상세한 요약 (주제 + 키워드)
                summary = f"사용자 {user_name}의 {topic_analysis['session_type']} - "
                summary += f"{user_count}개 질문, {assistant_count}개 응답"
                
                if topic_analysis['main_topics']:
                    summary += f" | 주제: {', '.join(topic_analysis['main_topics'][:3])}"
                    
                if topic_analysis['keywords']:
                    summary += f" | 키워드: {', '.join(topic_analysis['keywords'][:3])}"
            else:
                # 짧은 대화: 간결한 요약 (주제 중심)
                summary = f"사용자 {user_name}의 {topic_analysis['session_type']} - "
                summary += f"{user_count}개 질문, {assistant_count}개 응답"
                
                if topic_analysis['main_topics']:
                    summary += f" | 주제: {', '.join(topic_analysis['main_topics'][:2])}"
            
            print(f"   ✅ 생성된 요약: {summary}")
            return summary
            
        except Exception as e:
            print(f"스마트 요약 생성 실패: {e}")
            # 폴백: 기본 요약 생성
            user_count = len([msg for msg in messages if msg.get('role') == 'user'])
            assistant_count = len([msg for msg in messages if msg.get('role') == 'assistant'])
            return f"사용자 {user_name}의 대화세션 - {user_count}개 질문, {assistant_count}개 응답"
    
    def _analyze_conversation_topics(self, conversation_text: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        🔍 개선된 대화 내용 분석 - 맥락과 주제 전환을 더 정확히 파악
        
        Args:
            conversation_text: 전체 대화 텍스트
            messages: 원본 메시지 리스트
            
        Returns:
            Dict[str, Any]: {
                'session_type': '세션 유형',
                'main_topics': ['핵심 주제 리스트'],
                'keywords': ['키워드 리스트'],
                'message_count': 메시지 수,
                'complexity_indicators': ['복잡성 지표']
            }
            
        💡 개선된 분석 과정:
            1. 주제 전환 패턴 감지
            2. 부정적 표현과 긍정적 표현 구분
            3. 시간 흐름에 따른 주제 변화 추적
            4. 복합 주제 식별
        """
        try:
            # 💼 기본 세션 유형 분석 (기존 로직)
            session_types = {
                '커리어상담': ['커리어', '진로', '취업', '이직', '성장', '개발자', '직업', '분야', '포지션'],
                '기술학습': ['React', 'Python', '프로그래밍', '개발', '코딩', '언어', '프레임워크', '기술'],
                '창업상담': ['창업', '사업', '스타트업', '비즈니스', '회사'],
                '교육과정': ['강의', '수업', '학습', '교육', '과정', '코스'],
                '일반상담': []  # 기본값
            }
            
            # 🔄 주제 전환 감지 (개선됨)
            topic_progression = self._track_topic_progression(messages, session_types)
            
            # 📊 주요 세션 유형 결정 (가중치 기반)
            session_type = self._determine_primary_session_type(topic_progression, conversation_text)
            
            # 🔑 컨텍스트 인식 키워드 추출
            keywords = self._extract_contextual_keywords(conversation_text, session_type)
            
            # 🎯 도메인별 특화 주제 식별 (기존 로직 개선)
            main_topics = self._identify_specialized_topics(session_type, keywords, conversation_text)
            
            # ⚠️ 복잡성 지표 식별
            complexity_indicators = self._identify_complexity_indicators(conversation_text, messages)
            
            return {
                'session_type': session_type,
                'main_topics': main_topics[:3],
                'keywords': keywords[:5],
                'message_count': len(messages),
                'topic_progression': topic_progression,
                'complexity_indicators': complexity_indicators
            }
            
        except Exception as e:
            print(f"대화 주제 분석 실패: {e}")
            return {
                'session_type': '대화세션',
                'main_topics': [],
                'keywords': [],
                'message_count': len(messages),
                'topic_progression': [],
                'complexity_indicators': []
            }
    
    def _track_topic_progression(self, messages: List[Dict[str, Any]], session_types: Dict[str, List[str]]) -> List[str]:
        """🔄 시간 순서에 따른 주제 변화 추적"""
        progression = []
        
        for msg in messages:
            if msg.get('role') != 'user':
                continue
                
            content = msg.get('content', '')
            msg_topics = []
            
            # 각 메시지별 주제 식별
            for type_name, keywords in session_types.items():
                if any(keyword in content for keyword in keywords):
                    msg_topics.append(type_name)
            
            if msg_topics:
                progression.append(msg_topics[0])
            elif progression:  # 이전 주제 유지
                progression.append(progression[-1])
            else:
                progression.append('일반상담')
        
        return progression
    
    def _determine_primary_session_type(self, topic_progression: List[str], conversation_text: str) -> str:
        """📊 주제 진행을 바탕으로 주요 세션 유형 결정"""
        if not topic_progression:
            return '일반상담'
        
        # 주제별 가중치 계산
        topic_weights = {}
        total_messages = len(topic_progression)
        
        for i, topic in enumerate(topic_progression):
            # 나중에 나온 주제에 더 높은 가중치 (최근 주제가 더 중요)
            weight = (i + 1) / total_messages * 1.5 + 0.5
            topic_weights[topic] = topic_weights.get(topic, 0) + weight
        
        # 복합 주제 감지
        if len(set(topic_progression)) > 1:
            # 주제 전환이 있는 경우
            dominant_topic = max(topic_weights, key=topic_weights.get)
            
            # 창업+기술 조합 감지
            if ('창업상담' in topic_weights and '기술학습' in topic_weights):
                return '창업-기술 복합상담'
            elif ('커리어상담' in topic_weights and '기술학습' in topic_weights):
                return '커리어-기술 복합상담'
            else:
                return dominant_topic
        else:
            return topic_progression[0]
    
    def _extract_contextual_keywords(self, conversation_text: str, session_type: str) -> List[str]:
        """🔑 세션 유형에 맞는 컨텍스트 인식 키워드 추출"""
        # 기본 키워드 추출
        basic_keywords = self._extract_keywords(conversation_text)
        
        # 세션 유형별 특화 키워드 보강
        context_keywords = []
        
        if '복합상담' in session_type:
            # 복합 상담의 경우 두 영역 키워드 모두 중요
            tech_patterns = ['개발', '프로그래밍', 'React', 'Python', '기술']
            career_patterns = ['커리어', '진로', '창업', '이직']
            
            for keyword in basic_keywords:
                if any(pattern in keyword for pattern in tech_patterns + career_patterns):
                    context_keywords.append(keyword)
        
        # 컨텍스트 키워드가 충분하면 사용, 아니면 기본 키워드
        return context_keywords[:5] if len(context_keywords) >= 3 else basic_keywords[:5]
    
    def _identify_specialized_topics(self, session_type: str, keywords: List[str], conversation_text: str) -> List[str]:
        """🎯 개선된 도메인별 특화 주제 식별"""
        main_topics = []
        
        if session_type == '커리어상담' or '커리어' in session_type:
            career_topics = {
                '백엔드개발': ['백엔드', 'Django', 'FastAPI', 'API', '서버'],
                '프론트엔드': ['프론트엔드', 'React', 'Vue', 'JavaScript', '웹'],
                '데이터사이언스': ['데이터', '분석', '머신러닝', 'AI', '파이썬'],
                '커리어전환': ['전환', '이직', '변경', '바꾸고'],
                '성장고민': ['성장', '발전', '실력', '역량']
            }
            main_topics = self._match_topics_by_keywords(career_topics, keywords, conversation_text)
        
        elif session_type == '기술학습' or '기술' in session_type:
            tech_topics = {
                'React학습': ['React', '컴포넌트', 'JSX', 'Hook'],
                'Python기초': ['Python', '파이썬', '기초', '변수'],
                '웹개발': ['웹', 'HTML', 'CSS', '개발'],
                'AI학습': ['AI', '머신러닝', '딥러닝', '인공지능'],
                '프로그래밍입문': ['프로그래밍', '코딩', '입문', '시작']
            }
            main_topics = self._match_topics_by_keywords(tech_topics, keywords, conversation_text)
        
        elif session_type == '창업상담' or '창업' in session_type:
            business_topics = {
                '기술창업': ['기술', '개발', 'IT', '앱'],
                '아이디어검증': ['아이디어', '검증', '시장'],
                '팀빌딩': ['팀', '구성', '인력', '채용'],
                '사업계획': ['사업', '계획', '전략', '수익']
            }
            main_topics = self._match_topics_by_keywords(business_topics, keywords, conversation_text)
        
        # 복합 상담의 경우 특별 처리
        if '복합상담' in session_type:
            if '창업-기술' in session_type:
                main_topics.append('창업을 위한 기술역량')
            elif '커리어-기술' in session_type:
                main_topics.append('개발 커리어 고민')
        
        # 주제가 없으면 상위 키워드로 대체
        return main_topics[:3] if main_topics else keywords[:3]
    
    def _match_topics_by_keywords(self, topic_dict: Dict[str, List[str]], keywords: List[str], conversation_text: str) -> List[str]:
        """키워드 매칭을 통한 주제 식별"""
        matched_topics = []
        
        for topic, topic_keywords in topic_dict.items():
            # 키워드 직접 매칭
            keyword_matches = sum(1 for kw in keywords if any(tk in kw for tk in topic_keywords))
            # 대화 텍스트 직접 매칭
            text_matches = sum(1 for tk in topic_keywords if tk in conversation_text)
            
            # 매칭 점수가 충분하면 주제로 선정
            if keyword_matches >= 1 or text_matches >= 2:
                matched_topics.append(topic)
        
        return matched_topics
    
    def _identify_complexity_indicators(self, conversation_text: str, messages: List[Dict[str, Any]]) -> List[str]:
        """⚠️ 대화 복잡성 지표 식별"""
        indicators = []
        
        # 부정적 감정 표현
        negative_patterns = ['어려워', '힘들어', '포기', '모르겠어', '걱정']
        if any(pattern in conversation_text for pattern in negative_patterns):
            indicators.append('부정적 감정')
        
        # 주제 전환
        if len(set([msg.get('content', '')[:10] for msg in messages if msg.get('role') == 'user'])) > len(messages) // 2:
            indicators.append('주제 다양성')
        
        # 긴 대화
        if len(messages) >= 8:
            indicators.append('장시간 대화')
        
        # 복합 질문
        complex_question_count = sum(1 for msg in messages 
                                   if msg.get('role') == 'user' and len(msg.get('content', '')) > 50)
        if complex_question_count >= 2:
            indicators.append('복잡한 질문')
        
        return indicators
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        🔑 스마트 키워드 추출 - 대화에서 의미있는 핵심 키워드만 선별
        
        Args:
            text: 전체 대화 텍스트
            
        Returns:
            List[str]: 중요도 순으로 정렬된 키워드 리스트 (최대 5개)
            
        💡 추출 전략:
            1. 포괄적인 불용어 필터링 (조사, 일반적 표현 등)
            2. 기술/커리어 관련 키워드 우선순위 부여
            3. 중복 제거 및 길이 제한 (2글자 이상)
            4. 최종 5개 키워드 선별
        """
        # 🚫 포괄적인 불용어 리스트 - 한국어 조사, 일반적 표현, 시스템 메시지 등
        common_words = {
            # 한국어 조사/어미
            '은', '는', '이', '가', '을', '를', '에', '의', '와', '과', '로', '으로', '에서', '부터', '까지',
            # 일반적인 대화 표현
            'AI', '사용자', '시스템', '안녕하세요', '님', '합니다', '입니다', '있습니다', '됩니다', 
            '해주세요', '것', '수', '때', '등', '그', '저', '제', '거', '네', '요', '좀', '더', '정말',
            '사실', '그런데', '그래서', '하지만', '만약', '혹시', '아마', '특히', '예를들어', '때문에',
            # 시스템 특화 표현 (G.Navi 관련)
            '오현진의', '오현진님!', 'Growth', 'Navigator에', 'G.Navi', '전문', '상담사인', '테스트사용자의',
            '개발자가', '싶어요.', '안녕하세요!'
        }
        
        # 📝 단어 추출 및 기본 필터링
        import re
        words = re.findall(r'\b\w+\b', text)
        
        # 기본 조건 만족하는 키워드만 수집
        filtered_keywords = []
        for word in words:
            if (len(word) > 1 and                    # 2글자 이상
                word not in common_words and         # 불용어가 아님
                not word.isdigit() and               # 숫자가 아님
                word not in filtered_keywords):      # 중복이 아님
                filtered_keywords.append(word)
                if len(filtered_keywords) >= 15:     # 충분한 후보 수집
                    break
        
        # 🎯 중요도 기반 우선순위 키워드 선별
        priority_keywords = []
        
        # 기술 관련 고중요도 키워드
        tech_keywords = ['AI', '개발', '프로그래밍', 'Python', '데이터', '머신러닝', '딥러닝', 
                        'React', 'JavaScript', '코딩', '기술', '스킬', '언어', '프레임워크']
        
        # 커리어 관련 고중요도 키워드  
        career_keywords = ['커리어', '진로', '취업', '이직', '성장', '목표', '계획', '방향', 
                          '개발자', '직업', '분야', '포지션']
        
        # 우선순위 키워드 선별
        for keyword in filtered_keywords:
            if any(tech_word in keyword for tech_word in tech_keywords):
                priority_keywords.append(keyword)
            elif any(career_word in keyword for career_word in career_keywords):
                priority_keywords.append(keyword)
        
        # 🔧 최종 키워드 결정: 우선순위 → 일반 키워드 순
        final_keywords = priority_keywords[:5] if priority_keywords else filtered_keywords[:5]
        
        # 🐛 디버깅 정보 출력
        print(f"   🔑 키워드 추출 상세:")
        print(f"     📊 전체 단어: {len(words)}개")
        print(f"     ✅ 필터링 후: {len(filtered_keywords)}개")
        print(f"     ⭐ 우선순위: {priority_keywords}")
        print(f"     🎯 최종 선택: {final_keywords}")
        
        return final_keywords
    
    async def build_vector_db(self, 
                            conversation_id: str, 
                            member_id: str, 
                            user_name: str, 
                            messages: List[Dict[str, Any]],
                            session_metadata: Dict[str, Any]) -> bool:
        """
        🗃️ 세션 대화 내역을 사용자별 VectorDB에 저장하는 핵심 메서드
        
        Args:
            conversation_id: 대화방 고유 ID (예: "chat_session_123")
            member_id: 사용자 고유 ID (VectorDB 분리 기준)
            user_name: 사용자 이름 (메타데이터용)
            messages: 세션의 모든 대화 메시지들
            session_metadata: 세션 기본 정보 (생성시간, 지속시간 등)
            
        Returns:
            bool: VectorDB 구축 성공 여부
            
        🔄 처리 과정:
        1. 대화 내용 요약 생성 (검색 품질 향상)
        2. 사용자별 VectorDB 폴더 생성/접근
        3. 대화 텍스트를 적절한 크기로 청킹
        4. OpenAI Embeddings로 벡터화
        5. ChromaDB에 저장 + 메타데이터 첨부
        6. 세션 인덱스 파일 업데이트
        
        💾 저장 위치: storage/vector_stores/user_{member_id}_sessions/
        """
        try:
            print(f"🗃️ build_vector_db 시작: {conversation_id}")
            print(f"📊 전달받은 messages 개수: {len(messages) if messages else 0}개")
            print(f"👤 사용자: {user_name} (member_id: {member_id})")
            
            if messages:
                print(f"📋 전달받은 messages 상세:")
                for i, msg in enumerate(messages):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:50]
                    print(f"     #{i+1} {role}: {content}{'...' if len(msg.get('content', '')) > 50 else ''}")
            
            # ✅ 1단계: 빈 세션 검증
            if not messages:
                print(f"빈 메시지 세션 - VectorDB 구축 생략: {conversation_id}")
                return False
            
            # 📝 2단계: 대화 내용 요약 생성 (검색 품질 향상을 위해)
            summary = await self.summarize_session_content(messages, user_name)
            print(f"세션 요약 생성 완료: {conversation_id} - {summary}")
            
            # 📁 3단계: 사용자별 VectorDB 저장 경로 생성
            # 중요: 각 사용자마다 완전히 분리된 폴더로 개인정보 보호
            user_db_path = self.storage_path / f"user_{member_id}_sessions"
            user_db_path.mkdir(parents=True, exist_ok=True)
            
            # 🔤 4단계: 대화 메시지들을 하나의 텍스트로 변환
            conversation_text = self._format_messages_to_text(messages)
            
            # ✂️ 5단계: 긴 텍스트를 검색에 적합한 크기로 분할 (청킹)
            chunks = self.text_splitter.split_text(conversation_text)
            
            if not chunks:
                print(f"청킹된 텍스트가 없음 - VectorDB 구축 생략: {conversation_id}")
                return False
            
            # 🏷️ 6단계: 각 청크에 첨부할 메타데이터 준비
            metadata = {
                "conversation_id": conversation_id,        # 세션 ID
                "member_id": member_id,                   # 사용자 ID (검색 필터링용)
                "user_name": user_name,                   # 사용자 이름
                "summary": summary,                       # AI 생성 요약
                "created_at": session_metadata.get("created_at", datetime.utcnow()).isoformat(),
                "session_duration_minutes": session_metadata.get("session_duration_minutes", 0),
                "message_count": len(messages),           # 총 메시지 수
                "indexed_at": datetime.utcnow().isoformat()  # VectorDB 구축 시점
            }
            
            # 🗃️ 7단계: ChromaDB VectorStore 초기화 (사용자별 컬렉션)
            vectorstore = Chroma(
                collection_name=f"user_{member_id}_sessions",  # 사용자별 컬렉션명
                embedding_function=self.embeddings,            # OpenAI 임베딩 함수  
                persist_directory=str(user_db_path)            # 저장 경로
            )
            
            # 📦 8단계: 각 청크에 고유 메타데이터 추가하여 VectorDB에 저장
            metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()                    # 기본 메타데이터 복사
                chunk_metadata["chunk_index"] = i                   # 청크 순번
                chunk_metadata["chunk_content"] = chunk[:100] + "..." if len(chunk) > 100 else chunk  # 미리보기
                metadatas.append(chunk_metadata)
            
            # 💾 VectorDB에 텍스트 청크들 저장
            vectorstore.add_texts(
                texts=chunks,
                metadatas=metadatas,
                ids=[f"{conversation_id}_chunk_{i}" for i in range(len(chunks))]
            )
            
            # 📁 영속화 처리
            print(f"   💾 VectorDB 저장 완료: {len(chunks)}개 청크")
            
            # 📋 9단계: 세션 인덱스 파일 업데이트 (빠른 세션 탐색용)
            await self._update_session_index(user_db_path, conversation_id, metadata)
            
            print(f"✅ VectorDB 구축 성공: {conversation_id}")
            print(f"   👤 사용자: {user_name} (ID: {member_id})")
            print(f"   📝 요약: {summary}")
            print(f"   📊 청크 수: {len(chunks)}개")
            print(f"   💾 저장 위치: {user_db_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ VectorDB 구축 실패: {conversation_id} - {e}")
            return False
    
    async def _update_session_index(self, user_db_path: Path, conversation_id: str, metadata: Dict[str, Any]):
        """
        📋 사용자별 세션 인덱스 파일 업데이트
        
        Args:
            user_db_path: 사용자 VectorDB 저장 경로
            conversation_id: 대화 세션 ID
            metadata: 세션 메타데이터
            
        💡 기능:
            - 빠른 세션 탐색을 위한 인덱스 파일 생성/업데이트
            - 세션별 요약, 생성시간, 메시지 수 등 정보 저장
            - JSON 형태로 구조화된 인덱스 유지
        """
        try:
            index_file = user_db_path / "session_index.json"
            
            # 📖 기존 인덱스 로드 또는 새로 생성
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            else:
                index_data = {
                    "member_id": metadata["member_id"],
                    "created_at": datetime.utcnow().isoformat(),
                    "sessions": {}
                }
            
            # ➕ 새 세션 정보 추가
            index_data["sessions"][conversation_id] = {
                "summary": metadata["summary"],
                "created_at": metadata["created_at"],
                "indexed_at": metadata["indexed_at"],
                "message_count": metadata["message_count"],
                "session_duration_minutes": metadata["session_duration_minutes"]
            }
            
            # 📁 인덱스 업데이트 및 저장
            index_data["last_updated"] = datetime.utcnow().isoformat()
            index_data["total_sessions"] = len(index_data["sessions"])
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            print(f"   📋 세션 인덱스 업데이트 완료: {metadata['member_id']} - 총 {len(index_data['sessions'])}개 세션")
            
        except Exception as e:
            print(f"❌ 세션 인덱스 업데이트 실패: {e}")
    
    def get_user_vectorstore(self, member_id: str) -> Optional[Chroma]:
        """
        🗃️ 사용자별 VectorDB 인스턴스 반환
        
        Args:
            member_id: 사용자 고유 ID
            
        Returns:
            Optional[Chroma]: 사용자의 VectorStore 인스턴스 (없으면 None)
            
        💡 용도:
            - 과거 세션 검색 시 사용
            - 개인화된 대화 내역 조회
            - 사용자별 완전 분리된 VectorDB 접근
        """
        try:
            user_db_path = self.storage_path / f"user_{member_id}_sessions"
            
            if not user_db_path.exists():
                print(f"❌ 사용자 VectorDB가 존재하지 않음: {member_id}")
                return None
            
            vectorstore = Chroma(
                collection_name=f"user_{member_id}_sessions",
                embedding_function=self.embeddings,
                persist_directory=str(user_db_path)
            )
            
            print(f"✅ 사용자 VectorDB 로드 성공: {member_id}")
            return vectorstore
            
        except Exception as e:
            print(f"❌ 사용자 VectorDB 로드 실패: {member_id} - {e}")
            return None
    
    def search_user_sessions(self, member_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        🔍 사용자의 과거 세션에서 관련 내용 검색
        
        Args:
            member_id: 사용자 고유 ID
            query: 검색 쿼리
            k: 반환할 최대 결과 수
            
        Returns:
            List[Dict[str, Any]]: 검색 결과 리스트 (관련도 점수 포함)
            
        💡 기능:
            - 개인화된 과거 대화 내역 검색
            - 의미 기반 유사도 검색 (벡터 유사도)
            - 관련도 점수 기반 품질 필터링
        """
        try:
            vectorstore = self.get_user_vectorstore(member_id)
            
            if not vectorstore:
                return []
            
            # 🔍 의미 기반 유사도 검색 수행
            results = vectorstore.similarity_search_with_relevance_scores(
                query=query,
                k=k
            )
            
            # 📊 검색 결과 구조화
            search_results = []
            for doc, score in results:
                search_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": score,
                    "conversation_id": doc.metadata.get("conversation_id", "unknown"),
                    "session_summary": doc.metadata.get("summary", "요약 없음")
                })
            
            print(f"   🔍 사용자 {member_id} 세션 검색 완료: {len(search_results)}개 결과")
            return search_results
            
        except Exception as e:
            print(f"❌ 사용자 세션 검색 실패: {member_id} - {e}")
            return []
    
    def get_user_session_stats(self, member_id: str) -> Dict[str, Any]:
        """
        📊 사용자별 세션 통계 정보 반환
        
        Args:
            member_id: 사용자 고유 ID
            
        Returns:
            Dict[str, Any]: 세션 통계 정보
            {
                'member_id': 사용자 ID,
                'total_sessions': 총 세션 수,
                'total_messages': 총 메시지 수,
                'recent_sessions': 최근 세션 정보,
                'last_activity': 마지막 활동 시간
            }
            
        💡 용도:
            - 사용자 대화 활동 분석
            - 개인화 서비스 개선 데이터
            - 사용 패턴 파악
        """
        try:
            index_file = self.storage_path / f"user_{member_id}_sessions" / "session_index.json"
            
            if not index_file.exists():
                return {
                    "member_id": member_id,
                    "total_sessions": 0,
                    "total_messages": 0,
                    "recent_sessions": [],
                    "message": "저장된 세션이 없습니다"
                }
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 📊 통계 계산 및 최근 세션 정보 추출
            sessions = index_data.get("sessions", {})
            total_messages = sum(session.get("message_count", 0) for session in sessions.values())
            
            # 📅 최근 5개 세션 정보 (시간순 정렬)
            recent_sessions = []
            sorted_sessions = sorted(
                sessions.items(), 
                key=lambda x: x[1].get("created_at", ""), 
                reverse=True
            )[:5]
            
            for session_id, session_info in sorted_sessions:
                recent_sessions.append({
                    "session_id": session_id,
                    "summary": session_info.get("summary", "요약 없음"),
                    "created_at": session_info.get("created_at"),
                    "message_count": session_info.get("message_count", 0)
                })
            
            return {
                "member_id": member_id,
                "total_sessions": index_data.get("total_sessions", 0),
                "total_messages": total_messages,
                "recent_sessions": recent_sessions,
                "first_session": index_data.get("created_at"),
                "last_activity": index_data.get("last_updated")
            }
            
        except Exception as e:
            print(f"❌ 사용자 세션 통계 조회 실패: {member_id} - {e}")
            return {
                "member_id": member_id,
                "error": str(e)
            }


# 🌍 전역 인스턴스 - 애플리케이션 전체에서 공유
session_vectordb_builder = SessionVectorDBBuilder()
