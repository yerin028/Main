import { useEffect, useState } from "react";
import "./CustomerService.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const refundReasons = ["단순 변심", "서비스 불만족", "다른 서비스 구독"];
const PAGE_SIZE = 5;

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
  const [charCount, setCharCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [paymentInfo, setPaymentInfo] = useState(null);

  const loadQuestions = async () => {
    const userId = getCurrentUserId();
    try {
      const url = userId
        ? `${apiBaseUrl}/api/v1/cs/questions?user_id=${userId}`
        : `${apiBaseUrl}/api/v1/cs/questions`;
      const response = await fetch(url);
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
    loadPaymentInfo();
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
      setCharCount(0);
      setCurrentPage(1);
      await loadQuestions();
    } catch (error) {
      alert(error.message);
    }
  };

  const openRefundModal = () => {
    if (!paymentInfo) {
        alert("무료 회원이십니다. 환불할 결제 내역이 없습니다.");
        return;
    }
    setSelectedRefundReason("");
    setIsRefundModalOpen(true);
  };

  const closeRefundModal = () => setIsRefundModalOpen(false);

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
          payment_id: paymentInfo?.payment_id,
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

  // 페이지네이션
  const totalPages = Math.ceil(questions.length / PAGE_SIZE);
  const pagedQuestions = questions.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  // 홈 화면에 결제정보
  const loadPaymentInfo = async () => {
    const userId = getCurrentUserId();
    if (!userId) return;
    try {
        const response = await fetch(`${apiBaseUrl}/api/v1/payment?user_id=${userId}`);
        if (!response.ok) return;
        const data = await response.json();
        const latest = data.find(p => p.payment_status === "DONE");
        setPaymentInfo(latest || null);
    } catch {
        setPaymentInfo(null);
    }
  };
  loadPaymentInfo();

  return (
    <section className="customer-service-page" aria-label="고객센터">

      {/* 헤더 */}
      <div className="customer-header">
        <h1 className="customer-page-title">고객센터</h1>
        <p className="customer-page-subtitle">문의사항을 남겨주시면 빠르게 답변드리겠습니다.</p>
      </div>

      {/* 문의하기 */}
      <div className="customer-question-section">
        <div className="customer-question-card">
          <h2 className="customer-section-title">문의하기</h2>
          <p className="customer-section-desc">궁금한 내용을 남겨주세요.</p>
          <textarea
            className="customer-question-input"
            value={questionText}
            placeholder="문의 내용을 입력해주세요."
            maxLength={1000}
            onChange={(e) => {
              setQuestionText(e.target.value);
              setCharCount(e.target.value.length);
            }}
          />
          <div className="customer-question-footer">
            <span className="customer-char-count">{charCount} / 1,000</span>
            <button className="customer-submit-button" type="button" onClick={handleSubmitQuestion}>
              문의 등록
            </button>
          </div>
        </div>
      </div>

      {/* 내 문의 내역 */}
      <div className="customer-list-section">
        <h2 className="customer-section-title">내 문의 내역</h2>
        <div className="customer-question-table">
          {questions.length === 0 ? (
            <div className="customer-empty-row">작성한 질문이 없습니다.</div>
          ) : (
            pagedQuestions.map((question, index) => (
              <div
                className="customer-table-row"
                key={question.question_id}
                onClick={() => setSelectedQuestion(question)}
              >
                <span className="customer-row-num">
                  {questions.length - ((currentPage - 1) * PAGE_SIZE + index)}
                </span>
                <div className="customer-row-content">
                  <span className="customer-row-title">{question.content}</span>
                  <span className="customer-row-date">{formatDate(question.created_at)}</span>
                </div>
                <span className={`customer-status-badge ${question.answer_status === "답변 완료" ? "answered" : ""}`}>
                  ● {question.answer_status}
                </span>
                <span className="customer-row-arrow">›</span>
              </div>
            ))
          )}
        </div>

        {/* 페이지네이션 */}
        {totalPages > 1 && (
          <div className="customer-pagination">
            <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>{"<"}</button>
            <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>{"<<"}</button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                className={currentPage === page ? "active" : ""}
                onClick={() => setCurrentPage(page)}
              >
                {page}
              </button>
            ))}
            <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>{">>"}</button>
            <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>{">"}</button>
          </div>
        )}
      </div>

      {/* 하단 버튼 */}
      <div className="customer-bottom-actions">
        <button className="customer-action-button" type="button" onClick={openRefundModal}>
          <span className="customer-action-icon">↺</span>
          환불 신청
        </button>
        <button className="customer-action-button" type="button" onClick={handleWithdrawClick}>
          <span className="customer-action-icon">👤</span>
          회원 탈퇴
        </button>
      </div>

      {/* 질문 상세 모달 */}
      {selectedQuestion && (
        <div className="customer-modal-backdrop" role="presentation" onClick={() => setSelectedQuestion(null)}>
          <div className="customer-detail-modal" role="dialog" onClick={(e) => e.stopPropagation()}>
            <div className="customer-modal-header">
              <h2>문의 상세</h2>
              <button className="customer-modal-close" type="button" onClick={() => setSelectedQuestion(null)}>×</button>
            </div>

            <div className="customer-detail-section">
              <div className="customer-detail-label">질문</div>
              <div className="customer-detail-content">{selectedQuestion.content}</div>
              <div className="customer-detail-date">{formatDate(selectedQuestion.created_at)}</div>
            </div>

            <div className="customer-detail-divider" />

            <div className="customer-detail-section">
              <div className="customer-detail-label">답변</div>
              {selectedQuestion.answers && selectedQuestion.answers.length > 0 ? (
                selectedQuestion.answers.map((answer) => (
                  <div key={answer.answer_id}>
                    <div className="customer-detail-content">{answer.content}</div>
                    <div className="customer-detail-date">{formatDate(answer.created_at)}</div>
                  </div>
                ))
              ) : (
                <div className="customer-detail-empty">아직 답변이 없습니다.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 환불 모달 */}
      {isRefundModalOpen && (
        <div className="customer-modal-backdrop" role="presentation">
          <div className="customer-refund-modal" role="dialog" aria-modal="true" aria-labelledby="refund-modal-title">
            <div className="customer-modal-header">
              <h2 id="refund-modal-title">환불 사유</h2>
              <button className="customer-modal-close" type="button" aria-label="닫기" onClick={closeRefundModal}>×</button>
            </div>
            <p className="customer-modal-description">환불 사유를 선택해주세요.</p>
            <div className="customer-refund-options">
              {refundReasons.map((refundReason) => (
                <label className="customer-refund-option" key={refundReason}>
                  <input
                    type="radio"
                    name="refundReason"
                    checked={selectedRefundReason === refundReason}
                    onChange={() => setSelectedRefundReason(refundReason)}
                  />
                  <span className="customer-radio" aria-hidden="true" />
                  <span>{refundReason}</span>
                </label>
              ))}
            </div>
            <div className="customer-modal-actions">
              <button className="customer-secondary-button" type="button" onClick={closeRefundModal}>취소</button>
              <button className="customer-primary-button customer-modal-submit" type="button" onClick={handleRefundSubmit}>환불하기</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default CustomerService;