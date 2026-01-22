import psycopg

# ★ 사용 중인 DB 접속 정보 (build_db.py와 동일)
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "postgres",
    "user": "postgres",
    "password": "3510"  # 설정하신 비밀번호
}

def check_database():
    print(f"🔌 PostgreSQL DB({DB_CONFIG['host']}:{DB_CONFIG['port']})에 접속 시도 중...")

    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:

                # 1. 전체 데이터 개수 확인
                cursor.execute("SELECT COUNT(*) FROM defect_images;")
                total_count = cursor.fetchone()[0]

                print(f"\n📊 [PostgreSQL 현황 리포트]")
                print(f"✅ 총 저장된 데이터 개수: {total_count}개")
                print("-" * 60)

                if total_count == 0:
                    print("⚠️ 저장된 데이터가 없습니다. build_db.py를 먼저 실행해 주세요.")
                    return

                # 2. 상위 5개 샘플 데이터 조회
                # (파일명, 결함종류, 그리고 벡터가 잘 들어갔는지 길이 확인)
                cursor.execute("""
                    SELECT id, filename, defect_type, vector_dims(embedding) 
                    FROM defect_images 
                    ORDER BY id ASC 
                    LIMIT 5;
                """)

                rows = cursor.fetchall()

                print(f"{'ID':<5} {'결함 종류':<15} {'파일명':<30} {'벡터 차원'}")
                print("-" * 60)

                for row in rows:
                    db_id, fname, dtype, dim = row
                    # 파일명이 너무 길면 자르기
                    if len(fname) > 28: fname = fname[:25] + "..."

                    print(f"{db_id:<5} {dtype:<15} {fname:<30} {dim}차원")

                print("-" * 60)
                print("✅ 데이터가 정상적으로 조회됩니다!")

    except Exception as e:
        print(f"\n❌ DB 접속 실패 또는 에러 발생:\n{e}")
        print("\n[Tip] Docker 컨테이너가 켜져 있는지 확인해 보세요.")


if __name__ == "__main__":
    check_database()