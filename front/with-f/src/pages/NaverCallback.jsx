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

        fetch(`http://localhost:8000/api/v1/auth/login/naver?code=${code}&state=${state}`, {
      method: 'POST',
    })
        .then(res => res.json())
        .then(data => {
            console.log('네이버 로그인 성공:', data);
            navigate('/home');
        })
        .catch(err => {
            console.error('네이버 로그인 실패:', err);
        });
    }, []);

    return <div>네이버 로그인 처리 중</div>;
}

export default NaverCallback;