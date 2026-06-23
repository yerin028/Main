import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

function NaverCallback() {
    const navigate = useNavigate();
    const called = useRef(false);

    useEffect(() => {
        if (called.current) return;
        called.current = true;

        const code = new URL(window.location.href).searchParams.get('code');
        const state = new URL(window.location.href).searchParams.get('state');

        // 🚀 하드코딩 주소 대신 깃허브 액션이 주입해준 환경변수를 읽도록 수정
        const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

        fetch(`${API_BASE_URL}/api/v1/auth/login/naver?code=${code}&state=${state}`, {
            method: 'POST',
        })
        .then(res => {
            if (!res.ok) {
                return res.json().then(err => { throw new Error(err.detail); });
            }
            return res.json();
        })
        .then(data => {
            console.log('네이버 로그인 성공:', data);
            if (data.user_id) {
                localStorage.setItem("user_id", String(data.user_id));
            }
            if (data.nickname) {
                localStorage.setItem("user_name", data.nickname);
            }
            if (data.email) {
                localStorage.setItem("user_email", data.email);
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

    return <div>네이버 로그인 처리 중</div>;
}

export default NaverCallback;