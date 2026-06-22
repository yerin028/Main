# --- 1단계: Node.js를 이용해 리액트 앱 빌드 ---
FROM node:20-alpine AS build
 
WORKDIR /app
 
# 패키지 파일 복사 및 설치
COPY package*.json ./
RUN npm install
 
# 전체 소스 복사 후 프로덕션용 빌드 실행 (dist 폴더 생성)
COPY . .
RUN npm run build
 
# --- 2단계: 빌드된 정적 파일을 Nginx로 배포 ---
FROM nginx:alpine
 
# Vite가 빌드한 결과물(dist)을 Nginx의 웹 루트 디렉터리로 복사
COPY --from=build /app/dist /usr/share/nginx/html
 
# Nginx의 기본 80 포트 개방
EXPOSE 80
 
CMD ["nginx", "-g", "daemon off;"]
 