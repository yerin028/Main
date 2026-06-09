// 카카오 로그인

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

function KakaoCallback() {
    const navigate = useNavigate();

    useEffect(() => {
        const code = new URL(window.location.href).searchParams.get('code');
        console.log(code);

        // 백엔드로 code 전송
        fetch(`http://localhost:8000/api/v1/auth/login/kakao?code=${code}`, {
            method: 'POST',
        })
          .then(res => res.json())
          .then(data => {
            console.log('로그인 성공:', data);
            localStorage.setItem('user_id', data.user_id);
            navigate('/home');
          })
          .catch(err => {
            console.error('로그인 실패:', err);
          });
    }, []);

    return <div>카카오 로그인 처리 중</div>;
}

export default KakaoCallback;