// 📄 KakaoCallback.jsx 수정본
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

function KakaoCallback() {
    const navigate = useNavigate();

    useEffect(() => {
        const code = new URL(window.location.href).searchParams.get('code');

        // 🚀 중요: 하드코딩 주소를 지우고, 깃허브 액션이 주입해주는 환경변수를 읽도록 수정해!
        const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

        fetch(`${API_BASE_URL}/api/v1/auth/login/kakao?code=${code}`, {
            method: 'POST',
        })
        .then(res => {
            if (!res.ok) {
                return res.json().then(err => { throw new Error(err.detail); });
            }
            return res.json();
        })
        .then(data => {
            console.log('로그인 성공:', data);
            if (data.user_id) {
              localStorage.setItem("user_id", String(data.user_id));
            }
            if (data.nickname) {
              localStorage.setItem("user_name", data.nickname);
            }
            if (data.role) {
              localStorage.setItem("user_role", data.role);
            }
            navigate('/home');
        })
        .catch(err => {
            localStorage.clear();
            alert(err.message || '로그인 실패');
            navigate('/');
        });
    }, []);

    return <div>카카오 로그인 처리 중</div>;
}

export default KakaoCallback;