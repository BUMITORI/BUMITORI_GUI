# Python 3.9 Slim 이미지를 기반으로 사용
FROM python:3.9-slim

# 필수 패키지 설치 (OpenGL 및 python 관련 패키지 설치)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    python3-pip \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 로컬 파일을 컨테이너로 복사
COPY . /app

# 가상환경 생성 (이 명령어는 이미 설치된 python3를 사용)
RUN python3 -m venv .venv

# 가상환경 활성화 및 패키지 설치
RUN . .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# GUI를 위해 DISPLAY 환경변수 설정
ENV DISPLAY=:0

# 앱 실행
CMD ["/app/.venv/bin/python", "main.py"]
