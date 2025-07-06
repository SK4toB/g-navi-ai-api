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
    
    # 최우선 특수 케이스: 사용자가 제시한 정확한 형식
    exact_pattern = r'(위 다이어그램은 경로 전환 과정을 구조적으로 시각화한 것입니다\.)\s*## (선택 안내) (위 방향성.+?번호를 명시하여 답변해 주시기 바랍니다\.)'
    match = re.search(exact_pattern, text, re.DOTALL)
    if match:
        diagram_desc = match.group(1)
        title = match.group(2)
        content = match.group(3)
        
        # 리스트 항목 추출 및 처리
        list_items_html = '<ul>'
        for item in re.findall(r'-\s*"([^"]+)"', content):
            list_items_html += f'<li>"{item}"</li>'
        list_items_html += '</ul>'
        
        # 남은 텍스트에서 리스트 항목 제거
        remaining_text = re.sub(r'-\s*"[^"]+"', '', content).strip()
        
        # 처리된 HTML 생성
        replacement = f'<p>{diagram_desc}</p>\n<h2>{title}</h2>\n<p>{remaining_text}</p>\n{list_items_html}'
        
        # 원래 텍스트를 HTML로 교체
        text = text.replace(match.group(0), replacement)
    
    # 특수 케이스: '위 다이어그램은 경로 전환 과정을 구조적으로 시각화한 것입니다.' 뒤에 제목이 오는 경우
    special_case = r'(위 다이어그램은 경로 전환 과정을 구조적으로 시각화한 것입니다\.)\s*##\s+(선택 안내)\s+(.*?)(-\s*".*?".*?-\s*".*?")'
    match = re.search(special_case, text, re.DOTALL)
    if match:
        diagram_desc = match.group(1)
        title = match.group(2)
        middle_text = match.group(3).strip()
        list_items = match.group(4)
        
        # 처리된 HTML 생성
        diagram_html = f'<p>{diagram_desc}</p>'
        title_html = f'<h2>{title}</h2>'
        middle_html = f'<p>{middle_text}</p>'
        
        # 리스트 항목 처리
        list_items_html = '<ul>'
        for item in re.findall(r'-\s*"([^"]+)"', list_items):
            list_items_html += f'<li>"{item}"</li>'
        list_items_html += '</ul>'
        
        # 원래 텍스트를 HTML로 교체
        text = text.replace(match.group(0), f"{diagram_html}\n{title_html}\n{middle_html}\n{list_items_html}")
    
    # 마크다운 제목과 바로 이어지는 텍스트 패턴
    inline_heading_pattern = r'(#{1,3})\s+([^\n]+?)(\s+\S+.*)'
    for m in re.finditer(inline_heading_pattern, text):
        hashes = m.group(1)
        heading_text = m.group(2).strip()
        content = m.group(3)
        level = len(hashes)
        
        replacement = f'<h{level}>{heading_text}</h{level}><p>{content}'
        text = text.replace(m.group(0), replacement)
    
    # 이후 기본 마크다운 처리는 그대로 진행
    html = text
    
    # 1. ```mermaid ... ``` 형식 - 비탐욕적(non-greedy) 매칭으로 수정
    mermaid_pattern = r'```mermaid\s+(.*?)\s*```'
    mermaid_blocks = re.findall(mermaid_pattern, html, re.DOTALL)
    for i, mermaid_content in enumerate(mermaid_blocks):
        mermaid_html = f'''
<div class="mermaid-container">
    <div class="mermaid">
{mermaid_content}
    </div>
</div>
'''
        # 정확한 형태를 찾기 위해 여러 패턴 시도
        original_block = f"```mermaid\n{mermaid_content}```"
        if original_block in html:
            html = html.replace(original_block, mermaid_html, 1)
        else:
            # 줄바꿈이나 공백이 다를 수 있으므로 다른 패턴도 시도
            original_block_alt = f"```mermaid\r\n{mermaid_content}```"
            if original_block_alt in html:
                html = html.replace(original_block_alt, mermaid_html, 1)
            else:
                # 정규식으로 패턴 찾기 - 비탐욕적 매칭 사용
                pattern = re.compile(r'```mermaid\s+(.*?)\s*```', re.DOTALL)
                html = pattern.sub(mermaid_html, html, 1)
    
    # 2. `mermaid ... ` 형식 (백틱 하나만 사용) - 비탐욕적(non-greedy) 매칭으로 수정
    single_backtick_pattern = r'`mermaid\s+(.*?)\s*`'
    single_backtick_blocks = re.findall(single_backtick_pattern, html, re.DOTALL)
    for i, mermaid_content in enumerate(single_backtick_blocks):
        mermaid_html = f'''
<div class="mermaid-container">
    <div class="mermaid">
{mermaid_content}
    </div>
</div>
'''
        # 정확한 형태를 찾기 위해 여러 패턴 시도
        original_block = f"`mermaid\n{mermaid_content}`"
        if original_block in html:
            html = html.replace(original_block, mermaid_html, 1)
        else:
            # 줄바꿈이나 공백이 다를 수 있으므로 다른 패턴도 시도
            original_block_alt = f"`mermaid\r\n{mermaid_content}`"
            if original_block_alt in html:
                html = html.replace(original_block_alt, mermaid_html, 1)
            else:
                # 정규식으로 패턴 찾기 - 비탐욕적 매칭 사용
                pattern = re.compile(r'`mermaid\s+(.*?)\s*`', re.DOTALL)
                html = pattern.sub(mermaid_html, html, 1)
    
    # 구분선 처리 (---, ___, ***) - 다이어그램 뒤에 오는 구분선 처리
    # 패턴 개선: "--- ## 제목" 형태도 처리할 수 있도록
    # 우선 일반 구분선 패턴 처리
    html = re.sub(r'(?m)^\s*---\s*$', '<hr>', html)
    html = re.sub(r'(?m)^\s*___\s*$', '<hr>', html)
    html = re.sub(r'(?m)^\s*\*\*\*\s*$', '<hr>', html)
    
    # 특별 패턴: "--- ## 제목" 같은 형식 처리
    special_pattern = r'---\s+##\s+([^\n]+)'
    for match in re.finditer(special_pattern, html):
        full_match = match.group(0)
        title = match.group(1)
        replacement = f'<hr>\n<h2>{title}</h2>'
        html = html.replace(full_match, replacement)
    
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
    in_mermaid_container = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # mermaid 컨테이너 내부인 경우 그대로 추가
        if in_mermaid_container:
            html_lines.append(line)
            if "</div>" in line and "mermaid-container" in line:
                in_mermaid_container = False
            i += 1
            continue
        
        # mermaid 컨테이너 시작 확인
        if '<div class="mermaid-container">' in line:
            in_mermaid_container = True
            html_lines.append(line)
            i += 1
            continue
        
        # 이미 HTML로 변환된 요소는 그대로 추가
        if line.startswith('<h') or line.startswith('<p>') or line.startswith('<ul>') or line.startswith('<li>') or line.startswith('<hr>'):
            html_lines.append(line)
            i += 1
            continue
        
        line_stripped = line.strip()
        
        # 빈 줄 처리
        if not line_stripped:
            # 빈 줄이 리스트 중간에 있으면 리스트 종료로 처리
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            i += 1
            continue
        
        # 제목 처리
        if re.match(r'^#{1,3}\s+.+', line_stripped) and not '<h' in line:
            match = re.match(r'^(#{1,3})\s+(.+)', line_stripped)
            if match:
                level = len(match.group(1))
                title_content = match.group(2)
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(f'<h{level}>{title_content}</h{level}>')
                i += 1
                continue
                
        # 구분선 처리
        if line_stripped == '---' or line_stripped == '___' or line_stripped == '***':
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<hr>')
            i += 1
            continue
        
        # 리스트 처리
        if line_stripped.startswith('- ') and not '<li>' in line:
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            content = line_stripped[2:]
            html_lines.append(f'<li>{content}</li>')
            i += 1
            continue
            
        # 일반 텍스트 처리 (이미 HTML 태그가 없는 경우만)
        if not re.search(r'<[^>]+>', line):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<p>{line}</p>')
            i += 1
            continue
            
        # 이외의 경우는 그대로 추가
        html_lines.append(line)
        i += 1
    
    # 리스트가 열려있으면 닫기
    if in_list:
        html_lines.append('</ul>')

    return '\n'.join(html_lines)


def save_career_response_to_html(stage: str, response_data: Dict[str, Any], session_id: str = "unknown"):
    """커리어 상담 응답을 HTML 파일로 저장 (Mermaid 다이어그램 포함)"""
    try:
        # output 폴더 생성 (작업 디렉토리 기준)
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"career_response_{stage}_{timestamp}_{session_id[:8]}.html"
        filepath = os.path.join(output_dir, filename)
        
        # 메시지 추출 및 HTML 변환
        message = response_data.get("message", "메시지 없음")
        html_message = markdown_to_html(message)
        
        # 메시지에 이미 Mermaid 다이어그램이 포함되어 있는지 확인
        mermaid_already_included = "```mermaid" in message or "`mermaid" in message or '<div class="mermaid">' in html_message
        
        # Mermaid 다이어그램 처리 - 메시지에 이미 포함되어 있지 않은 경우에만 추가
        mermaid_diagram = response_data.get("mermaid_diagram", "")
        mermaid_section = ""
        
        if mermaid_diagram and not mermaid_already_included:
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
        output_dir = os.path.join(os.getcwd(), "output")
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
