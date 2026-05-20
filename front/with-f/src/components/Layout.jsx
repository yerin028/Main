import { useNavigate, useLocation } from 'react-router-dom';
import './Layout.css';

function Layout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();

  const getActiveMenu = () => {
    const path = location.pathname;
    if (path.includes('/interpreter')) return '수어통역';
    if (path.includes('/learn')) return '수어학습';
    if (path.includes('/dictionary')) return '수어검색';
    if (path.includes('/quiz')) return '수어퀴즈';
    if (path.includes('/cs')) return '고객센터';
    return '';
  };

  const activeMenu = getActiveMenu();

  const menuItems = [
    { label: '수어통역', path: '/interpreter' },
    { label: '수어학습', path: '/learn' },
    { label: '수어검색', path: '/dictionary' },
    { label: '수어퀴즈', path: '/quiz' },
    { label: '고객센터', path: '/cs' },
  ];

  return (
    <div className="layout-wrapper">
      {/* 상단 네비게이션 바 */}
      <header className="navbar">
        {/* 로고 버튼 - 클릭 시 홈으로 이동 */}
        <div className="navbar-logo" onClick={() => navigate('/home')}>
          Main
        </div>

        {/* 메뉴 */}
        <nav className="navbar-menu">
          {menuItems.map((item) => (
            <span
              key={item.label}
              className={`navbar-item ${activeMenu === item.label ? 'active' : ''}`}
              onClick={() => navigate(item.path)}
            >
              {item.label}
              {activeMenu === item.label && <div className="navbar-underline" />}
            </span>
          ))}
        </nav>

        {/* 홈 아이콘 버튼 */}
        <div className="navbar-home-icon" onClick={() => navigate('/home')}>
          
        </div>
      </header>

      {/* 구분선 */}
      <div className="navbar-divider" />

      {/* 페이지 콘텐츠 영역 */}
      <main className="layout-content">
        {children}
      </main>
    </div>
  );
}

export default Layout;