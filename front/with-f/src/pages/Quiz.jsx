import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import './Quiz.css';

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

const fallbackQuizzes = fallbackCategories.flatMap((category) =>
  Array.from({ length: 5 }, (_, index) => ({
    quiz_id: category.category_id * 100 + index + 1,
    category_id: category.category_id,
    category_name: category.name,
    video_url: null,
    options: ['동생', '친구', '어머니', '아버지'].sort(() => Math.random() - 0.5),
    answer: '동생',
    description: '이 수어는 "동생"을 의미합니다. 손가락을 아래로 향하게 하여...',
    sort_order: index + 1,
  })),
);

function Quiz() {
  const [searchParams, setSearchParams] = useSearchParams();
  const categoryIdFromUrl = Number(searchParams.get('category_id')) || null;

  const [categories, setCategories] = useState(fallbackCategories);
  const [quizzes, setQuizzes] = useState([]);
  const [selectedQuizIndex, setSelectedQuizIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [isAnswerChecked, setIsAnswerChecked] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [isCorrect, setIsCorrect] = useState(false);

  const selectedCategory = useMemo(
    () => categories.find((category) => category.category_id === categoryIdFromUrl),
    [categories, categoryIdFromUrl],
  );

  const currentQuiz = useMemo(() => quizzes[selectedQuizIndex], [quizzes, selectedQuizIndex]);
  const pageNumbers = useMemo(() => quizzes.map((_, index) => index + 1), [quizzes]);

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/quiz/categories`);
        if (response.ok) {
          const data = await response.json();
          setCategories(data.length > 0 ? data : fallbackCategories);
        }
      } catch (err) {
        console.error("Failed to fetch categories", err);
      }
    };
    loadCategories();
  }, []);

  useEffect(() => {
    if (!categoryIdFromUrl) {
      setQuizzes([]);
      setSelectedQuizIndex(0);
      setSelectedOption(null);
      setIsAnswerChecked(false);
      return;
    }

    const loadQuizzes = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/quiz?category_id=${categoryIdFromUrl}`);
        if (response.ok) {
          const data = await response.json();
          setQuizzes(data.length > 0 ? data : fallbackQuizzes.filter(q => q.category_id === categoryIdFromUrl));
        } else {
          setQuizzes(fallbackQuizzes.filter(q => q.category_id === categoryIdFromUrl));
        }
      } catch (err) {
        setQuizzes(fallbackQuizzes.filter(q => q.category_id === categoryIdFromUrl));
      }
    };
    loadQuizzes();
    setSelectedQuizIndex(0);
    setSelectedOption(null);
    setIsAnswerChecked(false);
  }, [categoryIdFromUrl]);

  const selectCategory = (categoryId) => {
    setSearchParams({ category_id: String(categoryId) });
  };

  const goBackToCategories = () => {
    setSearchParams({});
  };

  const goToQuiz = (nextIndex) => {
    if (nextIndex < 0 || nextIndex >= quizzes.length) return;
    setSelectedQuizIndex(nextIndex);
    setSelectedOption(null);
    setIsAnswerChecked(false);
    setShowModal(false);
  };

  const handleOptionClick = (option) => {
    if (isAnswerChecked) return;
    setSelectedOption(option);
  };

  const handleCheckAnswer = async () => {
    if (selectedOption === null) return;
    
    const correct = selectedOption === currentQuiz.answer;
    setIsCorrect(correct);
    setIsAnswerChecked(true);
    setShowModal(true);

    // Backend sync (Requirement: POST /api/v1/quiz/results)
    try {
        await fetch(`${API_BASE_URL}/quiz/results`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                quiz_id: currentQuiz.quiz_id,
                selected_option: selectedOption,
                is_correct: correct
            })
        });
    } catch (err) {
        console.error("Failed to post result", err);
    }
  };

  const closeModal = () => {
    setShowModal(false);
  };

  if (!categoryIdFromUrl) {
    return (
      <section className="quiz-page quiz-category-page">
        <h1 className="quiz-category-title">퀴즈 카테고리</h1>
        <div className="quiz-category-grid">
          {categories.map((category) => (
            <button
              className="quiz-category-card"
              key={category.category_id}
              type="button"
              onClick={() => selectCategory(category.category_id)}
            >
              <span className={`quiz-category-icon ${category.icon}`} aria-hidden="true" />
              <strong>{category.name}</strong>
            </button>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="quiz-page quiz-study-page">
      <div className="quiz-study-toolbar">
        <div className="quiz-toolbar-left">
            <span className="quiz-current-category">현재 카테고리: <strong>{selectedCategory?.name}</strong></span>
        </div>
        <div className="quiz-toolbar-right">
            <label htmlFor="quiz-category-select">카테고리 변경</label>
            <select
              id="quiz-category-select"
              className="quiz-category-select"
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
      </div>

      <div className="quiz-study-main">
        <div className="quiz-video-card">
          {currentQuiz?.video_url ? (
            <video key={currentQuiz.video_url} controls>
              <source src={currentQuiz.video_url} />
            </video>
          ) : (
            <div className="quiz-video-placeholder">
              <span className="quiz-camera-symbol" aria-hidden="true" />
            </div>
          )}
        </div>

        <article className="quiz-options-card">
          <p>다음 수어가 의미하는 것은?</p>
          <div className="quiz-options-list">
            {currentQuiz?.options.map((option, index) => {
              let statusClass = '';
              if (isAnswerChecked) {
                if (option === currentQuiz.answer) statusClass = 'correct';
                else if (option === selectedOption) statusClass = 'incorrect';
              } else if (option === selectedOption) {
                statusClass = 'selected';
              }

              return (
                <button
                  key={index}
                  className={`quiz-option-button ${statusClass}`}
                  type="button"
                  onClick={() => handleOptionClick(option)}
                  disabled={isAnswerChecked}
                >
                  <span className="option-index">{index + 1}</span>
                  {option}
                </button>
              );
            })}
          </div>
        </article>
      </div>

      <div className="quiz-study-footer">
        <button className="quiz-step-button" type="button" onClick={() => goToQuiz(selectedQuizIndex - 1)} disabled={selectedQuizIndex <= 0}>
          이전
        </button>

        <div className="quiz-action-area">
            {!isAnswerChecked ? (
                <button className="quiz-check-button" type="button" onClick={handleCheckAnswer} disabled={selectedOption === null}>
                    정답 확인
                </button>
            ) : (
                <button className="quiz-next-button" type="button" onClick={() => goToQuiz(selectedQuizIndex + 1)} disabled={selectedQuizIndex >= quizzes.length - 1}>
                    다음 문제
                </button>
            )}
        </div>

        <button className="quiz-step-button" type="button" onClick={() => goToQuiz(selectedQuizIndex + 1)} disabled={selectedQuizIndex >= quizzes.length - 1}>
          다음
        </button>
      </div>

      <div className="quiz-progress-section">
          <strong>진행률</strong>
          <div className="quiz-page-numbers">
            {pageNumbers.map((pageNumber, index) => (
              <button
                className={index === selectedQuizIndex ? 'active' : ''}
                key={pageNumber}
                type="button"
                onClick={() => goToQuiz(index)}
              >
                {pageNumber}
              </button>
            ))}
          </div>
      </div>

      <button className="quiz-back-button" type="button" onClick={goBackToCategories}>
        뒤로가기
      </button>

      {showModal && (
        <div className="quiz-modal-overlay" onClick={closeModal}>
          <div className="quiz-modal-content" onClick={e => e.stopPropagation()}>
            <div className={`quiz-modal-header ${isCorrect ? 'correct' : 'incorrect'}`}>
                <span className="modal-result-icon">{isCorrect ? '✓' : '✗'}</span>
                <h2>{isCorrect ? '정답입니다!' : '틀렸습니다'}</h2>
            </div>
            <div className="quiz-modal-body">
                <p className="modal-word-label">단어: <strong>{currentQuiz.answer}</strong></p>
                <div className="modal-divider" />
                <p className="modal-description-label">설명</p>
                <p className="modal-description-text">{currentQuiz.description}</p>
            </div>
            <div className="quiz-modal-footer">
                <button className="quiz-modal-close" onClick={closeModal}>닫기</button>
                {selectedQuizIndex < quizzes.length - 1 && (
                    <button className="quiz-modal-next" onClick={() => goToQuiz(selectedQuizIndex + 1)}>다음 문제</button>
                )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default Quiz;