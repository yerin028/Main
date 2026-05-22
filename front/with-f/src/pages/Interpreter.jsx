import { useEffect, useRef, useState } from 'react';
import './Interpreter.css';

// 백엔드 FastAPI 서버 주소입니다.
// .env 파일에 VITE_API_BASE_URL을 따로 설정하면 그 값을 사용하고,
// 없으면 개발 환경 기본 주소인 http://127.0.0.1:8000으로 요청합니다.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

// 화면이 처음 열렸을 때 결과 카드에 보여 줄 기본 문구입니다.
// 번역 API 응답을 받으면 이 값이 실제 인식/번역 결과로 바뀝니다.
const initialResult = {
  koreanText: '수어 인식 결과가 여기에 표시됩니다.',
  englishText: '영어 번역 결과가 여기에 표시됩니다.',
  confidence: null,
};

function Interpreter() {
  // cameraStatus는 현재 수어통역 화면의 진행 상태를 나타냅니다.
  // idle: 카메라 시작 전
  // ready: 카메라가 켜졌고 번역할 수 있는 상태
  // translating: 번역 API 요청을 보내고 응답을 기다리는 상태
  const [cameraStatus, setCameraStatus] = useState('idle');

  // 백엔드에서 받은 한국어 인식 결과, 영어 번역 결과, 신뢰도를 저장합니다.
  const [result, setResult] = useState(initialResult);

  // 카메라 권한 거부, API 실패 같은 오류 메시지를 화면에 보여주기 위한 상태입니다.
  const [errorMessage, setErrorMessage] = useState('');

  // videoRef는 JSX의 <video> 태그에 직접 접근하기 위한 참조입니다.
  // React에서는 DOM 요소를 직접 다뤄야 할 때 useRef를 사용합니다.
  const videoRef = useRef(null);

  // streamRef에는 브라우저 카메라 스트림 객체를 저장합니다.
  // 컴포넌트가 다시 렌더링되어도 스트림을 유지하고,
  // 종료할 때 getTracks().stop()으로 카메라를 안전하게 끌 수 있습니다.
  const streamRef = useRef(null);

  // 카메라 화면을 보여줘야 하는 상태인지 계산해 둔 값입니다.
  // JSX 안의 조건문을 더 읽기 쉽게 만들기 위해 변수로 분리했습니다.
  const isCameraReady = cameraStatus === 'ready' || cameraStatus === 'translating';

  // 켜져 있는 카메라 스트림을 모두 종료합니다.
  // 페이지를 나가거나 종료하기 버튼을 눌렀을 때 카메라가 계속 켜져 있지 않도록 필요합니다.
  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  // 시작하기 버튼을 눌렀을 때 실행되는 함수입니다.
  // 브라우저에 카메라 권한을 요청하고, 허용되면 <video> 태그에 실시간 화면을 연결합니다.
  const handleStartCamera = async () => {
    setErrorMessage('');

    // 일부 브라우저나 보안이 낮은 주소에서는 카메라 API가 제공되지 않을 수 있습니다.
    // localhost/127.0.0.1 또는 https 환경에서 테스트하는 것이 안전합니다.
    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMessage('현재 브라우저에서 카메라 기능을 사용할 수 없습니다.');
      return;
    }

    try {
      // getUserMedia는 브라우저의 카메라/마이크 접근 권한을 요청하는 표준 API입니다.
      // 여기서는 수어 인식용 영상만 필요하므로 audio는 false로 둡니다.
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = stream;

      // video 태그의 srcObject에 스트림을 넣으면 실시간 카메라 화면이 재생됩니다.
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      // 카메라가 켜졌으므로 버튼을 "번역하기" 상태로 바꾸기 위해 ready로 변경합니다.
      setCameraStatus('ready');
      setResult(initialResult);
    } catch (error) {
      console.error(error);
      setErrorMessage('카메라 권한을 허용해야 수어통역을 시작할 수 있습니다.');
    }
  };

  // 현재 video 화면 한 장면을 캡처해서 base64 이미지 문자열로 변환합니다.
  // 백엔드는 이 이미지 데이터를 받아 수어 인식 모델에 넘기는 구조로 확장할 수 있습니다.
  const captureFrame = () => {
    const video = videoRef.current;

    // video.readyState가 낮으면 아직 카메라 프레임이 준비되지 않은 상태입니다.
    // 이때 캡처하면 빈 이미지가 갈 수 있으므로 오류를 발생시킵니다.
    if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      throw new Error('카메라 화면이 아직 준비되지 않았습니다.');
    }

    // canvas는 화면에 직접 보이지 않는 임시 그림판입니다.
    // video 화면을 canvas에 그린 뒤 이미지 데이터로 꺼내기 위해 사용합니다.
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // JPEG 형식의 data URL을 반환합니다.
    // 예: data:image/jpeg;base64,/9j/4AAQSk...
    return canvas.toDataURL('image/jpeg', 0.88);
  };

  // 번역하기 버튼을 눌렀을 때 실행되는 함수입니다.
  // 현재 카메라 프레임을 캡처해서 백엔드 번역 API로 보내고, 응답 결과를 화면에 표시합니다.
  const handleTranslate = async () => {
    setErrorMessage('');
    setCameraStatus('translating');

    try {
      const imageData = captureFrame();

      // 요구사항명세서에 적힌 API입니다.
      // 프론트는 image_data에 캡처 이미지를 담아 보내고,
      // 백엔드는 korean_text / english_text / confidence를 반환합니다.
      const response = await fetch(`${API_BASE_URL}/api/v1/interpreter/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_data: imageData,
          input_type: 'camera',
          language_from: 'ko',
          language_to: 'en',
        }),
      });

      // HTTP 상태 코드가 200번대가 아니면 실패로 보고 오류 메시지를 표시합니다.
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail ?? '번역 요청에 실패했습니다.');
      }

      const data = await response.json();

      // API 응답을 React 상태에 저장하면 화면의 결과 카드가 자동으로 다시 렌더링됩니다.
      setResult({
        koreanText: data.korean_text,
        englishText: data.english_text,
        confidence: data.confidence,
      });

      // 번역 요청이 끝났으므로 다시 번역 가능한 ready 상태로 되돌립니다.
      setCameraStatus('ready');
    } catch (error) {
      console.error(error);
      setErrorMessage(error.message ?? '번역 중 오류가 발생했습니다.');
      setCameraStatus('ready');
    }
  };

  // 종료하기 버튼을 눌렀을 때 카메라와 화면 상태를 모두 초기화합니다.
  const handleReset = () => {
    stopCamera();
    setCameraStatus('idle');
    setResult(initialResult);
    setErrorMessage('');
  };

  // 컴포넌트가 화면에서 사라질 때 실행됩니다.
  // 예를 들어 다른 메뉴로 이동하면 수어통역 페이지가 언마운트되는데,
  // 이때 카메라 스트림을 정리하지 않으면 카메라가 계속 켜져 있을 수 있습니다.
  useEffect(() => {
    return () => stopCamera();
  }, []);

  return (
    <div className="interpreter-page">
      {/* 왼쪽 영역: 카메라 화면과 시작/번역/종료 버튼 */}
      <section className="interpreter-camera-panel" aria-label="수어통역 카메라">
        <div className="camera-stage">
          <video
            ref={videoRef}
            className={isCameraReady ? 'camera-video is-visible' : 'camera-video'}
            autoPlay
            playsInline
            muted
          />

          {/* 카메라가 아직 켜지지 않았을 때 보여주는 안내 화면입니다. */}
          {!isCameraReady && (
            <div className="camera-placeholder">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5.2 7.2h3.1l1.4-1.8h4.6l1.4 1.8h3.1A2.2 2.2 0 0 1 21 9.4v7.4a2.2 2.2 0 0 1-2.2 2.2H5.2A2.2 2.2 0 0 1 3 16.8V9.4a2.2 2.2 0 0 1 2.2-2.2Z" />
                <circle cx="12" cy="13" r="3.2" />
              </svg>
              <p>시작하기 버튼을 누르면 카메라가 활성화됩니다.</p>
            </div>
          )}
        </div>

        <div className="interpreter-actions">
          {/* idle 상태에서는 시작하기 버튼만 보여줍니다. */}
          {cameraStatus === 'idle' ? (
            <button type="button" className="primary-action" onClick={handleStartCamera}>
              시작하기
            </button>
          ) : (
            <>
              {/* ready 상태에서는 번역하기, translating 상태에서는 번역 중으로 표시합니다. */}
              <button
                type="button"
                className="primary-action"
                onClick={handleTranslate}
                disabled={cameraStatus === 'translating'}
              >
                {cameraStatus === 'translating' ? '번역 중' : '번역하기'}
              </button>
              <button type="button" className="secondary-action" onClick={handleReset}>
                종료하기
              </button>
            </>
          )}
        </div>

        {errorMessage && <p className="error-message">{errorMessage}</p>}
      </section>

      {/* 오른쪽 영역: 백엔드에서 받은 수어 인식 결과와 영어 번역 결과 */}
      <aside className="translation-panel" aria-label="번역 결과">
        <article className="translation-card">
          <p className="translation-label">수어 인식 결과</p>
          <p className="translation-text">{result.koreanText}</p>
          {result.confidence !== null && (
            <p className="confidence-text">신뢰도 {Math.round(result.confidence * 100)}%</p>
          )}
        </article>

        <article className="translation-card">
          <p className="translation-label">영어 번역 결과</p>
          <p className="translation-text">{result.englishText}</p>
        </article>
      </aside>

      {/* 하단 영역: 요구사항명세서의 유의사항/튜토리얼 안내 */}
      <section className="guide-panel" aria-label="수어통역 유의사항">
        <h2>수어통역 유의사항</h2>
        <div className="guide-steps">
          <div className="guide-step">
            <span>1</span>
            <p>카메라가 손과 얼굴을 잘 볼 수 있도록 화면 중앙에 위치해 주세요.</p>
          </div>
          <div className="guide-step">
            <span>2</span>
            <p>시작하기를 누른 뒤 카메라 화면이 보이면 번역하기를 눌러 주세요.</p>
          </div>
          <div className="guide-step">
            <span>3</span>
            <p>번역 결과는 한국어 인식 문장과 영어 번역 문장으로 표시됩니다.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Interpreter;
