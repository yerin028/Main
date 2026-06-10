// 홈
import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import './Home.css';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const getCurrentUserId = () => {
    const userId = Number(localStorage.getItem('user_id'));
    return Number.isFinite(userId) && userId > 0 ? userId : null;
};

function Home() {
    const navigate = useNavigate();
    const location = useLocation();
    const [lastLessonProgress, setLastLessonProgress] = useState(null);
    const [todayStats, setTodayStats] = useState({ studied_count: 0, percent: 0 });

    const handleLogout = () => {
        navigate('/');
    };

    useEffect(() => {
        const userId = getCurrentUserId();
        if (!userId) return;

        const loadLastLessonProgress = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/lessons/progress/latest?user_id=${userId}`);
                if (!response.ok) return;
                const data = await response.json();
                setLastLessonProgress(data);
            } catch {
                setLastLessonProgress(null);
            }
        };

        const loadTodayStats = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/lessons/progress/today-stats?user_id=${userId}`);
                if (!response.ok) return;
                const data = await response.json();
                setTodayStats(data);
            } catch {
                setTodayStats({ studied_count: 0, percent: 0 });
            }
        };

        loadLastLessonProgress();
        loadTodayStats();
    }, [location]);

    const goToLastLesson = () => {
        if (!lastLessonProgress?.category_id) return;
        navigate(`/learn?category_id=${lastLessonProgress.category_id}`);
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
                        <p>오늘 학습한 단어 {todayStats.studied_count}개</p>
                        <div className="progress-bar-wrapper">
                            <div
                                className="progress-bar-fill"
                                style={{ width: `${todayStats.percent}%` }}
                            />
                        </div>
                    </div>
                </div>

                {/* 마지막 학습 단어 */}
                <div
                    className={`home-card ${lastLessonProgress ? '' : 'disabled'}`}
                    onClick={goToLastLesson}
                >
                    <div className="home-card-icon">📖</div>
                    <div className="home-card-content">
                        <h3>마지막으로 학습한 단어</h3>
                        <p>
                            {lastLessonProgress
                                ? `${lastLessonProgress.category_name ?? '수어학습'} · ${lastLessonProgress.word ?? '저장된 단어'}부터 이어가기`
                                : '저장된 학습 기록이 없습니다.'}
                        </p>
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