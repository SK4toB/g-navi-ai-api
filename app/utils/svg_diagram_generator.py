# app/utils/svg_diagram_generator.py
"""
SVG 기반 성장 방향 다이어그램 생성기
최소한의 기능으로 가볍게 구현
"""

from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET

class GrowthDiagramGenerator:
    """성장 방향 다이어그램 SVG 생성기"""
    
    def __init__(self):
        self.width = 600
        self.height = 400
        self.padding = 30
        
        # 모던한 색상 팔레트
        self.colors = {
            'current': '#3B82F6',      # 현재 위치 (모던 블루)
            'target': '#10B981',       # 목표 (에메랄드)
            'path': '#F59E0B',         # 경로 (앰버)
            'skill': '#8B5CF6',        # 스킬 (바이올렛)
            'background': '#FFFFFF',   # 깔끔한 화이트
            'text': '#1F2937',         # 다크 그레이
            'text_light': '#6B7280',   # 라이트 그레이
            'border': '#E5E7EB',       # 연한 보더
            'shadow': '#00000010',     # 그림자
            'hover': '#F3F4F6'         # 호버 배경
        }
    
    def generate_career_path_diagram(self, data: Dict[str, Any]) -> str:
        """커리어 패스 다이어그램 생성 - 미니멀 모던 스타일"""
        current_role = data.get('current_role', '현재 역할')
        target_role = data.get('target_role', '목표 역할')
        steps = data.get('steps', [])
        skills = data.get('skills', [])
        
        # SVG 루트 생성
        svg = ET.Element('svg', {
            'width': str(self.width),
            'height': str(self.height),
            'xmlns': 'http://www.w3.org/2000/svg',
            'style': f'background-color: {self.colors["background"]}; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;'
        })
        
        # CSS 스타일 추가
        self._add_styles(svg)
        
        # 제목 추가 (더 간결하게)
        title = ET.SubElement(svg, 'text', {
            'x': str(self.width // 2),
            'y': '25',
            'text-anchor': 'middle',
            'fill': self.colors['text'],
            'font-size': '16',
            'font-weight': '600',
            'class': 'title'
        })
        title.text = f"{current_role} → {target_role}"
        
        # 현재 위치와 목표 위치 그리기 (더 작고 모던하게)
        self._draw_modern_role_box(svg, current_role, 60, 70, self.colors['current'], True)
        self._draw_modern_role_box(svg, target_role, 420, 70, self.colors['target'], False)
        
        # 모던한 화살표 그리기
        self._draw_modern_arrow(svg, 180, 90, 400, 90, self.colors['path'])
        
        # 중간 단계들 그리기 (더 컴팩트하게)
        if steps:
            self._draw_compact_steps(svg, steps, 80, 160)
        
        # 필요 스킬들 그리기 (더 심플하게)
        if skills:
            self._draw_compact_skills(svg, skills, 80, 260)
        
        return ET.tostring(svg, encoding='unicode')
    
    def generate_skill_development_diagram(self, data: Dict[str, Any]) -> str:
        """스킬 개발 다이어그램 생성 - 미니멀 모던 스타일"""
        skills = data.get('skills', [])
        
        # SVG 루트 생성
        svg = ET.Element('svg', {
            'width': str(self.width),
            'height': str(min(self.height, 60 + len(skills[:6]) * 50)),  # 동적 높이
            'xmlns': 'http://www.w3.org/2000/svg',
            'style': f'background-color: {self.colors["background"]}; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;'
        })
        
        # CSS 스타일 추가
        self._add_styles(svg)
        
        # 제목 추가
        title = ET.SubElement(svg, 'text', {
            'x': str(self.width // 2),
            'y': '25',
            'text-anchor': 'middle',
            'fill': self.colors['text'],
            'font-size': '16',
            'font-weight': '600',
            'class': 'title'
        })
        title.text = "스킬 개발 로드맵"
        
        # 스킬들을 레벨별로 그리기 (최대 6개)
        y_start = 50
        for i, skill in enumerate(skills[:6]):
            self._draw_modern_skill_bar(svg, skill, 40, y_start + i * 50, i)
        
        return ET.tostring(svg, encoding='unicode')
    
    def _add_styles(self, svg: ET.Element):
        """CSS 스타일 추가 - 호버 효과 포함"""
        style = ET.SubElement(svg, 'style')
        style.text = """
        .role-box { transition: all 0.3s ease; cursor: pointer; }
        .role-box:hover { filter: brightness(1.1); transform: translateY(-2px); }
        .role-box:hover .shadow { opacity: 0.2; }
        
        .step-item { transition: all 0.2s ease; cursor: pointer; }
        .step-item:hover { transform: scale(1.05); }
        .step-item:hover .step-bg { fill: #F3F4F6; }
        
        .skill-item { transition: all 0.2s ease; cursor: pointer; }
        .skill-item:hover { transform: translateX(5px); }
        .skill-item:hover .skill-bg { fill: #F9FAFB; }
        
        .skill-bar { transition: all 0.3s ease; }
        .skill-bar:hover { transform: scaleY(1.1); }
        
        .title { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .label { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        
        .tooltip { visibility: hidden; opacity: 0; transition: all 0.2s; }
        .tooltipped:hover .tooltip { visibility: visible; opacity: 1; }
        """
    
    def _draw_role_box(self, svg: ET.Element, text: str, x: int, y: int, color: str, is_current: bool):
        """역할 박스 그리기"""
        # 박스 그리기
        rect = ET.SubElement(svg, 'rect', {
            'x': str(x),
            'y': str(y),
            'width': '140',
            'height': '50',
            'fill': color,
            'stroke': self.colors['border'],
            'stroke-width': '2',
            'rx': '5'
        })
        
        # 텍스트 추가
        text_elem = ET.SubElement(svg, 'text', {
            'x': str(x + 70),
            'y': str(y + 30),
            'text-anchor': 'middle',
            'fill': 'white',
            'font-family': 'Arial, sans-serif',
            'font-size': '12',
            'font-weight': 'bold'
        })
        text_elem.text = text
        
        # 현재 위치 표시
        if is_current:
            indicator = ET.SubElement(svg, 'text', {
                'x': str(x + 70),
                'y': str(y - 10),
                'text-anchor': 'middle',
                'fill': self.colors['text'],
                'font-family': 'Arial, sans-serif',
                'font-size': '10'
            })
            indicator.text = "현재"
    
    def _draw_arrow(self, svg: ET.Element, x1: int, y1: int, x2: int, y2: int, color: str):
        """화살표 그리기"""
        # 선 그리기
        line = ET.SubElement(svg, 'line', {
            'x1': str(x1),
            'y1': str(y1),
            'x2': str(x2 - 10),
            'y2': str(y2),
            'stroke': color,
            'stroke-width': '3',
            'marker-end': 'url(#arrowhead)'
        })
        
        # 화살표 마커 정의
        defs = svg.find('defs')
        if defs is None:
            defs = ET.SubElement(svg, 'defs')
        
        marker = ET.SubElement(defs, 'marker', {
            'id': 'arrowhead',
            'markerWidth': '10',
            'markerHeight': '7',
            'refX': '9',
            'refY': '3.5',
            'orient': 'auto'
        })
        
        polygon = ET.SubElement(marker, 'polygon', {
            'points': '0 0, 10 3.5, 0 7',
            'fill': color
        })
    
    def _draw_steps(self, svg: ET.Element, steps: List[str], x: int, y: int):
        """중간 단계들 그리기"""
        title = ET.SubElement(svg, 'text', {
            'x': str(x),
            'y': str(y),
            'fill': self.colors['text'],
            'font-family': 'Arial, sans-serif',
            'font-size': '14',
            'font-weight': 'bold'
        })
        title.text = "성장 단계"
        
        for i, step in enumerate(steps[:4]):  # 최대 4개까지만
            # 단계 번호 원
            circle = ET.SubElement(svg, 'circle', {
                'cx': str(x + 15),
                'cy': str(y + 30 + i * 25),
                'r': '10',
                'fill': self.colors['path'],
                'stroke': self.colors['border'],
                'stroke-width': '1'
            })
            
            # 단계 번호
            number = ET.SubElement(svg, 'text', {
                'x': str(x + 15),
                'y': str(y + 35 + i * 25),
                'text-anchor': 'middle',
                'fill': 'white',
                'font-family': 'Arial, sans-serif',
                'font-size': '10',
                'font-weight': 'bold'
            })
            number.text = str(i + 1)
            
            # 단계 설명
            text = ET.SubElement(svg, 'text', {
                'x': str(x + 35),
                'y': str(y + 35 + i * 25),
                'fill': self.colors['text'],
                'font-family': 'Arial, sans-serif',
                'font-size': '11'
            })
            text.text = step[:40] + ('...' if len(step) > 40 else '')
    
    def _draw_skills(self, svg: ET.Element, skills: List[Dict[str, Any]], x: int, y: int):
        """스킬들 그리기"""
        title = ET.SubElement(svg, 'text', {
            'x': str(x),
            'y': str(y),
            'fill': self.colors['text'],
            'font-family': 'Arial, sans-serif',
            'font-size': '14',
            'font-weight': 'bold'
        })
        title.text = "필요 스킬"
        
        cols = 3
        for i, skill in enumerate(skills[:9]):  # 최대 9개까지만
            col = i % cols
            row = i // cols
            skill_x = x + col * 200
            skill_y = y + 30 + row * 60
            
            skill_name = skill.get('name', f'스킬 {i+1}') if isinstance(skill, dict) else str(skill)
            importance = skill.get('importance', 'medium') if isinstance(skill, dict) else 'medium'
            
            # 스킬 박스
            rect = ET.SubElement(svg, 'rect', {
                'x': str(skill_x),
                'y': str(skill_y),
                'width': '180',
                'height': '40',
                'fill': self.colors['skill'],
                'stroke': self.colors['border'],
                'stroke-width': '1',
                'rx': '3',
                'opacity': '0.8' if importance == 'low' else '1.0'
            })
            
            # 스킬 이름
            text = ET.SubElement(svg, 'text', {
                'x': str(skill_x + 90),
                'y': str(skill_y + 25),
                'text-anchor': 'middle',
                'fill': 'white',
                'font-family': 'Arial, sans-serif',
                'font-size': '11'
            })
            text.text = skill_name[:20] + ('...' if len(skill_name) > 20 else '')
    
    def _draw_skill_bar(self, svg: ET.Element, skill: Dict[str, Any], x: int, y: int):
        """스킬 진행도 바 그리기"""
        skill_name = skill.get('name', '스킬') if isinstance(skill, dict) else str(skill)
        current_level = skill.get('current_level', 0) if isinstance(skill, dict) else 0
        target_level = skill.get('target_level', 5) if isinstance(skill, dict) else 5
        
        # 스킬 이름
        text = ET.SubElement(svg, 'text', {
            'x': str(x),
            'y': str(y + 15),
            'fill': self.colors['text'],
            'font-family': 'Arial, sans-serif',
            'font-size': '12'
        })
        text.text = skill_name[:25] + ('...' if len(skill_name) > 25 else '')
        
        # 진행도 바 배경
        bg_rect = ET.SubElement(svg, 'rect', {
            'x': str(x + 200),
            'y': str(y),
            'width': '300',
            'height': '20',
            'fill': '#E0E0E0',
            'stroke': self.colors['border'],
            'stroke-width': '1',
            'rx': '10'
        })
        
        # 현재 레벨 바
        current_width = int(300 * min(current_level, target_level) / max(target_level, 1))
        current_rect = ET.SubElement(svg, 'rect', {
            'x': str(x + 200),
            'y': str(y),
            'width': str(current_width),
            'height': '20',
            'fill': self.colors['current'],
            'rx': '10'
        })
        
        # 목표 레벨 표시
        target_width = int(300 * target_level / max(target_level, 1))
        if target_width > current_width:
            target_rect = ET.SubElement(svg, 'rect', {
                'x': str(x + 200 + current_width),
                'y': str(y),
                'width': str(target_width - current_width),
                'height': '20',
                'fill': self.colors['target'],
                'opacity': '0.5',
                'rx': '10'
            })
        
        # 레벨 텍스트
        level_text = ET.SubElement(svg, 'text', {
            'x': str(x + 520),
            'y': str(y + 15),
            'fill': self.colors['text'],
            'font-family': 'Arial, sans-serif',
            'font-size': '11'
        })
        level_text.text = f"{current_level}/{target_level}"
    
    def _draw_modern_role_box(self, svg: ET.Element, text: str, x: int, y: int, color: str, is_current: bool):
        """모던한 역할 박스 그리기"""
        # 그룹 생성
        group = ET.SubElement(svg, 'g', {'class': 'role-box tooltipped'})
        
        # 그림자 효과
        shadow = ET.SubElement(group, 'rect', {
            'x': str(x + 2),
            'y': str(y + 2),
            'width': '120',
            'height': '40',
            'fill': self.colors['shadow'],
            'rx': '8',
            'class': 'shadow'
        })
        
        # 메인 박스
        rect = ET.SubElement(group, 'rect', {
            'x': str(x),
            'y': str(y),
            'width': '120',
            'height': '40',
            'fill': color,
            'stroke': 'none',
            'rx': '8'
        })
        
        # 텍스트
        text_elem = ET.SubElement(group, 'text', {
            'x': str(x + 60),
            'y': str(y + 26),
            'text-anchor': 'middle',
            'fill': 'white',
            'font-size': '12',
            'font-weight': '500',
            'class': 'label'
        })
        text_elem.text = text[:12] + ('...' if len(text) > 12 else '')
        
        # 현재 위치 표시 (더 모던하게)
        if is_current:
            badge = ET.SubElement(group, 'circle', {
                'cx': str(x + 110),
                'cy': str(y + 10),
                'r': '4',
                'fill': '#EF4444'
            })
            
            # 툴팁
            tooltip = ET.SubElement(group, 'text', {
                'x': str(x + 60),
                'y': str(y - 5),
                'text-anchor': 'middle',
                'fill': self.colors['text_light'],
                'font-size': '10',
                'class': 'tooltip'
            })
            tooltip.text = "현재 위치"
    
    def _draw_modern_arrow(self, svg: ET.Element, x1: int, y1: int, x2: int, y2: int, color: str):
        """모던한 화살표 그리기"""
        # 화살표 마커 정의
        defs = svg.find('defs')
        if defs is None:
            defs = ET.SubElement(svg, 'defs')
        
        marker = ET.SubElement(defs, 'marker', {
            'id': 'modern-arrow',
            'markerWidth': '8',
            'markerHeight': '6',
            'refX': '8',
            'refY': '3',
            'orient': 'auto',
            'markerUnits': 'strokeWidth'
        })
        
        path = ET.SubElement(marker, 'path', {
            'd': 'M0,0 L0,6 L8,3 z',
            'fill': color
        })
        
        # 선 그리기 (더 굵고 모던하게)
        line = ET.SubElement(svg, 'line', {
            'x1': str(x1),
            'y1': str(y1),
            'x2': str(x2 - 8),
            'y2': str(y2),
            'stroke': color,
            'stroke-width': '2',
            'stroke-dasharray': '5,3',
            'marker-end': 'url(#modern-arrow)',
            'opacity': '0.8'
        })
    
    def _draw_compact_steps(self, svg: ET.Element, steps: List[str], x: int, y: int):
        """컴팩트한 단계들 그리기"""
        # 섹션 제목
        title = ET.SubElement(svg, 'text', {
            'x': str(x),
            'y': str(y),
            'fill': self.colors['text'],
            'font-size': '14',
            'font-weight': '600',
            'class': 'label'
        })
        title.text = "성장 단계"
        
        # 단계들을 2열로 배치
        cols = 2
        for i, step in enumerate(steps[:4]):
            col = i % cols
            row = i // cols
            step_x = x + col * 240
            step_y = y + 25 + row * 35
            
            # 그룹 생성
            group = ET.SubElement(svg, 'g', {'class': 'step-item'})
            
            # 배경 (호버용)
            bg = ET.SubElement(group, 'rect', {
                'x': str(step_x - 5),
                'y': str(step_y - 15),
                'width': '230',
                'height': '25',
                'fill': 'transparent',
                'rx': '4',
                'class': 'step-bg'
            })
            
            # 단계 번호 (더 작은 원)
            circle = ET.SubElement(group, 'circle', {
                'cx': str(step_x + 8),
                'cy': str(step_y - 5),
                'r': '8',
                'fill': self.colors['path'],
                'opacity': '0.9'
            })
            
            # 단계 번호 텍스트
            number = ET.SubElement(group, 'text', {
                'x': str(step_x + 8),
                'y': str(step_y - 1),
                'text-anchor': 'middle',
                'fill': 'white',
                'font-size': '10',
                'font-weight': '600'
            })
            number.text = str(i + 1)
            
            # 단계 설명 (더 간결하게)
            text = ET.SubElement(group, 'text', {
                'x': str(step_x + 22),
                'y': str(step_y - 1),
                'fill': self.colors['text'],
                'font-size': '11',
                'class': 'label'
            })
            text.text = step[:28] + ('...' if len(step) > 28 else '')
    
    def _draw_compact_skills(self, svg: ET.Element, skills: List[Dict[str, Any]], x: int, y: int):
        """컴팩트한 스킬들 그리기"""
        # 섹션 제목
        title = ET.SubElement(svg, 'text', {
            'x': str(x),
            'y': str(y),
            'fill': self.colors['text'],
            'font-size': '14',
            'font-weight': '600',
            'class': 'label'
        })
        title.text = "핵심 스킬"
        
        # 스킬을 3열로 배치
        cols = 3
        for i, skill in enumerate(skills[:6]):
            col = i % cols
            row = i // cols
            skill_x = x + col * 170
            skill_y = y + 25 + row * 35
            
            skill_name = skill.get('name', f'스킬 {i+1}') if isinstance(skill, dict) else str(skill)
            importance = skill.get('importance', 'medium') if isinstance(skill, dict) else 'medium'
            
            # 그룹 생성
            group = ET.SubElement(svg, 'g', {'class': 'skill-item'})
            
            # 배경 (호버용)
            bg = ET.SubElement(group, 'rect', {
                'x': str(skill_x - 5),
                'y': str(skill_y - 15),
                'width': '160',
                'height': '25',
                'fill': 'transparent',
                'rx': '4',
                'class': 'skill-bg'
            })
            
            # 중요도 표시 점
            importance_color = self.colors['skill'] if importance == 'high' else self.colors['text_light']
            dot = ET.SubElement(group, 'circle', {
                'cx': str(skill_x + 6),
                'cy': str(skill_y - 5),
                'r': '3',
                'fill': importance_color
            })
            
            # 스킬 이름
            text = ET.SubElement(group, 'text', {
                'x': str(skill_x + 16),
                'y': str(skill_y - 1),
                'fill': self.colors['text'],
                'font-size': '11',
                'class': 'label'
            })
            text.text = skill_name[:18] + ('...' if len(skill_name) > 18 else '')
    
    def _draw_modern_skill_bar(self, svg: ET.Element, skill: Dict[str, Any], x: int, y: int, index: int):
        """모던한 스킬 진행도 바 그리기"""
        skill_name = skill.get('name', '스킬') if isinstance(skill, dict) else str(skill)
        current_level = skill.get('current_level', 0) if isinstance(skill, dict) else 0
        target_level = skill.get('target_level', 5) if isinstance(skill, dict) else 5
        
        # 그룹 생성
        group = ET.SubElement(svg, 'g', {'class': 'skill-item'})
        
        # 배경 (호버용)
        bg = ET.SubElement(group, 'rect', {
            'x': str(x - 10),
            'y': str(y - 5),
            'width': str(self.width - 60),
            'height': '35',
            'fill': 'transparent',
            'rx': '6',
            'class': 'skill-bg'
        })
        
        # 스킬 이름
        text = ET.SubElement(group, 'text', {
            'x': str(x),
            'y': str(y + 15),
            'fill': self.colors['text'],
            'font-size': '12',
            'font-weight': '500',
            'class': 'label'
        })
        text.text = skill_name[:20] + ('...' if len(skill_name) > 20 else '')
        
        # 진행도 바 시작 위치
        bar_x = x + 140
        bar_width = 200
        bar_height = 8
        
        # 진행도 바 배경
        bg_rect = ET.SubElement(group, 'rect', {
            'x': str(bar_x),
            'y': str(y + 5),
            'width': str(bar_width),
            'height': str(bar_height),
            'fill': self.colors['border'],
            'rx': '4'
        })
        
        # 현재 레벨 바
        if target_level > 0:
            current_width = int(bar_width * min(current_level, target_level) / target_level)
            current_rect = ET.SubElement(group, 'rect', {
                'x': str(bar_x),
                'y': str(y + 5),
                'width': str(current_width),
                'height': str(bar_height),
                'fill': self.colors['current'],
                'rx': '4',
                'class': 'skill-bar'
            })
            
            # 목표 레벨 표시 (연한 색)
            if target_level > current_level:
                remaining_width = int(bar_width * (target_level - current_level) / target_level)
                target_rect = ET.SubElement(group, 'rect', {
                    'x': str(bar_x + current_width),
                    'y': str(y + 5),
                    'width': str(remaining_width),
                    'height': str(bar_height),
                    'fill': self.colors['current'],
                    'opacity': '0.3',
                    'rx': '4'
                })
        
        # 레벨 텍스트
        level_text = ET.SubElement(group, 'text', {
            'x': str(bar_x + bar_width + 15),
            'y': str(y + 12),
            'fill': self.colors['text_light'],
            'font-size': '10',
            'class': 'label'
        })
        level_text.text = f"{current_level}/{target_level}"
