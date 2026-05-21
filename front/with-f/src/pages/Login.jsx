// 로그인

import { useNavigate } from "react-router-dom";
import './Login.css'

function Login() {
    const KAKAO_CLIENT_ID = import.meta.env.VITE_KAKAO_CLIENT_ID;
    const KAKAO_REDIRECT_URI = import.meta.env.VITE_KAKAO_REDIRECT_URI;

    const kakaoLogin = () => {
        window.location.href = `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_CLIENT_ID}&redirect_uri=${KAKAO_REDIRECT_URI}&response_type=code`;
    };

    return (
        <div className="login-wrapper">
            <div className="login-card">
                <h1 className="login-title">로그인</h1>
                <button className="kakao-btn" onClick={kakaoLogin}>카카오로 로그인</button>
            </div>
        </div>
    );
}

export default Login;