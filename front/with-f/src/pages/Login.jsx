// 로그인


import { useNavigate } from "react-router-dom";
import './Login.css'

function Login() {
    const KAKAO_CLIENT_ID = import.meta.env.VITE_KAKAO_CLIENT_ID;
    const KAKAO_REDIRECT_URI = import.meta.env.VITE_KAKAO_REDIRECT_URI;

    const NAVER_CLIENT_ID = import.meta.env.VITE_NAVER_CLIENT_ID;
    const NAVER_REDIRECT_URI = import.meta.env.VITE_NAVER_REDIRECT_URI;
    const NAVER_STATE = 'random_state_string';

    const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    const GOOGLE_REDIRECT_URI = import.meta.env.VITE_GOOGLE_REDIRECT_URI;

    const kakaoLogin = () => {
        window.location.href = `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_CLIENT_ID}&redirect_uri=${KAKAO_REDIRECT_URI}&response_type=code`;
    };

    const naverLogin = () => {
        window.location.href = `https://nid.naver.com/oauth2.0/authorize?client_id=${NAVER_CLIENT_ID}&redirect_uri=${NAVER_REDIRECT_URI}&response_type=code&state=${NAVER_STATE}`;
    };

    const googleLogin = () => {
        window.location.href = `https://accounts.google.com/o/oauth2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=${GOOGLE_REDIRECT_URI}&response_type=code&scope=email profile`;
    };

    return (
        <div className="login-wrapper">
            <div className="login-card">
                <h1 className="login-title">로그인</h1>
                <button className="kakao-btn" onClick={kakaoLogin}>카카오로 로그인</button>
                <button className="naver-btn" onClick={naverLogin}>네이버로 로그인</button>
                <button className="google-btn" onClick={googleLogin}>구글로 로그인</button>
            </div>
        </div>
    );
}

export default Login;