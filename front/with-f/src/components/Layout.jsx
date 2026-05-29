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
    if (path.includes('/cs') || path.includes('/admin')) return '고객센터';

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

  const handleMenuClick = (item) => {
    if (item.path === '/dictionary') {
      navigate('/dictionary', { state: { resetAt: Date.now() } });
      return;
    }

    if (item.path === '/cs' && localStorage.getItem('user_role') === 'admin') {
      navigate('/admin');
      return;
    }

    navigate(item.path);
  };

  return (
    <div className="layout-wrapper">
      <header className="navbar">
        <div className="navbar-logo" onClick={() => navigate('/home')}>
          Main
        </div>

        <nav className="navbar-menu">
          {menuItems.map((item) => (
            <span
              key={item.label}
              className={`navbar-item ${activeMenu === item.label ? 'active' : ''}`}
              onClick={() => handleMenuClick(item)}
            >
              {item.label}
              {activeMenu === item.label && <div className="navbar-underline" />}
            </span>
          ))}
        </nav>

        <div className="navbar-home-icon" onClick={() => navigate('/home')} />
      </header>

      <div className="navbar-divider" />

      <main className="layout-content">
        {children}
      </main>
    </div>
  );
}

export default Layout;
