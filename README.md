# Main(마인)

한국 수어 AI 통역 및 학습 플랫폼

---

## 프로젝트 개요

국내 청각장애인은 약 43만 명이지만 수어 통역사는 극심하게 부족합니다. Main은 웹캠 기반 AI 수어 인식으로 통역사 없이 즉각적인 소통을 지원하고, 수어 학습 콘텐츠를 함께 제공합니다.

- 팀명: TEAM WITH (5인)
- 기간: 2026.05 ~ 2026.06

---

## 기술 스택

**Frontend** React, Vite
**Backend** FastAPI, Python
**Database** MySQL, MongoDB
**AI** Azure OpenAI, MediaPipe, LSTM
**Infra** Docker, AWS EC2, GitHub Actions
**Payment** 토스페이먼츠

---

## 주요 기능

- **수어 통역**: 웹캠 수어 동작 인식 → MediaPipe + LSTM 분석 → Azure OpenAI로 문장 변환
- **수어 학습 / 검색**: 국립수어원 API 데이터 기반 학습, 진행 상황 저장
- **수어 퀴즈**: 학습 단어 기반 객관식 퀴즈 자동 생성 (구독 회원 전용)
- **결제 / 구독**: 무료·4,900원·9,900원 플랜, 토스페이먼츠 연동
- **고객센터**: 문의, 환불 신청, 회원 탈퇴
- **관리자 페이지**: 문의 답변, 환불 승인/거절 (승인 시 토스 환불 자동 처리)
- **회원 관리**: 카카오/네이버/구글 소셜 로그인

---

## 실행 방법

```bash
# Frontend
cd front/with-f
npm install
npm run dev

# Backend
cd back
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## 팀원

| 이름 | 역할 |
|------|------|
| 신예린 | 팀장 / Frontend, Backend |
| 서승민 | 팀원 / AI, Frontend, Backend |
| 김진욱 | 팀원 / Frontend, Backend |
| 임현진 | 팀원 / Frontend, Backend |
| 석연화 | 팀원 / Frontend, Backend |