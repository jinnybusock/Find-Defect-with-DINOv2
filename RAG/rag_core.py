import torch
import torchvision.transforms as T
from PIL import Image
import faiss
import numpy as np
import os
import glob
import pickle  # 데이터를 파일로 저장하기 위한 라이브러리
from collections import Counter

# 작은 이미지 처리 기능 & 저장/불러오기 기능

class DefectRAG_Enterprise:
    def __init__(self, tile_size=518, stride=259):
        self.tile_size = tile_size
        self.stride = stride
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🏭 [RAG 시스템] 초기화 (Device: {self.device})")

        # 모델을 'vitl14'(Large)로 변경
        # ---------------------------------------------------------
        # s: Small (384차원) -> b: Base (768차원) -> l: Large (1024차원)
        self.model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitl14')
        self.model.to(self.device)
        self.model.eval()

        self.transform = T.Compose([
            T.Resize((518, 518)),  # 해상도도 518로 유지 (도메인 맞춤)
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.dimension = 1024
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []

    def tile_image(self, img_path):
        try:
            img = Image.open(img_path).convert('RGB')
        except Exception as e:
            return [], []

        w, h = img.size
        tiles, coords = [], []

        # 작은 이미지 처리 (강제 리사이즈)
        if w < self.tile_size or h < self.tile_size:
            tiles.append(img.resize((self.tile_size, self.tile_size)))
            coords.append((0, 0))
            return tiles, coords

        for y in range(0, h, self.stride):
            for x in range(0, w, self.stride):
                box = (x, y, x + self.tile_size, y + self.tile_size)
                if box[2] > w or box[3] > h: continue
                tiles.append(img.crop(box))
                coords.append((x, y))

        if not tiles:  # 애매한 크기 처리
            tiles.append(img.resize((self.tile_size, self.tile_size)))
            coords.append((0, 0))

        return tiles, coords

    def extract_features(self, tiles):
        if not tiles: return None
        batch = torch.stack([self.transform(t) for t in tiles]).to(self.device)
        with torch.no_grad():
            features = self.model(batch)
        return features.cpu().numpy().astype('float32')

    def ingest_data_folder(self, root_folder):
        """이미지를 읽어서 메모리에 DB 구축"""
        print(f"\n📂 데이터 수집 시작: {root_folder}")
        subfolders = [f.path for f in os.scandir(root_folder) if f.is_dir()]
        valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')

        for folder in subfolders:
            defect_type = os.path.basename(folder)
            print(f"  Target: '{defect_type}' 학습 중...", end=" ")

            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(valid_exts)]
            if not files:
                print("-> ⚠️ 파일 없음")
                continue

            count = 0
            for img_path in files:
                tiles, coords = self.tile_image(img_path)
                if not tiles: continue

                vectors = self.extract_features(tiles)
                start_id = self.index.ntotal
                self.index.add(vectors)

                for i, coord in enumerate(coords):
                    self.metadata.append({
                        "id": start_id + i,
                        "type": defect_type,
                        "file": os.path.basename(img_path),
                        "coord": coord
                    })
                count += 1
            print(f"-> {count}장 완료.")

    # ==========================================
    # ★ 추가된 기능: DB 저장 및 불러오기
    # ==========================================
    def save_database(self, db_path="defect_db.index", meta_path="defect_meta.pkl"):
        """현재 학습된 DB를 파일로 저장"""
        print(f"\n💾 DB 저장 중... ({db_path})")
        faiss.write_index(self.index, db_path)
        with open(meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        print("✅ 저장 완료! 이제 search.py에서 바로 불러올 수 있습니다.")

    def load_database(self, db_path="defect_db.index", meta_path="defect_meta.pkl"):
        """파일에서 DB 불러오기"""
        if not os.path.exists(db_path) or not os.path.exists(meta_path):
            print(f"❌ 저장된 DB 파일이 없습니다! ({db_path}) 먼저 build_db.py를 실행하세요.")
            return False

        print(f"\n📂 저장된 DB 불러오는 중... ({db_path})")
        self.index = faiss.read_index(db_path)
        with open(meta_path, "rb") as f:
            self.metadata = pickle.load(f)
        print(f"✅ 로드 완료! (총 {len(self.metadata)}개 타일 데이터)")
        return True

    def search(self, query_img_path, k=5):
        print(f"\n🔍 [검사 요청] {os.path.basename(query_img_path)}")

        if not os.path.exists(query_img_path):
            print("❌ 파일 없음")
            return

        tiles, coords = self.tile_image(query_img_path)
        if not tiles:
            print("❌ 이미지 로드 실패")
            return

        vectors = self.extract_features(tiles)
        distances, indices = self.index.search(vectors, k)

        print(f"\n📊 [Top-{k} 상세 분석 및 근거 데이터]")
        print("-" * 90)
        # 헤더에 '참고 파일명' 추가
        print(f"{'순위':<6} {'결함 종류':<12} {'거리':<10} {'점수':<10} {'참고한 DB 파일명 (Evidence)':<30}")
        print("-" * 90)

        # 점수판을 더 똑똑하게 업그레이드 (점수만 넣는 게 아니라, 파일 목록도 같이 저장)
        # 구조: {'Crack': {'score': 500, 'evidence': ['file1', 'file2']}, ...}
        detailed_board = {}

        for rank, (idx, dist) in enumerate(zip(indices[0], distances[0])):
            if idx == -1: continue

            meta_info = self.metadata[idx]
            defect_type = meta_info['type']
            ref_filename = meta_info['file']  # ★ DB에 있는 참고 파일 이름

            # 점수 계산
            similarity_score = 100000 / (dist + 1.0)

            # 1. 상세 표 출력 (어떤 파일을 참고했는지 바로 보여줌)
            print(f"{rank + 1:<6} {defect_type:<12} {dist:<10.2f} {similarity_score:<10.2f} {ref_filename:<30}")

            # 모든 결함 종류(Good 포함)를 공평하게 점수판에 등록!
            if defect_type not in detailed_board:
                detailed_board[defect_type] = {'total_score': 0, 'files': []}

            # 점수 누적
            detailed_board[defect_type]['total_score'] += similarity_score
            # 어떤 파일 때문에 이 점수가 나왔는지 기록 (파일명, 점수)
            detailed_board[defect_type]['files'].append((ref_filename, similarity_score))

        print("-" * 90)

        # -----------------------------------------------------
        # 최종 판정 및 근거 제시
        # -----------------------------------------------------
        if not detailed_board:
            print("✅ 최종 판정: 정상 (Normal/Good) - 특이 사항 없음")
        else:
            # 점수 합계가 가장 높은 결함 찾기
            # item[1]['total_score']를 기준으로 내림차순 정렬
            sorted_defects = sorted(detailed_board.items(), key=lambda item: item[1]['total_score'], reverse=True)

            best_defect = sorted_defects[0][0]  # 1등 결함 이름 (예: Crack)
            best_data = sorted_defects[0][1]  # 1등의 상세 정보 (점수, 파일들)

            print(f"🏆 최종 판정: '{best_defect}'")
            print(f"   (이유: 유사도 점수 합계 {best_data['total_score']:.2f}점으로 1위)")

            print(f"\n   📂 [{best_defect} 판정의 근거 데이터]")
            for i, (fname, score) in enumerate(best_data['files']):
                print(f"     {i + 1}. {fname} (기여 점수: {score:.2f}점)")

            # 2등이 있다면 비교 (애매할 때 확인용)
            if len(sorted_defects) > 1:
                runner_up = sorted_defects[1][0]
                runner_up_score = sorted_defects[1][1]['total_score']
                print(f"\n   ⚠️ (참고: 2위는 '{runner_up}' - {runner_up_score:.2f}점)")