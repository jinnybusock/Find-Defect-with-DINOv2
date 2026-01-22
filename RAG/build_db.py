from rag_core import DefectRAG_Postgres

# ★ Docker 또는 로컬 DB 정보에 맞게 수정하세요 ★
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "postgres",       # 기본 DB 이름
    "user": "postgres",         # 기본 유저
    "password": "3510" # 설치할 때 설정한 비번
}

if __name__ == "__main__":
    # 1. PostgreSQL 연결
    rag = DefectRAG_Postgres(DB_CONFIG)

    # 2. 데이터 폴더 경로
    train_root = r"C:\Users\hjchung\Desktop\RAG Train"

    # 3. DB에 데이터 밀어넣기
    rag.ingest_data_folder(train_root)