import torch
import torchvision.transforms as T
from PIL import Image
import numpy as np
import os
import glob
import psycopg  # psycopg 3 버전
from pgvector.psycopg import register_vector


class DefectRAG_Postgres:
    def __init__(self, db_info):
        """
        db_info: DB 접속 정보 딕셔너리
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🏭 [PostgreSQL RAG] 시스템 초기화 (Device: {self.device})")

        self.db_info = db_info

        # DB 연결 및 테이블 생성
        with psycopg.connect(**self.db_info, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(conn)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS defect_images (
                    id SERIAL PRIMARY KEY,
                    filename TEXT,
                    defect_type TEXT,
                    embedding vector(1024)
                )
            """)
            print("✅ DB 연결 및 테이블 확인 완료")

        # AI 모델 로드 (DINOv2 Large)
        self.model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitl14')
        self.model.to(self.device)
        self.model.eval()

        self.transform = T.Compose([
            T.Resize((518, 518)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def get_embedding(self, img_path):
        img = Image.open(img_path).convert('RGB')
        img_t = self.transform(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            embedding = self.model(img_t)
        return embedding.cpu().numpy().flatten()

    def ingest_data_folder(self, folder_path):
        files = glob.glob(os.path.join(folder_path, "**", "*.jpg"), recursive=True) + \
                glob.glob(os.path.join(folder_path, "**", "*.png"), recursive=True)

        print(f"📂 {len(files)}개 이미지 발견. DB 저장을 시작합니다...")

        with psycopg.connect(**self.db_info, autocommit=True) as conn:
            register_vector(conn)
            with conn.cursor() as cursor:
                for i, filepath in enumerate(files):
                    defect_type = os.path.basename(os.path.dirname(filepath))
                    filename = os.path.basename(filepath)
                    vector = self.get_embedding(filepath)

                    cursor.execute(
                        "INSERT INTO defect_images (filename, defect_type, embedding) VALUES (%s, %s, %s)",
                        (filename, defect_type, vector)
                    )

                    if (i + 1) % 10 == 0:
                        print(f"   Saving... {i + 1}/{len(files)}")

        print("✅ DB 저장 완료!")

    def search(self, query_img_path, top_k=5):
        query_vector = self.get_embedding(query_img_path)

        with psycopg.connect(**self.db_info, autocommit=True) as conn:
            register_vector(conn)
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT defect_type, filename, (embedding <-> %s) as distance
                    FROM defect_images
                    ORDER BY distance ASC
                    LIMIT %s
                """, (query_vector, top_k))

                results = cursor.fetchall()

        detailed_board = {}
        print(f"\n🔍 PostgreSQL 검색 결과 (Top {top_k}):")
        print("-" * 90)

        for defect_type, fname, dist in results:
            # 점수 계산
            score = 100000 / (dist + 1.0)
            print(f"   - [{defect_type}] {fname} (거리: {dist:.4f}, 점수: {score:.2f})")

            if defect_type not in detailed_board:
                detailed_board[defect_type] = {'total_score': 0, 'files': []}

            detailed_board[defect_type]['total_score'] += score
            detailed_board[defect_type]['files'].append((fname, score))

        print("-" * 90)

        # =====================================================
        # ★ 여기가 복구된 최종 판정 로직입니다 ★
        # =====================================================
        if not detailed_board:
            print("✅ 최종 판정: 알 수 없음 (DB에 데이터가 없거나 검색 실패)")
        else:
            # 점수 합계가 가장 높은 결함 찾기
            sorted_defects = sorted(detailed_board.items(), key=lambda item: item[1]['total_score'], reverse=True)

            best_defect = sorted_defects[0][0]  # 1등 결함 이름
            best_data = sorted_defects[0][1]  # 1등 정보

            print(f"🏆 최종 판정: '{best_defect}'")
            print(f"   (이유: 유사도 점수 합계 {best_data['total_score']:.2f}점으로 1위)")

            print(f"\n   📂 [{best_defect} 판정의 근거 데이터]")
            for i, (fname, score) in enumerate(best_data['files']):
                print(f"     {i + 1}. {fname} (기여 점수: {score:.2f}점)")

            print("\n" + "=" * 50)

        return detailed_board