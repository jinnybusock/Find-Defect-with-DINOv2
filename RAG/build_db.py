from rag_core import DefectRAG_Enterprise  # 우리가 만든 rag_core 불러오기

# DB 구축용

if __name__ == "__main__":
    # 1. 시스템 준비
    rag = DefectRAG_Enterprise()

    # 2. 학습할 폴더 경로 (바탕화면 Train 폴더)
    train_root = r"C:\Users\hjchung\Desktop\RAG Train"

    # 3. 폴더 읽어서 DB 만들기
    rag.ingest_data_folder(train_root)

    # 4. ★ DB를 파일로 저장하기! (이게 핵심)
    rag.save_database(db_path="my_semicon_db.index", meta_path="my_semicon_meta.pkl")