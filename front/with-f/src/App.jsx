import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Start from './pages/Start';
import Login from './pages/Login';
import Home from './pages/Home';
import Interpreter from './pages/Interpreter';
import Learn from './pages/Learn';
import Dictionary from './pages/Dictionary';
import Quiz from './pages/Quiz';
import CustomerService from './pages/CustomerService';
import Payment from './pages/Payment';
import Admin from './pages/Admin';
import KakaoCallback from './pages/KakaoCallback';
import NaverCallback from './pages/NaverCallback';
import GoogleCallback from './pages/GoogleCallback';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 네비게이션 바 없는 화면 */}
        <Route path="/" element={<Start />} />
        <Route path="/login" element={<Login />} />

        {/* 네비게이션 바 있는 화면 */}
        <Route path="/home" element={<Layout><Home /></Layout>} />
        <Route path="/interpreter" element={<Layout><Interpreter /></Layout>} />
        <Route path="/learn" element={<Layout><Learn /></Layout>} />
        <Route path="/dictionary" element={<Layout><Dictionary /></Layout>} />
        <Route path="/quiz" element={<Layout><Quiz /></Layout>} />
        <Route path="/cs" element={<Layout><CustomerService /></Layout>} />
        <Route path="/payment" element={<Layout><Payment /></Layout>} />
        <Route path="/admin" element={<Layout><Admin /></Layout>} />
        <Route path="/login/oauth2/code/kakao" element={<KakaoCallback />} />
        <Route path="/login/oauth2/code/naver" element={<NaverCallback />} />
        <Route path="/login/oauth2/code/google" element={<GoogleCallback />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;