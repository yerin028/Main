import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

function GoogleCallback() {
    const navigate = useNavigate();
    const called = useRef(false);

    useEffect(() => {
        if (called.current) return;
        called.current = true;

        const code = new URL(window.location.href).searchParams.get('code');

        fetch(`http://localhost:8000/api/v1/auth/login/google?code=${code}`, {
            method: 'POST'
        })
            .then(res => res.json())
            .then(data => {
                console.log('구글 로그인 성공:', data);
                localStorage.setItem('user_id', data.user_id);
                navigate('/home');
            })
            .catch(err => {
                console.error('구글 로그인 실패:', err);
            });
    }, []);

    return <div>구글 로그인 처리 중</div>
}

export default GoogleCallback;