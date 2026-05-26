import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import './Learn.css';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const fallbackCategories = [
  { category_id: 1, name: '인사', icon: 'person', description: '', sort_order: 1 },
  { category_id: 2, name: '일상생활', icon: 'hands', description: '', sort_order: 2 },
  { category_id: 3, name: '가족', icon: 'family', description: '', sort_order: 3 },
  { category_id: 4, name: '학교/직장', icon: 'school', description: '', sort_order: 4 },
  { category_id: 5, name: '교통/장소', icon: 'bus', description: '', sort_order: 5 },
  { category_id: 6, name: '시간/날짜', icon: 'clock', description: '', sort_order: 6 },
  { category_id: 7, name: '감정/상태', icon: 'face', description: '', sort_order: 7 },
  { category_id: 8, name: '기타', icon: 'pen', description: '', sort_order: 8 },
];

const fallbackLessons = fallbackCategories.flatMap((category) =>
  Array.from({ length: 5 }, (_, index) => ({
    lesson_id: category.category_id * 100 + index + 1,
    category_id: category.category_id,
    category_name: category.name,
    word: index === 0 ? '동생' : `단어 ${index + 1}`,
    video_url: null,
    video_type: 'placeholder',
    description: index === 0 ? '단어의 의미' : 'AI 학습 데이터가 추가되면 단어의 의미가 표시됩니다.',
    ai_model_key: null,
    sort_order: index + 1,
  })),
);

function Learn() {
  const [searchParams, setSearchParams] = useSearchParams();
  const categoryIdFromUrl = Number(searchParams.get('category_id')) || null;

  const [categories, setCategories] = useState(fallbackCategories);
  const [lessons, setLessons] = useState([]);
  const [selectedLessonId, setSelectedLessonId] = useState(null);
  const [lessonDetail, setLessonDetail] = useState(null);

  const selectedCategory = useMemo(
    () => categories.find((category) => category.category_id === categoryIdFromUrl),
    [categories, categoryIdFromUrl],
  );

  const selectedLessonIndex = useMemo(
    () => lessons.findIndex((lesson) => lesson.lesson_id === selectedLessonId),
    [lessons, selectedLessonId],
  );

  const pageNumbers = useMemo(
    () => lessons.map((_, index) => index + 1),
    [lessons],
  );

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

    const localLessons = fallbackLessons.filter(
      (lesson) => lesson.category_id === categoryIdFromUrl,
    );

    const loadLessons = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/lessons?category_id=${categoryIdFromUrl}`);
        if (!response.ok) {
          throw new Error();
        }

        const data = await response.json();
        const nextLessons = data.lessons.length > 0 ? data.lessons : localLessons;
        setLessons(nextLessons);
        setSelectedLessonId(nextLessons[0]?.lesson_id ?? null);
      } catch {
        setLessons(localLessons);
        setSelectedLessonId(localLessons[0]?.lesson_id ?? null);
      }
    };

    loadLessons();
  }, [categoryIdFromUrl]);

  useEffect(() => {
    if (!selectedLessonId) return;

    const localLesson = fallbackLessons.find((lesson) => lesson.lesson_id === selectedLessonId);

    const loadLessonDetail = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/lessons/${selectedLessonId}`);
        if (!response.ok) {
          throw new Error();
        }

        const data = await response.json();
        setLessonDetail(data);
      } catch {
        setLessonDetail(localLesson ?? null);
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
    setSelectedLessonId(lessons[nextIndex].lesson_id);
  };

  if (!categoryIdFromUrl) {
    return (
      <section className="learn-page learn-category-page">
        <h1 className="learn-category-title">카테고리</h1>

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
      </section>
    );
  }

  return (
    <section className="learn-page learn-study-page">
      <div className="learn-study-toolbar">
        <label htmlFor="learn-category-select">카테고리</label>
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
          {lessonDetail?.video_url ? (
            <video key={lessonDetail.video_url} controls>
              <source src={lessonDetail.video_url} />
            </video>
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
          <h1>{lessonDetail?.word ?? lessons[0]?.word ?? '동생'}</h1>
          <div className="learn-info-divider" />
          <strong>의미</strong>
          <span>{lessonDetail?.description ?? '단어의 의미'}</span>
        </article>
      </div>

      <div className="learn-study-footer">
        <button className="learn-step-button" type="button" onClick={() => goToLesson(selectedLessonIndex - 1)} disabled={selectedLessonIndex <= 0}>
          이전
        </button>

        <div className="learn-page-select" aria-label="페이지 선택">
          <strong>페이지 선택</strong>
          <div className="learn-page-numbers">
            {pageNumbers.map((pageNumber, index) => (
              <button
                className={index === selectedLessonIndex ? 'active' : ''}
                key={pageNumber}
                type="button"
                onClick={() => goToLesson(index)}
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

      <button className="learn-back-button" type="button" onClick={goBackToCategories}>
        뒤로가기
      </button>
    </section>
  );
}

export default Learn;
