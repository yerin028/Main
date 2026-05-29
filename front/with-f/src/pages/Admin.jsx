// 관리자페이지
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Admin.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const adminUserIds = ["admin", "admin01", "manager", "user01"];
const userStorageKeys = ["user_id", "userId", "currentUserId", "loginUserId", "with-user-id"];

const getCurrentUserId = () => {
  for (const storageKey of userStorageKeys) {
    const savedUserId = localStorage.getItem(storageKey);

    if (savedUserId) {
      return savedUserId;
    }
  }

  return "";
};

const formatDate = (dateText) => {
  if (!dateText) {
    return "";
  }

  return new Date(dateText).toISOString().slice(0, 10).replaceAll("-", ".");
};

const formatDateTime = (dateText) => {
  if (!dateText) {
    return "";
  }

  const date = new Date(dateText);
  const datePart = date.toISOString().slice(0, 10).replaceAll("-", ".");
  const timePart = date.toTimeString().slice(0, 5);
  return `${datePart} ${timePart}`;
};

function Admin() {
  const navigate = useNavigate();
  const currentUserId = getCurrentUserId();
  const currentUserRole = localStorage.getItem("user_role");
  const isAdminUser = currentUserRole === "admin" || adminUserIds.includes(currentUserId);
  const [adminView, setAdminView] = useState("questions");
  const [questions, setQuestions] = useState([]);
  const [refundRequests, setRefundRequests] = useState([]);
  const [selectedQuestionId, setSelectedQuestionId] = useState(null);
  const [answerText, setAnswerText] = useState("");

  const selectedQuestion = useMemo(
    () => questions.find((question) => question.question_id === selectedQuestionId),
    [questions, selectedQuestionId],
  );

  const loadQuestions = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/cs/questions`);

      if (!response.ok) {
        throw new Error("질문 목록을 불러오지 못했습니다.");
      }

      const data = await response.json();
      setQuestions(data);
      setSelectedQuestionId((currentQuestionId) => currentQuestionId ?? data[0]?.question_id ?? null);
    } catch (error) {
      console.error(error);
      setQuestions([]);
      setSelectedQuestionId(null);
    }
  };

  const loadRefundRequests = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/refunds`);

      if (!response.ok) {
        throw new Error("환불 신청 목록을 불러오지 못했습니다.");
      }

      const data = await response.json();
      setRefundRequests(data);
    } catch (error) {
      console.error(error);
      setRefundRequests([]);
    }
  };

  useEffect(() => {
    if (isAdminUser) {
      loadQuestions();
      loadRefundRequests();
    }
  }, [isAdminUser]);

  const handleAnswerSubmit = async () => {
    if (!selectedQuestion) {
      alert("답변할 질문을 선택해주세요.");
      return;
    }

    if (!answerText.trim()) {
      alert("답변을 작성해주세요.");
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/cs/answers`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question_id: selectedQuestion.question_id,
          content: answerText.trim(),
          user_id: Number(currentUserId) || null,
        }),
      });

      if (!response.ok) {
        throw new Error("답변 등록에 실패했습니다.");
      }

      setAnswerText("");
      await loadQuestions();
    } catch (error) {
      alert(error.message);
    }
  };

  const handleRefundAction = async (action, refundRequest) => {
    const paymentText = refundRequest.toss_order_id || refundRequest.payment_id || "선택한 결제";
    const nextStatus = action === "승인" ? "승인됨" : "거절됨";

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/refunds`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          refund_id: refundRequest.refund_id,
          status: nextStatus,
        }),
      });

      if (!response.ok) {
        throw new Error("환불 상태 변경에 실패했습니다.");
      }

      await loadRefundRequests();
      alert(`${paymentText} 환불 신청을 ${action}했습니다.`);
    } catch (error) {
      alert(error.message);
    }
  };

  if (!isAdminUser) {
    return (
      <section className="admin-page">
        <div className="admin-access-panel">
          <h1>관리자 권한이 필요합니다.</h1>
          <p>관리자로 등록된 계정으로 로그인한 사용자만 관리자 페이지에 접근할 수 있습니다.</p>
          <button type="button" onClick={() => navigate("/login")}>
            로그인 페이지로 이동
          </button>
        </div>
      </section>
    );
  }

  if (adminView === "refunds") {
    return (
      <section className="admin-page">
        <h1 className="admin-page-title">관리자 페이지</h1>

        <button className="admin-mode-button" type="button" onClick={() => setAdminView("questions")}>
          <span className="admin-money-icon" aria-hidden="true">$</span>
          환불 관리
        </button>

        <div className="admin-refund-panel">
          <h2 className="admin-panel-title">환불 신청 목록</h2>
          <div className="admin-refund-table">
            <div className="admin-refund-row admin-table-header">
              <span>번호</span>
              <span>사용자</span>
              <span>결제ID</span>
              <span>환불사유</span>
              <span>신청일시</span>
              <span>상태</span>
              <span>관리</span>
            </div>

            {refundRequests.length === 0 ? (
              <div className="admin-empty-row">등록된 환불 신청이 없습니다.</div>
            ) : refundRequests.map((refundRequest) => (
              <div className="admin-refund-row" key={refundRequest.refund_id}>
                <span>{refundRequest.refund_id}</span>
                <span>{refundRequest.user_name || refundRequest.user_email || refundRequest.user_id || "-"}</span>
                <span>{refundRequest.toss_order_id || refundRequest.payment_id || "-"}</span>
                <span>{refundRequest.reason || "-"}</span>
                <span>{formatDateTime(refundRequest.request_at)}</span>
                <span>
                  <span className="admin-status-badge">{refundRequest.status}</span>
                </span>
                <span className="admin-action-buttons">
                  <button
                    type="button"
                    disabled={refundRequest.status !== "신청"}
                    onClick={() => handleRefundAction("승인", refundRequest)}
                  >
                    승인
                  </button>
                  <button
                    type="button"
                    disabled={refundRequest.status !== "신청"}
                    onClick={() => handleRefundAction("거절", refundRequest)}
                  >
                    거절
                  </button>
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="admin-page">
      <button className="admin-mode-button" type="button" onClick={() => setAdminView("refunds")}>
        <span className="admin-user-icon" aria-hidden="true" />
        관리자 모드
      </button>

      <div className="admin-question-layout">
        <div className="admin-question-panel">
          <h2 className="admin-panel-title">질문 목록</h2>

          <div className="admin-question-table">
            <div className="admin-question-row admin-table-header">
              <span>번호</span>
              <span>제목</span>
              <span>작성자</span>
              <span>작성일</span>
              <span>답변 상태</span>
            </div>

            {questions.length === 0 ? (
              <div className="admin-empty-row">등록된 질문이 없습니다.</div>
            ) : (
              questions.map((question, index) => (
                <button
                  className={`admin-question-row ${
                    question.question_id === selectedQuestionId ? "admin-question-row-selected" : ""
                  }`}
                  key={question.question_id}
                  type="button"
                  onClick={() => setSelectedQuestionId(question.question_id)}
                >
                  <span>{index + 1}</span>
                  <span>{question.content}</span>
                  <span>{question.user_name || question.user_email || question.user_id || "-"}</span>
                  <span>{formatDate(question.created_at)}</span>
                  <span>
                    <span className="admin-status-badge">{question.answer_status}</span>
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="admin-detail-panel">
          <h2 className="admin-panel-title">질문 상세</h2>

          {selectedQuestion ? (
            <>
              <h3 className="admin-detail-title">질문</h3>
              <div className="admin-question-content">
                {selectedQuestion.content.split("\n").map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>

              <div className="admin-question-meta">
                <span>작성자</span>
                <strong>{selectedQuestion.user_name || selectedQuestion.user_email || selectedQuestion.user_id || "-"}</strong>
                <span className="admin-meta-divider" />
                <span>작성일</span>
                <strong>{formatDate(selectedQuestion.created_at)}</strong>
                <span className="admin-meta-divider" />
                <span>답변 상태</span>
                <span className="admin-status-badge">{selectedQuestion.answer_status}</span>
              </div>

              <div className="admin-answer-area">
                <h3 className="admin-detail-title">답변</h3>
                <textarea
                  className="admin-answer-input"
                  value={answerText}
                  placeholder="답변을 작성해주세요"
                  onChange={(event) => setAnswerText(event.target.value)}
                />
                <button className="admin-answer-button" type="button" onClick={handleAnswerSubmit}>
                  답변하기
                </button>
              </div>
            </>
          ) : (
            <div className="admin-empty-detail">선택된 질문이 없습니다.</div>
          )}
        </div>
      </div>
    </section>
  );
}

export default Admin;

