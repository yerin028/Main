import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import './Learn.css';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';
const lessonPageSize = 1000;
const visiblePageCount = 5;

const fallbackCategories = [
  { category_id: 1, name: '사회생활', icon: 'fi fi-br-hand-paper', description: '', sort_order: 1 },
  { category_id: 2, name: '일상생활', icon: 'hands', description: '', sort_order: 2 },
  { category_id: 3, name: '삶/가족', icon: 'family', description: '', sort_order: 3 },
  { category_id: 4, name: '교육/정보', icon: 'school', description: '', sort_order: 4 },
  { category_id: 5, name: '교통/지역', icon: 'bus', description: '', sort_order: 5 },
  { category_id: 6, name: '개념/자연', icon: 'clock', description: '', sort_order: 6 },
  { category_id: 7, name: '인간/감정', icon: 'face', description: '', sort_order: 7 },
  { category_id: 8, name: '기타/문화', icon: 'pen', description: '', sort_order: 8 },
];

const getVideoUrl = (videoUrl) => {
  if (!videoUrl) return null;
  return videoUrl.replace('http://sldict.korean.go.kr', 'https://sldict.korean.go.kr');
};

const getVideoPosterUrl = (videoUrl) => {
  if (!videoUrl) return undefined;
  return videoUrl.replace('_700X466.mp4', '_215X161.jpg');
};

const getCurrentUserId = () => {
  const userId = Number(localStorage.getItem('user_id'));
  return Number.isFinite(userId) && userId > 0 ? userId : null;
};

function FingerGuide({ onOpen }) {
  return (
    <section className="learn-finger-guide" aria-label="손가락 번호 안내">
      <button className="learn-finger-button" type="button" onClick={onOpen}>
        손가락 번호 안내 보기
      </button>
    </section>
  );
}

function Learn() {
  const [searchParams, setSearchParams] = useSearchParams();
  const categoryIdFromUrl = Number(searchParams.get('category_id')) || null;

  const [categories, setCategories] = useState(fallbackCategories);
  const [lessons, setLessons] = useState([]);
  const [selectedLessonId, setSelectedLessonId] = useState(null);
  const [lessonDetail, setLessonDetail] = useState(null);
  const [isFingerGuideOpen, setIsFingerGuideOpen] = useState(false);
  const [progressMessage, setProgressMessage] = useState('');
  const [isSavingProgress, setIsSavingProgress] = useState(false);

  const selectedCategory = useMemo(
    () => categories.find((category) => category.category_id === categoryIdFromUrl),
    [categories, categoryIdFromUrl],
  );

  const selectedLessonIndex = useMemo(
    () => lessons.findIndex((lesson) => lesson.lesson_id === selectedLessonId),
    [lessons, selectedLessonId],
  );

  const pageNumbers = useMemo(() => {
    const safeLessonIndex = Math.max(selectedLessonIndex, 0);
    const startIndex = Math.floor(safeLessonIndex / visiblePageCount) * visiblePageCount;

    return lessons
      .slice(startIndex, startIndex + visiblePageCount)
      .map((_, index) => startIndex + index + 1);
  }, [lessons, selectedLessonIndex]);
  const lessonVideoUrl = getVideoUrl(lessonDetail?.video_url);

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/lessons/categories`);
        if (!response.ok) return;

        const data = await response.json();
        setCategories(
          data.length > 0
            ? data.map((category) => ({
                ...category,
                icon:
                  fallbackCategories.find((item) => item.category_id === category.category_id)
                    ?.icon ?? 'person',
              }))
            : fallbackCategories,
        );
      } catch {
        setCategories(fallbackCategories);
      }
    };

    loadCategories();
  }, []);

  useEffect(() => {
    if (!categoryIdFromUrl) {
      setLessons([]);
      setSelectedLessonId(null);
      setLessonDetail(null);
      return;
    }

    const loadLessons = async () => {
      try {
        setLessonDetail(null);
        setProgressMessage('');
        const response = await fetch(
          `${API_BASE_URL}/lessons?category_id=${categoryIdFromUrl}&size=${lessonPageSize}`,
        );
        if (!response.ok) {
          throw new Error();
        }

        const data = await response.json();
        const nextLessons = data.lessons;
        let nextLessonId = nextLessons[0]?.lesson_id ?? null;
        const userId = getCurrentUserId();

        if (userId && nextLessonId) {
          const progressResponse = await fetch(
            `${API_BASE_URL}/lessons/progress?user_id=${userId}&category_id=${categoryIdFromUrl}`,
          );

          if (progressResponse.ok) {
            const progress = await progressResponse.json();
            const savedLesson = nextLessons.find(
              (lesson) => lesson.lesson_id === progress?.lesson_id,
            );

            if (savedLesson) {
              nextLessonId = savedLesson.lesson_id;
              setProgressMessage('저장된 위치부터 이어서 학습합니다.');
            }
          }
        }

        setLessons(nextLessons);
        setSelectedLessonId(nextLessonId);
      } catch {
        setLessons([]);
        setSelectedLessonId(null);
      }
    };

    loadLessons();
  }, [categoryIdFromUrl]);

  useEffect(() => {
    if (!selectedLessonId) return;

    const loadLessonDetail = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/lessons/${selectedLessonId}`);
        if (!response.ok) {
          throw new Error();
        }

        const data = await response.json();
        setLessonDetail(data);
      } catch {
        setLessonDetail(null);
      }
    };

    loadLessonDetail();
  }, [selectedLessonId]);

  const selectCategory = (categoryId) => {
    setSearchParams({ category_id: String(categoryId) });
  };

  const goBackToCategories = () => {
    setSearchParams({});
  };

  const goToLesson = (nextIndex) => {
    if (nextIndex < 0 || nextIndex >= lessons.length) return;
    setProgressMessage('');
    setSelectedLessonId(lessons[nextIndex].lesson_id);
  };

  const saveLessonProgress = async () => {
    const userId = getCurrentUserId();

    if (!userId) {
      setProgressMessage('로그인 후 학습 진행상황을 저장할 수 있습니다.');
      return;
    }

    if (!categoryIdFromUrl || !selectedLessonId || selectedLessonIndex < 0) {
      setProgressMessage('저장할 학습 위치가 없습니다.');
      return;
    }

    setIsSavingProgress(true);
    setProgressMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/lessons/progress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          category_id: categoryIdFromUrl,
          lesson_id: selectedLessonId,
          lesson_index: selectedLessonIndex,
          word: lessonDetail?.word ?? lessons[selectedLessonIndex]?.word ?? '',
        }),
      });

      if (!response.ok) {
        throw new Error();
      }

      setProgressMessage('현재 학습 위치를 저장했습니다.');
    } catch {
      setProgressMessage('학습 진행상황 저장에 실패했습니다.');
    } finally {
      setIsSavingProgress(false);
    }
  };

  if (!categoryIdFromUrl) {
    return (
      <section className="learn-page learn-category-page">
        <h1 className="learn-category-title">학습 카테고리</h1>

        <div className="learn-category-grid" aria-label="수어학습 카테고리">
          {categories.map((category) => (
            <button
              className="learn-category-card"
              key={category.category_id}
              type="button"
              onClick={() => selectCategory(category.category_id)}
            >
              <span className={`learn-category-icon ${category.icon}`} aria-hidden="true" />
              <strong>{category.name}</strong>
            </button>
          ))}
        </div>

        <FingerGuide onOpen={() => setIsFingerGuideOpen(true)} />

        {isFingerGuideOpen && (
          <div
            className="learn-modal-backdrop"
            role="presentation"
            onMouseDown={() => setIsFingerGuideOpen(false)}
          >
            <div
              className="learn-finger-modal"
              role="dialog"
              aria-modal="true"
              aria-label="손가락 번호 안내"
              onMouseDown={(event) => event.stopPropagation()}
            >
              <button
                className="learn-modal-close"
                type="button"
                aria-label="닫기"
                onClick={() => setIsFingerGuideOpen(false)}
              >
                ×
              </button>
              <img
                className="learn-finger-modal-image"
                src="/assets/finger-guide.webp"
                alt="1지는 집게손가락, 2지는 가운데손가락, 3지는 약손가락, 4지는 새끼손가락, 5지는 엄지손가락을 뜻하는 손가락 번호 안내"
              />
            </div>
          </div>
        )}
      </section>
    );
  }

  return (
    <section className="learn-page learn-study-page">
      <div className="learn-study-toolbar">
        <label htmlFor="learn-category-select">학습 카테고리</label>
        <select
          id="learn-category-select"
          className="learn-category-select"
          value={categoryIdFromUrl}
          onChange={(event) => selectCategory(Number(event.target.value))}
        >
          {categories.map((category) => (
            <option key={category.category_id} value={category.category_id}>
              {category.name}
            </option>
          ))}
        </select>
      </div>

      <div className="learn-study-main">
        <div className="learn-video-card" aria-label={`${lessonDetail?.word ?? '수어'} 학습 동영상`}>
          {lessonVideoUrl ? (
            <video
              key={lessonVideoUrl}
              src={lessonVideoUrl}
              poster={getVideoPosterUrl(lessonVideoUrl)}
              controls
              playsInline
              preload="metadata"
            />
          ) : (
            <>
              <div className="learn-video-placeholder">
                <span className="learn-camera-symbol" aria-hidden="true" />
              </div>
              <div className="learn-video-controls" aria-hidden="true">
                <span className="play-icon" />
                <span className="time-label">0:00 / 0:05</span>
                <span className="progress-track">
                  <span className="progress-fill" />
                  <span className="progress-thumb" />
                </span>
                <span className="sound-icon" />
                <span className="screen-icon" />
              </div>
            </>
          )}
        </div>

        <article className="learn-info-card">
          <p>단어</p>
          <h1>{lessonDetail?.word ?? lessons[0]?.word ?? '선택된 단어 없음'}</h1>
          <div className="learn-info-divider" />
          <strong>의미</strong>
          <span>{lessonDetail?.description ?? '표시할 수어 데이터가 없습니다.'}</span>
        </article>
      </div>

      <div className="learn-study-footer">
        <button className="learn-step-button" type="button" onClick={() => goToLesson(selectedLessonIndex - 1)} disabled={selectedLessonIndex <= 0}>
          이전
        </button>

        <div className="learn-page-select" aria-label="페이지 선택">
          <strong>페이지 선택</strong>
          <div className="learn-page-numbers">
            {pageNumbers.map((pageNumber) => (
              <button
                className={pageNumber - 1 === selectedLessonIndex ? 'active' : ''}
                key={pageNumber}
                type="button"
                onClick={() => goToLesson(pageNumber - 1)}
              >
                {pageNumber}
              </button>
            ))}
          </div>
        </div>

        <button className="learn-step-button" type="button" onClick={() => goToLesson(selectedLessonIndex + 1)} disabled={selectedLessonIndex === -1 || selectedLessonIndex >= lessons.length - 1}>
          다음
        </button>
      </div>

      <div className="learn-progress-actions">
        <button
          className="learn-save-progress-button"
          type="button"
          onClick={saveLessonProgress}
          disabled={isSavingProgress || selectedLessonIndex < 0}
        >
          {isSavingProgress ? '저장 중' : '학습 진행 저장'}
        </button>
        {progressMessage && <p>{progressMessage}</p>}
      </div>

      <button className="learn-back-button" type="button" onClick={goBackToCategories}>
        뒤로가기
      </button>
    </section>
  );
}

export default Learn;
