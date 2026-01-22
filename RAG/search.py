from rag_core import DefectRAG_Postgres  # [수정] 이제 Enterprise 대신 Postgres를 불러옵니다.
import os
import sys

# ★ 중요: build_db.py와 똑같은 DB 접속 정보를 입력해야 합니다.
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "postgres",  # 아까 수정한 기본 DB 이름
    "user": "postgres",
    "password": "3510"  # 설정하신 비밀번호
}


def find_file_fuzzy(user_input, folder_path):
    """
    사용자의 말(user_input)에서 폴더 내의 파일 이름을 찾아내는 탐정 함수
    예: "이거 image_01 좀 봐줘" -> folder/image_01.png 경로 반환
    """
    if not os.path.exists(folder_path):
        return None, "폴더를 찾을 수 없습니다."

    all_files = os.listdir(folder_path)

    # 특수문자 제거 및 단어 분리
    clean_input = user_input.replace("'", "").replace('"', "").replace("?", "").replace("!", "")
    words = clean_input.split()

    candidate = None

    for file in all_files:
        # (1) 정확히 일치하는 경우
        if file in words:
            candidate = file
            break

        # (2) 확장자 떼고 비교 (예: 사용자가 "img_01"이라고만 했을 때 "img_01.png" 찾기)
        filename_no_ext = os.path.splitext(file)[0]
        for word in words:
            if word == filename_no_ext:
                candidate = file
                break
            # 너무 짧은 단어(4글자 이하)는 오탐지 방지를 위해 제외
            if len(word) > 4 and word in filename_no_ext:
                candidate = file
                break

        if candidate: break

    if candidate:
        return os.path.join(folder_path, candidate), candidate
    else:
        return None, None


if __name__ == "__main__":
    # 1. 시스템 로딩 (DB 연결)
    try:
        rag = DefectRAG_Postgres(DB_CONFIG)
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        sys.exit()

    # 2. 검사 대상 폴더 (검색할 이미지가 들어있는 폴더)
    target_folder = r"C:\Users\hjchung\Desktop\RAG Test"

    print("\n" + "=" * 50)
    print("🤖 PostgreSQL 기반 AI 결함 판별 챗봇 준비 완료!")
    print(f"📂 대상 폴더: {os.path.basename(target_folder)}")
    print("💡 사용법: 파일명을 포함하여 질문해 주세요.")
    print("   예시: '[000001]R3xC10' 이미지 결함 종류가 뭐야?")
    print("❌ 종료하려면 'exit' 또는 '종료'라고 입력하세요.")
    print("=" * 50 + "\n")

    # 3. 대화 루프
    while True:
        user_query = input("user > ")

        if user_query.strip().lower() in ["exit", "quit", "종료", "꺼져"]:
            print("🤖 시스템을 종료합니다. 안녕히 가세요!")
            break

        if not user_query.strip():
            continue

        # 질문에서 파일명 찾기
        found_path, filename = find_file_fuzzy(user_query, target_folder)

        if found_path:
            print(f"🤖 아하! '{filename}' 파일을 분석할게요.")
            # DB 검색 실행
            rag.search(found_path)
            print("-" * 30)
        else:
            print("🤖 죄송해요. 문장에서 파일 이름을 찾을 수 없거나, 폴더에 없는 파일입니다.")
            print("   (파일명이 정확한지 확인해주세요)")
            print("-" * 30)