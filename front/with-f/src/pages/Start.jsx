// 시작화면

import { useNavigate } from 'react-router-dom';
import './Start.css';

function Start() {
    const navigate = useNavigate();

    return (
        <div className='start-wrapper'>
            <div className='start-card'>
                <h1 className='start-logo'>Main</h1>
                <p className='start-subtitle'>수어 통역 및 학습을 시작해보세요</p>
                <div className='start-buttons'>
                    <button className='start-btn-fill' onClick={() => navigate('/login')}>시작하기</button>
                </div>
            </div>
        </div>
    )
}

export default Start;