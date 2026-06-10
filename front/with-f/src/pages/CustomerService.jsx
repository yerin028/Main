import { useEffect, useState } from "react";
import "./CustomerService.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const refundReasons = ["단순 변심", "서비스 불만족", "다른 서비스 구독"];

const formatDate = (dateText) => {
  if (!dateText) return "";

  return new Date(dateText).toISOString().slice(0, 10).replaceAll("-", ".");
};

const getCurrentUserId = () => {
  const userId = Number(localStorage.getItem("user_id"));
  return Number.isNaN(userId) ? null : userId;
};

function CustomerService() {
  const [questionText, setQuestionText] = useState("");
  const [questions, setQuestions] = useState([]);
  const [isRefundModalOpen, setIsRefundModalOpen] = useState(false);
  const [selectedRefundReason, setSelectedRefundReason] = useState("");

  const loadQuestions = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/cs/questions`);
      if (!response.ok) throw new Error("질문 목록을 불러오지 못했습니다.");

      const data = await response.json();
      setQuestions(data);
    } catch (error) {
      console.error(error);
      setQuestions([]);
    }
  };

  useEffect(() => {
    loadQuestions();
  }, []);

  const handleSubmitQuestion = async () => {
    const trimmedQuestion = questionText.trim();

    if (!trimmedQuestion) {
      alert("질문을 작성해주세요.");
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/cs/questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: trimmedQuestion,
          user_id: getCurrentUserId(),
        }),
      });

      if (!response.ok) throw new Error("질문 작성에 실패했습니다.");

      setQuestionText("");
      await loadQuestions();
    } catch (error) {
      alert(error.message);
    }
  };

  const openRefundModal = () => {
    setSelectedRefundReason("");
    setIsRefundModalOpen(true);
  };

  const closeRefundModal = () => {
    setIsRefundModalOpen(false);
  };

  const handleRefundSubmit = async () => {
    if (!selectedRefundReason) {
      alert("환불 사유를 선택해주세요.");
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/refunds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: selectedRefundReason,
          user_id: getCurrentUserId(),
        }),
      });

      if (!response.ok) throw new Error("환불 신청에 실패했습니다.");

      alert("환불 신청이 접수되었습니다.");
      closeRefundModal();
    } catch (error) {
      alert(error.message);
    }
  };

  const handleWithdrawClick = async () => {
  const confirmed = window.confirm("정말 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다.");
  if (!confirmed) return;

  const userId = getCurrentUserId();
  if (!userId) {
    alert("로그인 정보가 없습니다.");
    return;
  }

  try {
    const response = await fetch(
      `${apiBaseUrl}/api/v1/cs/withdraw?user_id=${userId}`,
      { method: "POST" }
    );
    if (!response.ok) throw new Error("탈퇴 처리에 실패했습니다.");

    alert("탈퇴가 완료되었습니다.");
    localStorage.clear();
    window.location.href = "/";
  } catch (error) {
    alert(error.message);
  }
};

  return (
    <section className="customer-service-page" aria-label="고객센터">
      <div className="customer-question-section">
        <h2 className="customer-section-title">질문 작성</h2>

        <div className="customer-question-form">
          <textarea
            className="customer-question-input"
            value={questionText}
            placeholder="질문을 작성해주세요"
            onChange={(event) => setQuestionText(event.target.value)}
          />

          <button
            className="customer-primary-button customer-submit-button"
            type="button"
            onClick={handleSubmitQuestion}
          >
            작성 완료
          </button>
        </div>
      </div>

      <div className="customer-list-section">
        <h2 className="customer-section-title">내 질문 목록</h2>

        <div className="customer-question-table">
          <div className="customer-table-row customer-table-header">
            <span>번호</span>
            <span>질문</span>
            <span>작성일</span>
            <span>답변 상태</span>
          </div>

          {questions.length === 0 ? (
            <div className="customer-empty-row">작성한 질문이 없습니다.</div>
          ) : (
            questions.map((question, index) => (
              <div className="customer-table-row" key={question.question_id}>
                <span>{index + 1}</span>
                <span>{question.content}</span>
                <span>{formatDate(question.created_at)}</span>
                <span>
                  <span className="customer-status-badge">{question.answer_status}</span>
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="customer-bottom-actions">
        <button
          className="customer-primary-button customer-refund-button"
          type="button"
          onClick={openRefundModal}
        >
          환불하기
        </button>

        <button
          className="customer-secondary-button customer-withdraw-button"
          type="button"
          onClick={handleWithdrawClick}
        >
          탈퇴하기
        </button>
      </div>

      {isRefundModalOpen && (
        <div className="customer-modal-backdrop" role="presentation">
          <div className="customer-refund-modal" role="dialog" aria-modal="true" aria-labelledby="refund-modal-title">
            <div className="customer-modal-header">
              <h2 id="refund-modal-title">환불 사유</h2>
              <button className="customer-modal-close" type="button" aria-label="닫기" onClick={closeRefundModal}>
                ×
              </button>
            </div>

            <div className="customer-refund-options">
              {refundReasons.map((refundReason) => (
                <label className="customer-refund-option" key={refundReason}>
                  <input
                    type="checkbox"
                    checked={selectedRefundReason === refundReason}
                    onChange={() => setSelectedRefundReason(refundReason)}
                  />
                  <span className="customer-checkbox" aria-hidden="true" />
                  <span>{refundReason}</span>
                </label>
              ))}
            </div>

            <div className="customer-modal-actions">
              <button className="customer-secondary-button" type="button" onClick={closeRefundModal}>
                취소
              </button>
              <button className="customer-primary-button customer-modal-submit" type="button" onClick={handleRefundSubmit}>
                환불하기
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default CustomerService;
