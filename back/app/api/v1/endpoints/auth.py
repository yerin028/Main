from fastapi import APIRouter
import httpx
import os

router = APIRouter()

VITE_KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
VITE_KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

@router.post("/login/kakao")
async def kakao_login(code:str):
    # 1. 카카오에서 토큰 받기
    token_response  =await httpx.AsyncClient().post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": VITE_KAKAO_CLIENT_ID,
            "redirect_uri": VITE_KAKAO_REDIRECT_URI,
            "code": code,
        }
    )
    token_data = token_response.json()
    access_token = token_data.get("access_token")

    # 2. 토큰으로 사용자 정보 가져오기
    user_response = await httpx.AsyncClient().get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user_data = user_response.json()

    # 3. 사용자 정보 DB
    kakao_id = str(user_data.get("id"))
    nickname = user_data.get("kakao_account", {}).get("profile", {}).get("nickname")

    return {"kakao_id": kakao_id, "nickname": nickname}