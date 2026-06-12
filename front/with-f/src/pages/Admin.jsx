import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Admin.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const userStorageKeys = ["user_id", "userId", "currentUserId", "loginUserId", "with-user-id"];
const pageSize = 5;

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
  if (!dateText) return "-";

  return new Date(dateText).toISOString().slice(0, 10).replaceAll("-", ".");
};

const formatDateTime = (dateText) => {
  if (!dateText) return "-";

  const date = new Date(dateText);
  const datePart = date.toISOString().slice(0, 10).replaceAll("-", ".");
  const timePart = date.toTimeString().slice(0, 5);
  return `${datePart} ${timePart}`;
};

const getWriterName = (item) => {
  if (item?.user_name && !item.user_name.includes("*")) {
    return item.user_name;
  }

  if (item?.user_email) {
    return item.user_email.split("@")[0];
  }

  return item?.user_name || (item?.user_id ? `ID ${item.user_id}` : "-");
};

const getQuestionTitle = (question) => {
  const content = question?.content || "";
  const firstLine = content.split("\n").find((line) => line.trim());
  return firstLine || "제목 없음";
};

const hasAnswer = (question) => {
  return Array.isArray(question?.answers) && question.answers.length > 0;
};

const getAnswerStatusText = (question) => {
  return hasAnswer(question) ? "답변 완료" : "답변 대기";
};

const getAnswerStatusClassName = (question) => {
  return `admin-status-badge ${hasAnswer(question) ? "admin-status-badge-complete" : ""}`;
};

function Admin() {
  const navigate = useNavigate();
  const currentUserId = getCurrentUserId();
  const isAdminUser = true;
  const [adminView, setAdminView] = useState("questions");
  const [questions, setQuestions] = useState([]);
  const [refundRequests, setRefundRequests] = useState([]);
  const [selectedQuestionId, setSelectedQuestionId] = useState(null);
  const [answerText, setAnswerText] = useState("");
  const [searchText, setSearchText] = useState("");
  const [questionFilter, setQuestionFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);

  const selectedQuestion = useMemo(
    () => questions.find((question) => question.question_id === selectedQuestionId),
    [questions, selectedQuestionId],
  );

  const selectedAnswer = selectedQuestion?.answers?.[selectedQuestion.answers.length - 1] || null;
  const selectedQuestionAnswered = hasAnswer(selectedQuestion);

  const filteredQuestions = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();

    return questions.filter((question) => {
      if (questionFilter === "pending" && hasAnswer(question)) {
        return false;
      }

      if (questionFilter === "complete" && !hasAnswer(question)) {
        return false;
      }

      if (!keyword) {
        return true;
      }

      const searchableText = [
        getQuestionTitle(question),
        question.content,
        getWriterName(question),
        formatDate(question.created_at),
        getAnswerStatusText(question),
      ]
        .join(" ")
        .toLowerCase();

      return searchableText.includes(keyword);
    });
  }, [questions, questionFilter, searchText]);

  const totalPages = Math.max(1, Math.ceil(filteredQuestions.length / pageSize));
  const visibleQuestions = filteredQuestions.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const completeCount = questions.filter((question) => hasAnswer(question)).length;
  const pendingCount = Math.max(0, questions.length - completeCount);

  const loadQuestions = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/cs/questions`);

      if (!response.ok) {
        throw new Error("질문 목록을 불러오지 못했습니다.");
      }

      const data = await response.json();
      setQuestions(data);
      setSelectedQuestionId((currentQuestionId) => {
        if (data.some((question) => question.question_id === currentQuestionId)) {
          return currentQuestionId;
        }

        return data[0]?.question_id ?? null;
      });
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
        throw new Error("환불 요청 목록을 불러오지 못했습니다.");
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

  useEffect(() => {
    setCurrentPage(1);
  }, [questionFilter, searchText]);

  useEffect(() => {
    if (filteredQuestions.length === 0) {
      setSelectedQuestionId(null);
      return;
    }

    setSelectedQuestionId((currentQuestionId) => {
      if (filteredQuestions.some((question) => question.question_id === currentQuestionId)) {
        return currentQuestionId;
      }

      return filteredQuestions[0].question_id;
    });
  }, [filteredQuestions]);

  const handleAnswerSubmit = async () => {
    if (!selectedQuestion) {
      alert("답변할 문의를 선택해주세요.");
      return;
    }

    if (selectedQuestionAnswered) {
      alert("이미 답변이 완료된 문의입니다.");
      return;
    }

    if (!answerText.trim()) {
      alert("답변 내용을 입력해주세요.");
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
      alert(`${paymentText} 환불 요청을 ${action}했습니다.`);
    } catch (error) {
      alert(error.message);
    }
  };

  if (!isAdminUser) {
    return (
      <section className="admin-page">
        <div className="admin-access-panel">
          <h1>관리자 권한이 필요합니다</h1>
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
        <main className="admin-main">
          <div className="admin-title-row">
            <div>
              <h1>환불 관리</h1>
              <p>고객의 실제 환불 요청을 확인하고 상태를 처리합니다.</p>
            </div>
            <button className="admin-outline-action" type="button" onClick={() => setAdminView("questions")}>
              문의 관리
            </button>
          </div>

          <div className="admin-refund-panel">
            <h2 className="admin-panel-title">환불 요청 목록</h2>
            <div className="admin-refund-table">
              <div className="admin-refund-row admin-table-header">
                <span>번호</span>
                <span>사용자</span>
                <span>결제 ID</span>
                <span>환불 사유</span>
                <span>요청 일시</span>
                <span>상태</span>
                <span>관리</span>
              </div>

              {refundRequests.length === 0 ? (
                <div className="admin-empty-row">등록된 환불 요청이 없습니다.</div>
              ) : (
                refundRequests.map((refundRequest) => (
                  <div className="admin-refund-row" key={refundRequest.refund_id}>
                    <span>{refundRequest.refund_id}</span>
                    <span>{getWriterName(refundRequest)}</span>
                    <span>{refundRequest.toss_order_id || refundRequest.payment_id || "-"}</span>
                    <span>{refundRequest.reason || "-"}</span>
                    <span>{formatDateTime(refundRequest.request_at)}</span>
                    <span>
                      <span className="admin-status-badge">{refundRequest.status || "요청"}</span>
                    </span>
                    <span className="admin-action-buttons">
                      <button
                        type="button"
                        disabled={refundRequest.status !== "요청"}
                        onClick={() => handleRefundAction("승인", refundRequest)}
                      >
                        승인
                      </button>
                      <button
                        type="button"
                        disabled={refundRequest.status !== "요청"}
                        onClick={() => handleRefundAction("거절", refundRequest)}
                      >
                        거절
                      </button>
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </main>
      </section>
    );
  }

  return (
    <section className="admin-page">
      <main className="admin-main">
        <div className="admin-title-row">
          <div>
            <h1>서비스 관리</h1>
            <p>고객센터에 등록된 실제 문의를 확인하고 답변을 처리합니다.</p>
          </div>
          <button className="admin-outline-action" type="button" onClick={() => setAdminView("refunds")}>
            <span className="admin-action-icon" aria-hidden="true">
              $
            </span>
            환불 관리
          </button>
        </div>

        <div className="admin-summary-grid">
          <button
            className={`admin-summary-card ${questionFilter === "all" ? "admin-summary-card-active" : ""}`}
            type="button"
            onClick={() => setQuestionFilter("all")}
          >
            <span className="admin-summary-icon admin-summary-icon-blue" aria-hidden="true">
              ☺
            </span>
            <div>
              <span>전체 문의</span>
              <strong>{questions.length}</strong>
            </div>
          </button>
          <button
            className={`admin-summary-card ${questionFilter === "pending" ? "admin-summary-card-active" : ""}`}
            type="button"
            onClick={() => setQuestionFilter("pending")}
          >
            <span className="admin-summary-icon admin-summary-icon-orange" aria-hidden="true">
              ◷
            </span>
            <div>
              <span>답변 대기</span>
              <strong>{pendingCount}</strong>
            </div>
          </button>
          <button
            className={`admin-summary-card ${questionFilter === "complete" ? "admin-summary-card-active" : ""}`}
            type="button"
            onClick={() => setQuestionFilter("complete")}
          >
            <span className="admin-summary-icon admin-summary-icon-green" aria-hidden="true">
              ✓
            </span>
            <div>
              <span>답변 완료</span>
              <strong>{completeCount}</strong>
            </div>
          </button>
        </div>

        <div className="admin-question-layout">
          <div className="admin-question-panel">
            <div className="admin-panel-header">
              <h2 className="admin-panel-title">문의 목록</h2>
              <label className="admin-search-box">
                <span aria-hidden="true">⌕</span>
                <input
                  value={searchText}
                  placeholder="제목 또는 작성자 검색"
                  onChange={(event) => setSearchText(event.target.value)}
                />
              </label>
            </div>

            <div className="admin-question-table">
              <div className="admin-question-row admin-table-header">
                <span>번호</span>
                <span>제목</span>
                <span>작성자 / 작성일</span>
                <span>상태</span>
              </div>

              {visibleQuestions.length === 0 ? (
                <div className="admin-empty-row">등록된 문의가 없습니다.</div>
              ) : (
                visibleQuestions.map((question, index) => (
                  <button
                    className={`admin-question-row ${
                      question.question_id === selectedQuestionId ? "admin-question-row-selected" : ""
                    }`}
                    key={question.question_id}
                    type="button"
                    onClick={() => setSelectedQuestionId(question.question_id)}
                  >
                    <span>{(currentPage - 1) * pageSize + index + 1}</span>
                    <span>{getQuestionTitle(question)}</span>
                    <span>
                      <strong>{getWriterName(question)}</strong>
                      <small>{formatDate(question.created_at)}</small>
                    </span>
                    <span>
                      <span className={getAnswerStatusClassName(question)}>{getAnswerStatusText(question)}</span>
                    </span>
                  </button>
                ))
              )}
            </div>

            <div className="admin-pagination" aria-label="문의 페이지">
              <button
                type="button"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              >
                ‹
              </button>
              {Array.from({ length: totalPages }, (_, index) => (
                <button
                  className={currentPage === index + 1 ? "admin-page-number-active" : ""}
                  key={index + 1}
                  type="button"
                  onClick={() => setCurrentPage(index + 1)}
                >
                  {index + 1}
                </button>
              ))}
              <button
                type="button"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              >
                ›
              </button>
            </div>
          </div>

          <div className="admin-detail-panel">
            <h2 className="admin-panel-title">문의 상세</h2>

            {selectedQuestion ? (
              <>
                <h3 className="admin-detail-question-title">{getQuestionTitle(selectedQuestion)}</h3>

                <div className="admin-question-meta">
                  <span>작성자</span>
                  <strong>{getWriterName(selectedQuestion)}</strong>
                  <span>작성일</span>
                  <strong>{formatDate(selectedQuestion.created_at)}</strong>
                  <span>상태</span>
                  <span className={getAnswerStatusClassName(selectedQuestion)}>
                    {getAnswerStatusText(selectedQuestion)}
                  </span>
                </div>

                <div className="admin-detail-block">
                  <h3 className="admin-detail-title">문의 내용</h3>
                  <div className="admin-question-content">
                    {selectedQuestion.content.split("\n").map((line, index) => (
                      <p key={`${line}-${index}`}>{line}</p>
                    ))}
                  </div>
                </div>

                {selectedAnswer && (
                  <div className="admin-detail-block">
                    <h3 className="admin-detail-title">등록된 답변</h3>
                    <div className="admin-question-content admin-answer-preview">
                      {selectedAnswer.content.split("\n").map((line, index) => (
                        <p key={`${line}-${index}`}>{line}</p>
                      ))}
                    </div>
                  </div>
                )}

                {!selectedQuestionAnswered && (
                  <div className="admin-answer-area">
                    <h3 className="admin-detail-title">답변 작성</h3>
                    <textarea
                      className="admin-answer-input"
                      value={answerText}
                      placeholder="답변 내용을 입력해주세요"
                      onChange={(event) => setAnswerText(event.target.value)}
                    />
                    <button className="admin-answer-button" type="button" onClick={handleAnswerSubmit}>
                      답변 등록
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="admin-empty-detail">선택된 문의가 없습니다.</div>
            )}
          </div>
        </div>
      </main>
    </section>
  );
}

export default Admin;
