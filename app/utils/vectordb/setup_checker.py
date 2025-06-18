# app/utils/vectordb/setup_checker.py
"""
벡터 DB 구축 전 필요한 파일들이 올바른 위치에 있는지 확인하는 스크립트
"""

import os
import shutil
from pathlib import Path

def check_and_setup_files():
    """필요한 파일들의 위치를 확인하고 설정"""
    
    print("벡터 DB 구축을 위한 파일 확인 중...")
    
    # 1. CSV 파일 확인
    required_files = {
        "career_history_v2.csv": "app/data/csv/career_history_v2.csv",
        "skill_set.csv": "app/data/csv/skill_set.csv"
    }
    
    missing_files = []
    
    for filename, target_path in required_files.items():
        if not os.path.exists(target_path):
            print(f"{target_path} 파일이 없음")
            missing_files.append(filename)
        else:
            print(f"{target_path} 파일 확인")
    
    # 2. 벡터 DB 처리 스크립트 위치 확인
    processor_script = "app/utils/vectordb/careerhistory_data_processor.py"
    if not os.path.exists(processor_script):
        print(f"{processor_script} 스크립트가 없습니다")
    else:
        print(f"{processor_script} 스크립트 확인")
    
    # 3. 디렉토리 생성
    directories = [
        "app/data/csv",
        "app/storage/vector_stores/career_data", 
        "app/storage/cache/embedding_cache",
        "app/storage/docs",
        "app/utils/vectordb"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"{directory} 디렉토리 준비 완료")
    
    # 4. 결과 요약
    if missing_files:
        print(f"\n다음 파일들이 필요합니다:")
        for filename in missing_files:
            print(f"   - {filename}")
        print(f"\n다음 단계:")
        print(f"   1. CSV 파일들을 app/data/csv/ 디렉토리에 복사")
        print(f"   2. careerhistory_data_processor.py를 app/utils/vectordb/에 복사")
        return False
    else:
        print(f"\n모든 필요 파일이 준비되었습니다!")
        return True

if __name__ == "__main__":
    setup_complete = check_and_setup_files()
    
    if setup_complete:
        print("\nsetup 테스트 완료")
    else:
        print("\n필요한 파일들을 준비한 후 다시 실행 필요")