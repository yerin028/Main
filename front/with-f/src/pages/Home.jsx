// 홈

import { useNavigate } from "react-router-dom";
import './Home.css';

function Home() {
    const navigate = useNavigate();

    const handleLogout = () => {
        //이게 뭔디
        navigate('/');
    };

    return (
        <div className="home-wrapper">
            <div className="home-greeting">
                <h2>안녕하세요</h2>
                <p>오늘도 수어로 소통해요</p>
            </div>
            
            <div className="home-cards">
                {/* 수어 통역 이동 */}
                <div className="home-card" onClick={() => navigate('/interpreter')}>
                    <div className="home-card-icon">🤟</div>
                    <div className="home-card-content">
                        <h3>수어 통역 이동</h3>
                        <p>실시간 수어 통역 및 번역을 이용할 수 있습니다.</p>
                    </div>
                </div>

                {/* 학습 현황 */}
                <div className="home-card">
                    <div className="home-card-icon">📊</div>
                    <div className="home-card-content">
                        <h3>학습 현황</h3>
                        <p>오늘의 진도율을 그래프 및 퍼센트로 시작합니다.</p>
                    </div>
                </div>

                {/* 마지막 학습 단어 */}
                <div className="home-card">
                    <div className="home-card-icon">📖</div>
                    <div className="home-card-content">
                        <h3>마지막으로 학습한 단어</h3>
                        <p>마지막으로 학습한 단어의 영상/카테고리/단어이름을 나열합니다.</p>
                    </div>
                </div>

                {/* 결제 정보 */}
                <div className="home-card" onClick={() => navigate('/payment')}>
                    <div className="home-card-icon">💳</div>
                    <div className="home-card-content">
                        <h3>결제 정보</h3>
                        <p>이용 중인 플랜과 잔여 기간을 확인하세요.</p>
                    </div>
                </div>
            </div>

            {/* 로그아웃 버튼 */}
            <button className="home-logout-btn" onClick={handleLogout}>
                로그아웃
            </button>
        </div>
    );
}

export default Home;