import os
from PIL import Image
import sys

# 1. 문제가 되는 파일 경로 (사용자님 경로 그대로)
test_file = r"C:\Users\hjchung\Desktop\RAG Test\R1xC22-4-82pxl.png"
train_folder = r"C:\Users\hjchung\Desktop\Train\crack"

print(f"python version: {sys.version}")

# --- 테스트 1: 파일이 진짜 있나? ---
if os.path.exists(test_file):
    print(f"✅ 파일 존재함: {test_file}")

    # --- 테스트 2: PIL이 열 수 있나? ---
    try:
        img = Image.open(test_file)
        img.load()  # 실제 데이터를 읽어봄 (여기서 터질 확률 높음)
        print(f"✅ 이미지 읽기 성공! 크기: {img.size}")
    except Exception as e:
        print(f"❌ [에러 발생] 이미지를 못 엽니다!")
        print(f"👉 에러 내용: {e}")
        print(f"👉 에러 타입: {type(e)}")
else:
    print(f"❌ 파일이 경로에 없습니다. 이름이나 확장자를 확인하세요.")

# --- 테스트 3: 폴더 안에 파일들이 보이나? ---
print(f"\n📂 Train 폴더 확인 중: {train_folder}")
try:
    files = os.listdir(train_folder)
    print(f"   발견된 파일들: {files[:5]} ... (총 {len(files)}개)")
except Exception as e:
    print(f"❌ 폴더를 못 읽겠습니다: {e}")