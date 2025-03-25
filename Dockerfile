# Python 3.9 이미지 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (PyQt와 시리얼 통신을 위한 라이브러리 포함)
RUN apt-get update && \
    apt-get install -y \
    libxcb-xinerama0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libegl1-mesa \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사
COPY requirements.txt /app/

# 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 코드 복사
COPY . /app/

# PyQt 애플리케이션 실행
CMD ["python", "main.py"]
