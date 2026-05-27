import { useState } from "react";
import Admin from "./Admin";
import "./CustomerService.css";

const refundReasons = ["단순 변심", "서비스 불만족", "다른 서비스 구독"];
const adminUserIds = ["admin", "admin01", "manager", "user01"];

const getCurrentUserId = () => {
  const storageKeys = [
    "user_id",
    "userId",
    "currentUserId",
    "loginUserId",
    "with-user-id",
  ];

  for (const storageKey of storageKeys) {
    const savedUserId = localStorage.getItem(storageKey);

    if (savedUserId) {
      return savedUserId;
    }
  }

  return "";
};

function CustomerService() {
  const currentUserId = getCurrentUserId();
  const isAdminUser = adminUserIds.includes(currentUserId);

  const [questionText, setQuestionText] = useState("");
  const [questions, setQuestions] = useState([]);
  const [isRefundModalOpen, setIsRefundModalOpen] = useState(false);
  const [selectedRefundReason, setSelectedRefundReason] = useState("");

  const handleSubmitQuestion = () => {
    const trimmedQuestion = questionText.trim();

    if (!trimmedQuestion) {
      alert("질문을 작성해주세요.");
      return;
    }

    const today = new Date();
    const createdAt = [
      today.getFullYear(),
      String(today.getMonth() + 1).padStart(2, "0"),
      String(today.getDate()).padStart(2, "0"),
    ].join(".");

    setQuestions((currentQuestions) => [
      {
        id: currentQuestions.length + 1,
        title: trimmedQuestion,
        createdAt,
        status: "답변 대기",
      },
      ...currentQuestions,
    ]);
    setQuestionText("");
  };

  const openRefundModal = () => {
    setSelectedRefundReason("");
    setIsRefundModalOpen(true);
  };

  const closeRefundModal = () => {
    setIsRefundModalOpen(false);
  };

  const handleRefundSubmit = () => {
    if (!selectedRefundReason) {
      alert("환불 사유를 선택해주세요.");
      return;
    }

    alert("환불 신청이 접수되었습니다.");
    closeRefundModal();
  };

  if (isAdminUser) {
    return <Admin />;
  }

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
            <span>제목</span>
            <span>작성일</span>
            <span>답변 상태</span>
          </div>

          {questions.length === 0 ? (
            <div className="customer-empty-row">작성한 질문이 없습니다.</div>
          ) : (
            questions.map((question) => (
              <div className="customer-table-row" key={question.id}>
                <span>{question.id}</span>
                <span>{question.title}</span>
                <span>{question.createdAt}</span>
                <span>
                  <span className="customer-status-badge">{question.status}</span>
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      <button
        className="customer-primary-button customer-refund-button"
        type="button"
        onClick={openRefundModal}
      >
        환불하기
      </button>

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
