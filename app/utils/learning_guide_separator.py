#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Learning Guide 분리 프로그램
VSCode에서 실행 가능한 완전한 코드

사용 방법:
1. college.csv 파일을 이 파이썬 파일과 같은 폴더에 위치
2. VSCode에서 이 파일을 열고 실행 (F5 또는 Ctrl+F5)
3. 결과 파일 college_processed.csv가 생성됨
"""

import pandas as pd
import os
import sys

def process_learning_guides(df):
    """
    Learning Guide 컬럼을 특화, 추천, 공통필수로 분리하는 함수
    
    Args:
        df (DataFrame): 원본 데이터프레임
    
    Returns:
        DataFrame: 처리된 데이터프레임
    """
    print("Learning Guide 분리 작업을 시작합니다...")
    
    # 새로운 컬럼들을 위한 리스트 초기화
    specialized = []     # 특화
    recommended = []     # 추천
    common_required = [] # 공통필수
    
    total_rows = len(df)
    
    for index, row in df.iterrows():
        # 진행률 표시
        if (index + 1) % 50 == 0 or index == total_rows - 1:
            print(f"처리 중... ({index + 1}/{total_rows})")
        
        learning_guide = str(row['Learning Guide']) if pd.notna(row['Learning Guide']) else ''
        
        # 각 카테고리별 리스트 초기화
        spec_items = []
        rec_items = []
        common_items = []
        
        if learning_guide and learning_guide != 'nan':
            # 쉼표로 분리하고 공백 제거
            guides = [guide.strip() for guide in learning_guide.split(',')]
            
            for guide in guides:
                if guide.startswith('특화 -'):
                    spec_items.append(guide.replace('특화 - ', '').strip())
                elif guide.startswith('추천 -'):
                    rec_items.append(guide.replace('추천 - ', '').strip())
                elif guide.startswith('공통필수 -'):
                    common_items.append(guide.replace('공통필수 - ', '').strip())
        
        # 세미콜론으로 구분하여 저장
        specialized.append('; '.join(spec_items) if spec_items else '')
        recommended.append('; '.join(rec_items) if rec_items else '')
        common_required.append('; '.join(common_items) if common_items else '')
    
    # 새로운 데이터프레임 생성
    df_processed = df.copy()
    df_processed['특화'] = specialized
    df_processed['추천'] = recommended
    df_processed['공통필수'] = common_required
    
    # 원본 Learning Guide 컬럼 제거
    if 'Learning Guide' in df_processed.columns:
        df_processed = df_processed.drop('Learning Guide', axis=1)
    
    print("Learning Guide 분리 작업이 완료되었습니다!")
    return df_processed

def check_file_exists(filename):
    """
    파일 존재 여부 확인
    """
    if not os.path.exists(filename):
        print(f"❌ 오류: '{filename}' 파일을 찾을 수 없습니다.")
        print(f"현재 작업 디렉토리: {os.getcwd()}")
        print("다음을 확인해주세요:")
        print("1. college.csv 파일이 이 Python 파일과 같은 폴더에 있는지 확인")
        print("2. 파일명이 정확한지 확인 (대소문자 포함)")
        return False
    return True

def display_sample_results(df_processed, num_samples=3):
    """
    처리 결과 샘플 출력
    """
    print(f"\n=== 처리 결과 샘플 (첫 {num_samples}개 행) ===")
    
    for i in range(min(num_samples, len(df_processed))):
        print(f"\n📋 {i+1}번째 행:")
        print(f"   교육과정명: {df_processed.iloc[i]['교육과정명']}")
        print(f"   특화: {df_processed.iloc[i]['특화'][:100]}{'...' if len(str(df_processed.iloc[i]['특화'])) > 100 else ''}")
        print(f"   추천: {df_processed.iloc[i]['추천'][:100]}{'...' if len(str(df_processed.iloc[i]['추천'])) > 100 else ''}")
        print(f"   공통필수: {df_processed.iloc[i]['공통필수'][:100]}{'...' if len(str(df_processed.iloc[i]['공통필수'])) > 100 else ''}")

def display_statistics(df_processed):
    """
    통계 정보 출력
    """
    stats = {
        '특화있음': len(df_processed[df_processed['특화'] != '']),
        '추천있음': len(df_processed[df_processed['추천'] != '']),
        '공통필수있음': len(df_processed[df_processed['공통필수'] != '']),
        '전체': len(df_processed)
    }
    
    print(f"\n=== 📊 통계 정보 ===")
    print(f"전체 행 수: {stats['전체']:,}개")
    print(f"특화 가이드가 있는 행: {stats['특화있음']:,}개 ({stats['특화있음']/stats['전체']*100:.1f}%)")
    print(f"추천 가이드가 있는 행: {stats['추천있음']:,}개 ({stats['추천있음']/stats['전체']*100:.1f}%)")
    print(f"공통필수 가이드가 있는 행: {stats['공통필수있음']:,}개 ({stats['공통필수있음']/stats['전체']*100:.1f}%)")

def main():
    """
    메인 실행 함수
    """
    print("=" * 60)
    print("🚀 Learning Guide 분리 프로그램 시작")
    print("=" * 60)
    
    # 입력 파일명
    input_filename = 'college.csv'
    output_filename = 'college_processed.csv'
    
    try:
        # 1. 파일 존재 여부 확인
        if not check_file_exists(input_filename):
            input("프로그램을 종료하려면 Enter를 누르세요...")
            return
        
        # 2. CSV 파일 읽기
        print(f"📖 '{input_filename}' 파일을 읽는 중...")
        try:
            df = pd.read_csv(input_filename, encoding='utf-8')
        except UnicodeDecodeError:
            print("UTF-8 인코딩 실패, CP949 인코딩으로 재시도...")
            df = pd.read_csv(input_filename, encoding='cp949')
        
        print(f"✅ 파일 읽기 완료: {len(df):,}행, {len(df.columns)}열")
        print(f"컬럼명: {list(df.columns)}")
        
        # 3. Learning Guide 컬럼 확인
        if 'Learning Guide' not in df.columns:
            print("❌ 오류: 'Learning Guide' 컬럼을 찾을 수 없습니다.")
            print(f"사용 가능한 컬럼: {list(df.columns)}")
            input("프로그램을 종료하려면 Enter를 누르세요...")
            return
        
        # 4. Learning Guide 분리 처리
        df_processed = process_learning_guides(df)
        
        # 5. 결과 확인
        print(f"✅ 처리 완료: {len(df_processed):,}행, {len(df_processed.columns)}열")
        print(f"새로운 컬럼: {list(df_processed.columns)}")
        
        # 6. 샘플 결과 출력
        display_sample_results(df_processed)
        
        # 7. 통계 정보 출력
        display_statistics(df_processed)
        
        # 8. 처리된 결과를 새 CSV 파일로 저장
        print(f"\n💾 결과를 '{output_filename}' 파일로 저장 중...")
        df_processed.to_csv(output_filename, index=False, encoding='utf-8-sig')
        print(f"✅ 저장 완료!")
        
        # 9. 저장된 파일 정보
        file_size = os.path.getsize(output_filename)
        print(f"📁 저장된 파일 크기: {file_size:,} bytes")
        print(f"📍 저장 위치: {os.path.abspath(output_filename)}")
        
        print("\n" + "=" * 60)
        print("🎉 모든 작업이 성공적으로 완료되었습니다!")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"❌ 파일 오류: {e}")
    except pd.errors.EmptyDataError:
        print("❌ 오류: CSV 파일이 비어있습니다.")
    except pd.errors.ParserError as e:
        print(f"❌ CSV 파싱 오류: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        input("\n프로그램을 종료하려면 Enter를 누르세요...")

def simple_test():
    """
    간단한 테스트 함수
    """
    print("\n" + "=" * 40)
    print("🧪 간단한 테스트 실행")
    print("=" * 40)
    
    # 샘플 데이터
    sample_data = {
        '교육과정명': [
            '[Guided Project] Btv 시청데이터를 활용한 추천 모델 개발',
            'ERP 시스템 이해',
            '클라우드 보안 기초'
        ],
        'Learning Guide': [
            '특화 - AIX - AI/Data Dev.,추천 - AIX - G.AI Dev.,G.AI Model Dev.,추천 - Manufacturing - 지능화',
            '특화 - Biz. Consulting - ERP,추천 - PM - Solution PM,추천 - Solution - ERP Dev.',
            '공통필수 - Cloud/Infra - Cyber Security,공통필수 - Architect - Technical Archi.'
        ]
    }
    
    df_sample = pd.DataFrame(sample_data)
    df_result = process_learning_guides(df_sample)
    
    for i in range(len(df_result)):
        print(f"\n{i+1}. {df_result.iloc[i]['교육과정명']}")
        print(f"   특화: {df_result.iloc[i]['특화']}")
        print(f"   추천: {df_result.iloc[i]['추천']}")
        print(f"   공통필수: {df_result.iloc[i]['공통필수']}")

if __name__ == "__main__":
    # 판다스가 설치되어 있는지 확인
    try:
        import pandas as pd
        print("✅ pandas 라이브러리가 정상적으로 로드되었습니다.")
    except ImportError:
        print("❌ 오류: pandas 라이브러리가 설치되어 있지 않습니다.")
        print("다음 명령어로 설치해주세요:")
        print("pip install pandas")
        input("프로그램을 종료하려면 Enter를 누르세요...")
        sys.exit(1)
    
    # 테스트 실행 여부 확인
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        simple_test()
    else:
        main()