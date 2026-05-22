from fastapi import APIRouter
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# 카카오
VITE_KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
VITE_KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

# 네이버
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI = os.getenv("NAVER_REDIRECT_URI")

print("CLIENT_ID:", VITE_KAKAO_CLIENT_ID)
print("REDIRECT_URI:", VITE_KAKAO_REDIRECT_URI)

# 카카오
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
    print("카카오 토큰 데이터:", token_data)
    access_token = token_data.get("access_token")
    print("카카오 액세스 토큰:", access_token)

    # 2. 토큰으로 사용자 정보 가져오기
    user_response = await httpx.AsyncClient().get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user_data = user_response.json()
    print("카카오 유저 데이터:", user_data)  

    # 3. 사용자 정보 DB
    kakao_id = str(user_data.get("id"))
    # nickname = user_data.get("kakao_account", {}).get("profile", {}).get("nickname")
    
    # 변경된 부분 (핵심)
    nickname = (
        user_data
        .get("kakao_account", {})
        .get("profile", {})
        .get("nickname")
    )

    return {"kakao_id": kakao_id, "nickname": nickname}


# 네이버
@router.post("/login/naver")
async def naver_login(code: str, state: str):
    # 1. 네이버에서 토큰 받기
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://nid.naver.com/oauth2.0/token",
            data={
                "grant_type": "authorization_code",
                "client_id": NAVER_CLIENT_ID,
                "client_secret": NAVER_CLIENT_SECRET,
                "redirect_uri": NAVER_REDIRECT_URI,
                "code": code,
                "state": state,
            }
        )
        token_data = token_response.json()
        print("네이버 토큰 데이터:", token_data)
        access_token = token_data.get("access_token")

        # 2. 토큰으로 사용자 정보 가져오기
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://openapi.naver.com/v1/nid/me", # 이건 뭥미
                headers={"Authorization": f"Bearer {access_token}"}
            )
        user_data = user_response.json()
        print("네이버 유저 데이터:", user_data)

        # 3. 사용자 정보
        naver_id = user_data.get("response", {}).get("id")
        nickname = user_data.get("response", {}).get("nickname")
        email = user_data.get("response", {}).get("email")

        return {"naver_id": naver_id, "nickname": nickname, "email": email}