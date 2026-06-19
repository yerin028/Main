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

  // 인식할 수어의 카테고리는 백엔드 API 규격을 유지하기 위해 내부 고정 상태로 '개념'을 지정합니다.
  const [category] = useState('개념');

  // videoRef는 JSX의 <video> 태그에 직접 접근하기 위한 참조입니다.
  const videoRef = useRef(null);

  // streamRef에는 브라우저 카메라 스트림 객체를 저장합니다.
  const streamRef = useRef(null);

  // 카메라 화면을 보여줘야 하는 상태인지 계산해 둔 값입니다.
  const isCameraReady = cameraStatus === 'ready' || cameraStatus === 'translating';

  // 켜져 있는 카메라 스트림을 모두 종료합니다.
  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  // 시작하기 버튼을 눌렀을 때 실행되는 함수입니다.
  const handleStartCamera = async () => {
    setErrorMessage('');

    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMessage('현재 브라우저에서 카메라 기능을 사용할 수 없습니다.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setCameraStatus('ready');
      setResult(initialResult);
    } catch (error) {
      console.error(error);
      setErrorMessage('카메라 권한을 허용해야 수어통역을 시작할 수 있습니다.');
    }
  };

  // 현재 video 화면 한 장면을 캡처해서 base64 이미지 문자열로 변환합니다.
  const captureFrame = () => {
    const video = videoRef.current;

    if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      throw new Error('카메라 화면이 아직 준비되지 않았습니다.');
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    return canvas.toDataURL('image/jpeg', 0.88);
  };

  // 번역하기 버튼을 눌렀을 때 실행되는 단발성 번역 함수입니다.
  const handleTranslate = async () => {
    setErrorMessage('');
    setCameraStatus('translating');

    try {
      const imageData = captureFrame();

      const response = await fetch(`${API_BASE_URL}/api/v1/interpreter/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_data: imageData,
          input_type: 'camera',
          language_from: 'ko',
          language_to: 'en',
          category: category,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail ?? '번역 요청에 실패했습니다.');
      }

      const data = await response.json();

      setResult({
        koreanText: data.korean_text,
        englishText: data.english_text,
        confidence: data.confidence,
      });

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

  // 컴포넌트 언마운트 시 리소스를 정리합니다.
  useEffect(() => {
    return () => {
      stopCamera();
    };
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
              {/* 번역하기 버튼 */}
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
            <p>시작하기를 누른 뒤 카메라 화면이 보이면 번역할 동작을 취해 주세요.</p>
          </div>
          <div className="guide-step">
            <span>3</span>
            <p>동작을 취한 상태에서 번역하기 버튼을 누르면 수어 해석 결과가 표시됩니다.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Interpreter;
