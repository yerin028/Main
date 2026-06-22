# 파이썬 3.11 슬림 버전 이미지 사용
FROM python:3.11-slim

WORKDIR /app

# mediapipe, opencv 실행에 필요한 시스템 라이브러리 설치
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 현재 백엔드 폴더(backend/)에 있는 모든 파일과 폴더를 컨테이너 안으로 통째로 복사
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]