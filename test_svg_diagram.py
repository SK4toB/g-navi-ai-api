# test_svg_diagram.py
"""
SVG 다이어그램 생성기 테스트 스크립트
"""

from app.utils.svg_diagram_generator import GrowthDiagramGenerator

def test_career_path_diagram():
    """커리어 패스 다이어그램 테스트"""
    generator = GrowthDiagramGenerator()
    
    # 테스트 데이터
    data = {
        'current_role': 'Backend Developer',
        'target_role': 'Tech Lead',
        'steps': [
            '시스템 아키텍처 이해',
            '주니어 개발자 멘토링 시작',
            '기술 의사결정 참여',
            '팀 리더십 경험 확보'
        ],
        'skills': [
            {'name': 'System Design', 'importance': 'high'},
            {'name': 'Mentoring', 'importance': 'high'},
            {'name': 'Communication', 'importance': 'medium'},
            {'name': 'Code Review', 'importance': 'medium'}
        ]
    }
    
    svg_content = generator.generate_career_path_diagram(data)
    
    # 파일로 저장
    with open('test_career_path.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    
    print("커리어 패스 다이어그램 생성 완료: test_career_path.svg")

def test_skill_development_diagram():
    """스킬 개발 다이어그램 테스트"""
    generator = GrowthDiagramGenerator()
    
    # 테스트 데이터
    data = {
        'skills': [
            {'name': 'Java/Spring', 'current_level': 4, 'target_level': 5, 'importance': 'high'},
            {'name': 'System Design', 'current_level': 2, 'target_level': 4, 'importance': 'high'},
            {'name': 'Leadership', 'current_level': 1, 'target_level': 3, 'importance': 'medium'},
            {'name': 'Communication', 'current_level': 3, 'target_level': 5, 'importance': 'high'},
            {'name': 'DevOps', 'current_level': 2, 'target_level': 4, 'importance': 'medium'}
        ]
    }
    
    svg_content = generator.generate_skill_development_diagram(data)
    
    # 파일로 저장
    with open('test_skill_development.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    
    print("스킬 개발 다이어그램 생성 완료: test_skill_development.svg")

if __name__ == "__main__":
    print("SVG 다이어그램 생성기 테스트 시작...")
    
    test_career_path_diagram()
    test_skill_development_diagram()
    
    print("테스트 완료!")
    print("생성된 SVG 파일들을 브라우저에서 열어서 확인해보세요.")
