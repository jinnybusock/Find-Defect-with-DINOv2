from rag_core import DefectRAG_Enterprise
import os
import sys


def find_file_fuzzy(user_input, folder_path):
    """
    사용자의 말(user_input)에서 폴더 내의 파일 이름을 찾아내는 탐정 함수
    예: "이거 image_01 좀 봐줘" -> folder/image_01.png 경로 반환
    """
    # 1. 폴더 내 모든 파일 목록 가져오기
    if not os.path.exists(folder_path):
        return None, "폴더를 찾을 수 없습니다."

    all_files = os.listdir(folder_path)

    # 2. 사용자가 말한 문장을 띄어쓰기 단위로 쪼개기 (예: ['R1xC22', '결함', '뭐야?'])
    #    특수문자(?, !, ' 등)는 제거해서 비교
    clean_input = user_input.replace("'", "").replace('"', "").replace("?", "").replace("!", "")
    words = clean_input.split()

    candidate = None

    # 3. 매칭 로직 (스마트 검색)
    for file in all_files:
        # (1) 정확히 일치하는 경우 (확장자 포함)
        if file in words:
            candidate = file
            break

        # (2) 확장자 떼고 비교 (사용자가 "img_01"이라고만 했을 때 "img_01.png" 찾기)
        filename_no_ext = os.path.splitext(file)[0]
        for word in words:
            if word == filename_no_ext:  # 정확히 이름만 불렀을 때
                candidate = file
                break
            if word in filename_no_ext and len(word) > 4:  # 이름의 일부만 불렀을 때 (너무 짧은 건 제외)
                # 예: "[00001]TestImage" 파일이 있는데 사용자가 "TestImage"라고 했을 때
                candidate = file
                break

        if candidate: break

    if candidate:
        return os.path.join(folder_path, candidate), candidate
    else:
        return None, None


# =========================================================
# 실행 파트 (대화형 루프)
# =========================================================
if __name__ == "__main__":
    # 1. 시스템 로딩
    rag = DefectRAG_Enterprise()

    # DB 파일이 없으면 경고
    if not os.path.exists("my_semicon_db.index"):
        print("❌ DB 파일이 없습니다! 먼저 build_db.py를 실행해주세요.")
        sys.exit()

    rag.load_database(db_path="my_semicon_db.index", meta_path="my_semicon_meta.pkl")

    # 2. 검사 대상 폴더 (여기에 있는 이미지만 검색 가능)
    target_folder = r"C:\Users\hjchung\Desktop\RAG Test"

    print("\n" + "=" * 50)
    print("🤖 AI 결함 판별 챗봇이 준비되었습니다!")
    print(f"📂 대상 폴더: {os.path.basename(target_folder)}")
    print("💡 사용법: 파일명을 포함하여 질문해 주세요. 예시: [000001]R3xC10-1-241pxl 이미지 결함 종류가 뭐야?")
    print("❌ 종료하려면 'exit' 또는 '종료'라고 입력하세요.")
    print("=" * 50 + "\n")

    # 3. 무한 대화 루프
    while True:
        user_query = input("user > ")

        if user_query.strip().lower() in ["exit", "quit", "종료", "꺼져"]:
            print("🤖 시스템을 종료합니다. 안녕히 가세요!")
            break

        if not user_query.strip():
            continue

        # 스마트 파일 찾기
        found_path, filename = find_file_fuzzy(user_query, target_folder)

        if found_path:
            print(f"🤖 아하! '{filename}' 파일을 분석할게요.")
            rag.search(found_path)
            print("-" * 30)
        else:
            print("🤖 죄송해요. 문장에서 파일 이름을 찾을 수 없거나, 폴더에 없는 파일입니다.")
            print("   (파일명이 정확한지, 혹은 RAG Test 폴더에 있는지 확인해주세요)")
            print("-" * 30)