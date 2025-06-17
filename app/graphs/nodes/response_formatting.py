# app/graphs/nodes/response_formatting.py
# 적응적 응답 포맷팅 노드

import json
import logging
import os
import markdown
from datetime import datetime
from app.graphs.state import ChatState
from app.graphs.agents.formatter import ResponseFormattingAgent


class ResponseFormattingNode:
    """적응적 응답 포맷팅 노드"""

    def __init__(self, graph_builder_instance):
        self.graph_builder = graph_builder_instance
        self.response_formatting_agent = ResponseFormattingAgent()
        self.logger = logging.getLogger(__name__)

    def format_response_node(self, state: ChatState) -> ChatState:
        """4단계: 적응적 응답 포맷팅"""
        start_time = datetime.now()
        try:
            self.logger.info("=== 4단계: 적응적 응답 포맷팅 ===")
            
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
            user_data = self.graph_builder.get_user_info_from_session(state)
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
            
            # AI 응답을 current_session_messages에 추가하여 MemorySaver가 저장하도록 함
            if "current_session_messages" not in state:
                state["current_session_messages"] = []
            
            assistant_message = {
                "role": "assistant",
                "content": final_response.get("formatted_content", ""),
                "timestamp": datetime.now().isoformat(),
                "format_type": final_response.get("format_type", "adaptive")
            }
            state["current_session_messages"].append(assistant_message)
            self.logger.info(f"AI 응답을 current_session_messages에 추가 (총 {len(state['current_session_messages'])}개 메시지)")
            
            self.logger.info(f"HTML 파일 저장 완료: {html_path}")
            self.logger.info("적응적 응답 포맷팅 완료")
            
        except Exception as e:
            error_msg = f"응답 포맷팅 실패: {e}"
            self.logger.error(error_msg)
            state["error_messages"].append(error_msg)
            state["final_response"] = {"error": str(e)}
        
        processing_time = (datetime.now() - start_time).total_seconds()
        state["processing_log"].append(f"4단계 처리 시간: {processing_time:.2f}초")
        
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
