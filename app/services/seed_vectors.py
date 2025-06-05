# seed_vectors.py
from services.vector_db_service import upsert_vector
import pandas as pd

# 엑셀 로딩 및 전처리
df = pd.read_excel("SKALA전달용_구성원성장history_v.0.2_250530.xlsx", sheet_name="구성원성장History")
df.columns = df.columns.str.strip().str.replace("\n", " ")

# 행 → 텍스트 + 메타데이터
for _, row in df.iterrows():
    if pd.isna(row["고유번호"]): continue

    doc = f"{row['연차']}년차, 프로젝트: {row['주요 업무/프로젝트 예시: OO은행 차세대 시스템 구축']}, 역할: {row['수행역할 예시: PM, 분석/설계,개발자, PL(사업관리)']}, 도메인: {row['Industry/Domain 예시: 금융, 통신, 제조 등']}, 커리어 설명: {row['큰 영향을 받은 업무/시기에 대한 설명']}"
    skills = [row[k] for k in ['활용 Skill set 1', '활용 Skill set 2', '활용 Skill set 3', '활용 Skill set 4'] if pd.notna(row[k])]
    meta = {
        "mentor_id": str(row["고유번호"]),
        "year": row["연차"],
        "role": row["수행역할 예시: PM, 분석/설계,개발자, PL(사업관리)"],
        "domain": row["Industry/Domain 예시: 금융, 통신, 제조 등"],
        "skills": ", ".join(skills) 
    }
    id = f"{row['고유번호']}-{int(row['연차'])}"
    upsert_vector(id, doc, meta)

print("✅ mentor_history vector 구축 완료!")
