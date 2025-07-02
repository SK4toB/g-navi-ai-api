# app/utils/html_logger.py
"""
커리어 상담 노드 응답을 HTML로 저장하는 간단한 유틸리티
"""

import os
import re
from datetime import datetime
from typing import Dict, Any


def markdown_to_html(text: str) -> str:
    """간단한 Markdown을 HTML로 변환"""
    # 개행 문자를 <br>로 변환
    html = text.replace('\n', '<br>')
    
    # **굵은 글씨**를 <strong>으로 변환
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    
    # *기울임*을 <em>으로 변환
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    
    # # 제목들을 헤딩으로 변환
    html = re.sub(r'<br>### (.*?)<br>', r'<br><h3>\1</h3><br>', html)
    html = re.sub(r'<br>## (.*?)<br>', r'<br><h2>\1</h2><br>', html)
    html = re.sub(r'<br># (.*?)<br>', r'<br><h1>\1</h1><br>', html)
    
    # 시작 부분의 제목 처리
    html = re.sub(r'^### (.*?)<br>', r'<h3>\1</h3><br>', html)
    html = re.sub(r'^## (.*?)<br>', r'<h2>\1</h2><br>', html)
    html = re.sub(r'^# (.*?)<br>', r'<h1>\1</h1><br>', html)
    
    # - 리스트를 <ul><li>로 변환
    lines = html.split('<br>')
    result_lines = []
    in_list = False
    
    for line in lines:
        if line.strip().startswith('- '):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            result_lines.append(f'<li>{line.strip()[2:]}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(line)
    
    if in_list:
        result_lines.append('</ul>')
    
    html = '<br>'.join(result_lines)
    
    # ```코드블록``` 처리
    html = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    
    # `인라인 코드` 처리
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    
    # 연속된 <br> 정리
    html = re.sub(r'(<br>){3,}', r'<br><br>', html)
    
    return html


def save_career_response_to_html(stage: str, response_data: Dict[str, Any], session_id: str = "unknown"):
    """커리어 상담 응답을 HTML 파일로 저장"""
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
        
        # HTML 템플릿
        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>커리어 상담 응답 - {stage}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
            background: #f8f9fa;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .content {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            line-height: 1.7;
        }}
        .content h1, .content h2, .content h3 {{
            color: #343a40;
            margin-top: 25px;
            margin-bottom: 15px;
        }}
        .content h2 {{
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 8px;
        }}
        .content ul {{
            padding-left: 25px;
            margin: 15px 0;
        }}
        .content li {{
            margin: 8px 0;
        }}
        .content code {{
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            color: #e83e8c;
        }}
        .content pre {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            overflow-x: auto;
            margin: 15px 0;
        }}
        .content strong {{
            color: #495057;
            font-weight: 600;
        }}
        .meta {{
            background: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
            font-size: 0.9em;
            color: #6c757d;
        }}
        .stage {{
            color: #495057;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 G.Navi 커리어 상담</h1>
        <div class="stage">{stage} 단계</div>
    </div>
    
    <div class="content">
        {html_message}
    </div>
    
    <div class="meta">
        <strong>생성 시간:</strong> {datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")}<br>
        <strong>세션 ID:</strong> {session_id}<br>
        <strong>상담 단계:</strong> {stage}<br>
        <strong>파일명:</strong> {filename}
    </div>
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
