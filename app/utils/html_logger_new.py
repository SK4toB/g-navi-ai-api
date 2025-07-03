# app/utils/html_logger.py
"""
커리어 상담 노드 응답을 HTML로 저장하는 간단한 유틸리티
"""

import os
import re
from datetime import datetime
from typing import Dict, Any


def markdown_to_html(text: str) -> str:
    """간단한 Markdown을 HTML로 변환 (깔끔하고 읽기 쉬운 레이아웃)"""
    if not text:
        return ""
    
    # 먼저 기본 마크다운 요소 처리
    html = text
    
    # **굵은 글씨** 처리
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    # *기울임* 처리  
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    # `인라인 코드` 처리
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    
    # 줄 단위로 처리
    lines = html.split('\n')
    html_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        
        # 빈 줄 건너뛰기 (불필요한 간격 제거)
        if not line:
            continue
        
        # 제목 처리
        if line.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('# '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h1>{line[2:]}</h1>')
        # 리스트 처리
        elif line.startswith('- '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            content = line[2:]
            html_lines.append(f'<li>{content}</li>')
        # 일반 텍스트 처리
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<p>{line}</p>')
    
    # 리스트가 열려있으면 닫기
    if in_list:
        html_lines.append('</ul>')
    
    return '\n'.join(html_lines)


def save_career_response_to_html(stage: str, response_data: Dict[str, Any], session_id: str = "unknown"):
    """커리어 상담 응답을 HTML 파일로 저장 (Mermaid 다이어그램 포함)"""
    try:
        # output 폴더 생성
        output_dir = "/Users/ijaewon/4toB/g-navi-ai-api/output"
        os.makedirs(output_dir, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"career_response_{stage}_{timestamp}_{session_id[:8]}.html"
        filepath = os.path.join(output_dir, filename)
        
        # 메시지 추출 및 HTML 변환
        message = response_data.get("message", "메시지 없음")
        html_message = markdown_to_html(message)
        
        # Mermaid 다이어그램 처리
        mermaid_diagram = response_data.get("mermaid_diagram", "")
        mermaid_section = ""
        
        if mermaid_diagram:
            mermaid_section = f"""
    <div class="mermaid-container">
        <h3>🎯 커리어 경로 시각화</h3>
        <div class="mermaid">
{mermaid_diagram}
        </div>
    </div>
            """
        
        # HTML 템플릿 - Mermaid.js 포함
        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>커리어 상담 응답 - {stage}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #ffffff;
            color: #333;
            line-height: 1.5;
        }}
        .content {{
            padding: 0;
        }}
        .content h1, .content h2, .content h3 {{
            color: #2c3e50;
            margin-top: 1em;
            margin-bottom: 0.5em;
            font-weight: 600;
        }}
        .content h1 {{
            font-size: 1.6em;
        }}
        .content h2 {{
            font-size: 1.4em;
            border-bottom: 1px solid #eee;
            padding-bottom: 0.3em;
        }}
        .content h3 {{
            font-size: 1.2em;
        }}
        .content ul {{
            padding-left: 1.5em;
            margin: 0.5em 0;
        }}
        .content li {{
            margin: 0.2em 0;
        }}
        .content p {{
            margin: 0.5em 0;
        }}
        .content code {{
            background: #f4f4f4;
            padding: 0.1em 0.3em;
            border-radius: 3px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9em;
        }}
        .content pre {{
            background: #f8f8f8;
            padding: 1em;
            border-radius: 5px;
            border-left: 3px solid #ddd;
            overflow-x: auto;
            margin: 1em 0;
        }}
        .content strong {{
            font-weight: 600;
        }}
        .content em {{
            font-style: italic;
        }}
        .mermaid-container {{
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            background: #f8fafc;
        }}
        .mermaid-container h3 {{
            margin-top: 0;
            margin-bottom: 10px;
            color: #1a202c;
            font-size: 1.3em;
        }}
        .mermaid {{
            text-align: center;
            background: white;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="content">
        {html_message}
        {mermaid_section}
    </div>
    
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true
            }}
        }});
    </script>
</body>
</html>
        """
        
        # 파일 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"💾 커리어 상담 응답 HTML 저장: {filename}")
        
    except Exception as e:
        print(f"❌ HTML 저장 실패: {e}")


def save_simple_log(stage: str, message: str, session_id: str = "unknown"):
    """간단한 텍스트 로그도 함께 저장 (백업용)"""
    try:
        output_dir = "/Users/ijaewon/4toB/g-navi-ai-api/output"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(output_dir, "career_consultation_log.txt")
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"세션: {session_id}\n")
            f.write(f"단계: {stage}\n")
            f.write(f"{'='*50}\n")
            f.write(f"{message[:200]}...\n")
            
    except Exception as e:
        print(f"❌ 텍스트 로그 저장 실패: {e}")
