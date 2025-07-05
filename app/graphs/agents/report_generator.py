# app/graphs/agents/report_generator.py
"""
* @className : ReportGeneratorAgent
* @description : 보고서 생성 에이전트 모듈
*                관리자용 상세 보고서를 생성하는 에이전트입니다.
*                사용자 상담 내용과 AI 응답을 종합하여 분석 리포트를 작성합니다.
*
* @modification : 2025.07.01(이재원) 최초생성
*
* @author 이재원
* @Date 2025.07.01
* @version 1.0
* @see HTML, Report
*  == 개정이력(Modification Information) ==
*  
*   수정일        수정자        수정내용
*   ----------   --------     ---------------------------
*   2025.07.01   이재원       최초 생성
*  
* Copyright (C) by G-Navi AI System All right reserved.
"""

import os
import logging
import markdown
from datetime import datetime
from typing import Dict, Any, Optional


class ReportGeneratorAgent:
    """
    🔒 관리자 전용 HTML 보고서 생성 에이전트
    
    상담 품질 관리를 위해 상담 내용을 체계적으로 정리한
    HTML 보고서를 생성하는 관리자 전용 에이전트입니다.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def should_generate_report(self, user_question: str, user_data: Dict[str, Any]) -> bool:
        """
        🔒 관리자 설정: 보고서 생성 필요 여부 판단
        
        관리자가 설정한 조건에 따라 HTML 보고서 생성 여부를 결정합니다.
        현재는 모든 상담에 대해 보고서를 생성하도록 설정되어 있습니다.
        
        Args:
            user_question: 사용자 질문
            user_data: 사용자 프로필 정보
            
        Returns:
            bool: 보고서 생성 필요 여부
        """
        return True # 🔒 관리자 설정: 현재 모든 상담에 대해 보고서 생성 (관리자용)

        # 🔒 관리자 설정 예시 (현재 비활성화됨):
        # 보고서 생성 키워드들
        report_keywords = [
            "보고서", "report", "리포트", "문서", "저장", "다운로드", 
            "파일", "html", "정리", "요약서", "분석서", "결과서"
        ]
        
        question_lower = user_question.lower()
        
        # 키워드 매칭 확인
        for keyword in report_keywords:
            if keyword in question_lower:
                self.logger.info(f"보고서 생성 키워드 감지: '{keyword}'")
                return True
        
        # 질문이 길고 상세한 분석을 요청하는 경우 (100자 이상)
        if len(user_question) > 100:
            self.logger.info("상세한 질문으로 보고서 생성 추천")
            return True
            
        return False
    
    def generate_html_report(self, 
                           final_response: Dict[str, Any], 
                           user_data: Dict[str, Any],
                           state: Dict[str, Any]) -> Optional[str]:
        """🔒 관리자 전용: HTML 보고서 파일 생성"""
        try:
            self.logger.info("HTML 보고서 생성 시작")
            
            # 마크다운 내용을 HTML로 변환
            markdown_content = final_response.get("formatted_content", "")
            
            # 커리어 상담인 경우 message 키 사용
            if not markdown_content and final_response.get("message"):
                markdown_content = final_response.get("message", "")
            
            # 빈 내용인 경우 보고서 생성하지 않음
            if not markdown_content or len(markdown_content.strip()) < 10:
                self.logger.warning("보고서 내용이 너무 짧아 생성을 건너뜁니다.")
                return None
                
            html_content = self._convert_markdown_to_html(markdown_content)
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            user_name = user_data.get("name", "user")
            user_name = user_name.replace(" ", "_") if user_name else "user"
            file_name = f"{user_name}_{timestamp}"
            
            # output 디렉토리 생성
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # HTML 파일 경로
            html_path = os.path.join(output_dir, f"{file_name}.html")
            
            # HTML 파일 작성
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            self.logger.info(f"HTML 보고서 생성 완료: {html_path}")
            return html_path
            
        except Exception as e:
            self.logger.error(f"HTML 보고서 생성 실패: {e}")
            return None
    
    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """마크다운 텍스트를 HTML로 변환 (Mermaid 다이어그램 지원)"""
        try:
            # Mermaid 다이어그램 코드 블록을 HTML div로 변환
            mermaid_html = self._process_mermaid_blocks(markdown_text)
            
            # 기본 마크다운 변환
            html = markdown.markdown(
                mermaid_html,
                extensions=['tables', 'fenced_code', 'codehilite'],
                extension_configs={
                    'codehilite': {
                        'css_class': 'highlight'
                    }
                }
            )
            
            # Mermaid가 포함되어 있는지 확인
            has_mermaid = 'class="mermaid"' in html
            
            # 완전한 HTML 문서로 감싸기
            full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>G.Navi AI 커리어 컨설팅 보고서</title>
    {self._get_mermaid_scripts() if has_mermaid else ""}
    <style>
        body {{
            font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: #fafafa;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 30px;
        }}
        h3 {{
            color: #5a6c7d;
            margin-top: 25px;
        }}
        p {{
            margin-bottom: 15px;
        }}
        ul, ol {{
            margin-bottom: 20px;
            padding-left: 25px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        strong {{
            color: #2c3e50;
        }}
        em {{
            color: #7f8c8d;
        }}
        blockquote {{
            border-left: 4px solid #bdc3c7;
            padding-left: 20px;
            margin: 20px 0;
            font-style: italic;
            color: #7f8c8d;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        code {{
            background-color: #f1f2f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
        }}
        pre {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 15px 0;
        }}
        .timestamp {{
            text-align: right;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .highlight {{
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #ffc107;
            margin: 15px 0;
        }}
        /* Mermaid 다이어그램 스타일 */
        .mermaid {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        .diagram-title {{
            text-align: center;
            font-weight: bold;
            color: #495057;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html}
        <div class="timestamp">
            보고서 생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}
        </div>
    </div>
    {self._get_mermaid_init_script() if has_mermaid else ""}
</body>
</html>"""
            
            return full_html
            
        except Exception as e:
            self.logger.error(f"마크다운 HTML 변환 실패: {e}")
            # 실패 시 기본 HTML 반환
            return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>G.Navi AI 보고서</title>
</head>
<body>
    <pre>{markdown_text}</pre>
</body>
</html>"""
    
    def _process_mermaid_blocks(self, markdown_text: str) -> str:
        """마크다운에서 Mermaid 코드 블록을 HTML div로 변환"""
        try:
            import re
            
            # ```mermaid 코드 블록을 찾아서 div로 변환
            pattern = r'```mermaid\s*\n(.*?)\n```'
            
            def replace_mermaid(match):
                mermaid_code = match.group(1).strip()
                # HTML div로 변환 (Mermaid.js가 렌더링할 수 있도록)
                return f'<div class="mermaid">\n{mermaid_code}\n</div>'
            
            # 정규표현식으로 변환
            processed_text = re.sub(pattern, replace_mermaid, markdown_text, flags=re.DOTALL)
            
            return processed_text
            
        except Exception as e:
            self.logger.warning(f"Mermaid 블록 처리 실패: {e}")
            return markdown_text

    def _get_mermaid_scripts(self) -> str:
        """Mermaid.js 스크립트 태그 반환"""
        return """
    <!-- Mermaid.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
"""

    def _get_mermaid_init_script(self) -> str:
        """Mermaid 초기화 스크립트 반환"""
        return """
    <script>
        // Mermaid 초기화
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            themeVariables: {
                primaryColor: '#3498db',
                primaryTextColor: '#2c3e50',
                primaryBorderColor: '#3498db',
                lineColor: '#34495e',
                backgroundColor: '#ffffff',
                secondaryColor: '#ecf0f1',
                tertiaryColor: '#f8f9fa'
            },
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true
            },
            sequence: {
                useMaxWidth: true,
                wrap: true
            },
            timeline: {
                useMaxWidth: true
            }
        });
        
        // 페이지 로드 완료 후 Mermaid 렌더링
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Mermaid 다이어그램 렌더링 시작...');
            mermaid.run();
        });
    </script>
"""