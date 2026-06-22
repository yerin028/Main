import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

function KakaoCallback() {
    const navigate = useNavigate();

    useEffect(() => {
        const code = new URL(window.location.href).searchParams.get('code');

        fetch(`http://localhost:8000/api/v1/auth/login/kakao?code=${code}`, {
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
            alert(err.message || '로그인 실패');
            navigate('/');
        });
    }, []);

    return <div>카카오 로그인 처리 중</div>;
}

export default KakaoCallback;
