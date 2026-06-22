import { useEffect, useMemo, useRef, useState } from "react";
import "./Payment.css";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const tossClientKey = import.meta.env.VITE_TOSS_CLIENT_KEY;
const tossSdkUrl = "https://js.tosspayments.com/v2/standard";

const paymentPlans = [
  {
    id: "free",
    title: "무료",
    price: "0",
    amount: 0,
    periodMonth: 1,
    isDefault: false,
    isSelectable: false,
    features: ["수어 학습", "수어 통역 서비스"],
  },
  {
    id: "standard",
    title: "스탠다드",
    price: "4,900",
    amount: 4900,
    periodMonth: 1,
    isDefault: true,
    isSelectable: true,
    features: ["수어 학습", "수어 퀴즈", "수어 통역 서비스"],
  },
  {
    id: "special-three-month",
    title: "스탠다드\n3개월 구독 시",
    price: "9,900",
    amount: 9900,
    periodMonth: 3,
    isDefault: false,
    isSelectable: true,
    features: ["수어 학습", "수어 퀴즈", "수어 통역 서비스"],
  },
];

const paymentFeatures = ["수어 학습", "수어 퀴즈", "수어 통역 서비스"];

// 추가 - 플랜 이름 변환 함수
function getPlanName(amount) {
  if (amount === 4900)
    return "스탠다드";
  if (amount === 9900)
    return "스탠다드 3개월";
  return "이용권";
}

function loadTossPaymentSdk() {
  if (window.TossPayments) {
    return Promise.resolve(window.TossPayments);
  }

  return new Promise((resolve, reject) => {
    const existingScript = document.querySelector(`script[src="${tossSdkUrl}"]`);

    if (existingScript) {
      existingScript.addEventListener("load", () => resolve(window.TossPayments));
      existingScript.addEventListener("error", reject);
      return;
    }

    const script = document.createElement("script");
    script.src = tossSdkUrl;
    script.async = true;
    script.onload = () => resolve(window.TossPayments);
    script.onerror = reject;
    document.body.appendChild(script);
  });
}

function getCustomerKey() {
  const savedCustomerKey = localStorage.getItem("with-payment-customer-key");

  if (savedCustomerKey) {
    return savedCustomerKey;
  }

  const customerKey = `customer_${crypto.randomUUID().replaceAll("-", "")}`.slice(0, 50);
  localStorage.setItem("with-payment-customer-key", customerKey);
  return customerKey;
}

function createOrderId() {
  return `order_${crypto.randomUUID().replaceAll("-", "")}`;
}

function Payment() {
  const defaultPlan = paymentPlans.find((paymentPlan) => paymentPlan.isDefault);
  const [selectedPlanId, setSelectedPlanId] = useState(defaultPlan.id);
  const [isPaying, setIsPaying] = useState(false);
  const hasConfirmedRef = useRef(false);
  //추가
  const [currentPayment, setCurrentPayment] = useState(null); // 현재 구독 정보
  const [userInfo, setUserInfo] = useState(null); // 유저 정보
  const [isChangingPlan, setIsChangingPlan] = useState(false); // 플랜 변경 모드

  const selectedPlan = useMemo(
    () => paymentPlans.find((paymentPlan) => paymentPlan.id === selectedPlanId),
    [selectedPlanId],
  );

  // 추가
  useEffect(() => {
    const userId = Number(localStorage.getItem("user_id"));
    if (!userId)
      return;

    const loadCurrentPayment = async () => {
      try {
        const response = await fetch (`${apiBaseUrl}/api/v1/payment?user_id=${userId}`);
        if (!response.ok)
          return;
        const data = await response.json();
        const latest = data.find((p) => p.payment_status === "DONE");
        setCurrentPayment(latest || null) ;
      } catch {
        setCurrentPayment(null);
      }
    };

    const loadUserInfo = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/auth/me?user_id=${userId}`);
        if (!response.ok)
          return;
        const data = await response.json();
        setUserInfo(data);
      } catch {
        setUserInfo(null);
      }
    };

    loadCurrentPayment();
    loadUserInfo();
  }, []);
  //여기까지

  // 추가: 플랜 변경 모드일 때 현재 구독 중인 플랜과 동일한 플랜이 선택되지 않도록 기본 선택값을 다른 선택 가능한 플랜으로 자동 변경
  useEffect(() => {
    if (isChangingPlan && currentPayment) {
      const otherPlan = paymentPlans.find(
        (p) => p.isSelectable && p.amount !== currentPayment.amount
      );
      if (otherPlan) {
        setSelectedPlanId(otherPlan.id);
      }
    }
  }, [isChangingPlan, currentPayment]);

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const result = searchParams.get("result");
    const paymentKey = searchParams.get("paymentKey");
    const orderId = searchParams.get("orderId");
    const amount = Number(searchParams.get("amount"));

    if (result === "fail") {
      const message = searchParams.get("message") || "결제가 취소되었거나 실패했습니다.";
      alert(message);
      window.history.replaceState(null, "", window.location.pathname);
      return;
    }

    // 정기 결제 (빌링) 성공 리다이렉트 처리
    const authKey = searchParams.get("authKey");
    const customerKey = searchParams.get("customerKey");

    if (result === "success-billing" && authKey && customerKey && amount && !hasConfirmedRef.current) {
      hasConfirmedRef.current = true;

      const confirmBilling = async () => {
        setIsPaying(true);

        try {
          const response = await fetch(`${apiBaseUrl}/api/v1/payment/billing/confirm`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            credentials: "include",
            body: JSON.stringify({
              auth_key: authKey,
              customer_key: customerKey,
              amount,
              user_id: Number(localStorage.getItem("user_id")),
            }),
          });

          if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail?.message || "정기 결제 승인에 실패했습니다.");
          }

          alert("정기 결제가 신청되었으며 첫 결제가 완료되었습니다.");
          window.history.replaceState(null, "", window.location.pathname);
          window.location.reload();
        } catch (error) {
          alert(error.message);
        } finally {
          setIsPaying(false);
        }
      };

      confirmBilling();
      return;
    }

    if (result !== "success" || !paymentKey || !orderId || !amount || hasConfirmedRef.current) {
      return;
    }

    hasConfirmedRef.current = true;

    const confirmPayment = async () => {
      setIsPaying(true);

      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/payment/confirm`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({
            payment_key: paymentKey,
            order_id: orderId,
            amount,
            user_id: Number(localStorage.getItem("user_id")),
          }),
        });

        if (!response.ok) {
          throw new Error("결제 승인에 실패했습니다.");
        }

        alert("결제가 완료되었습니다.");
        window.history.replaceState(null, "", window.location.pathname);
        window.location.reload(); //추가 - 결제 완료 후 페이지 새로고침
      } catch (error) {
        alert(error.message);
      } finally {
        setIsPaying(false);
      }
    };

    confirmPayment();
  }, []);

  const handlePlanClick = (paymentPlan) => {
    if (!paymentPlan.isSelectable) {
      return;
    }

    setSelectedPlanId(paymentPlan.id);
  };

  const handlePaymentClick = async () => {
    if (!selectedPlan) {
      alert("요금제를 선택해주세요.");
      return;
    }

    if (selectedPlan.amount <= 0) {
      alert("무료 요금제는 결제가 필요하지 않습니다.");
      return;
    }

    if (!tossClientKey) {
      alert("VITE_TOSS_CLIENT_KEY를 설정해주세요.");
      return;
    }

    // 추가 - 플랜 변경 시 기존 결제 취소
    if (isChangingPlan && currentPayment) {
      const confirmed = window.confirm(
        `현재 ${getPlanName(currentPayment.amount)} 플랜을 취소하고 ${selectedPlan.title.replace("\n", " ")} 플랜으로 변경하시겠습니까?`
      );
      if (!confirmed)
        return;

      try {
        const cancelRes = await fetch(
          `${apiBaseUrl}/api/v1/payment/cancel?payment_id=${currentPayment.payment_id}&cancel_reason=플랜 변경`,
          { method: "POST" }
        );
        if (!cancelRes.ok)
          throw new Error("기존 결제 취소에 실패했습니다.");
      } catch (error) {
        alert(error.message);
        return;
      }
    }
    // 여기까지

    setIsPaying(true);

    try {
      const TossPayments = await loadTossPaymentSdk();
      const tossPayments = TossPayments(tossClientKey);
      const customerKey = userInfo?.customer_key || getCustomerKey();
      const payment = tossPayments.payment({ customerKey });
      const currentUrl = window.location.origin;

      // 정기 결제 (빌링) 인증창 호출
      await payment.requestBillingAuth({
        method: "CARD",
        successUrl: `${currentUrl}/payment?result=success-billing&planId=${selectedPlan.id}&amount=${selectedPlan.amount}`,
        failUrl: `${currentUrl}/payment?result=fail`,
      });
    } catch (error) {
      alert(error.message || "결제창 호출에 실패했습니다.");
      setIsPaying(false);
    }
  };

  const handleStopRecurring = async () => {
    const confirmed = window.confirm(
      "정말 정기 결제를 해지하시겠습니까? 해지하셔도 남은 만료일까지는 계속 이용하실 수 있습니다."
    );
    if (!confirmed) return;

    try {
      const response = await fetch(
        `${apiBaseUrl}/api/v1/payment/billing/stop-recurring?user_id=${userInfo.user_id}`,
        { method: "POST" }
      );
      if (!response.ok) {
        throw new Error("정기 결제 해지에 실패했습니다.");
      }
      alert("정기 결제가 성공적으로 해지되었습니다.");
      window.location.reload();
    } catch (error) {
      alert(error.message);
    }
  };

  // 추가
  if (currentPayment && !isChangingPlan) {
    const remainingDays = userInfo?.subscription_end_date
      ? Math.max(0, Math.ceil((new Date(userInfo.subscription_end_date) - new Date()) / (1000 * 60 * 60 * 24)))
      : 0;

    return (
      <section className="payment-page" aria-label="결제 정보">
        <div className="payment-current-plan">
          <h2 className="payment-current-title">현재 구독 중인 플랜</h2>
          <div className="payment-current-info">
            <p>이용 중인 플랜 · <strong>{getPlanName(currentPayment.amount)}</strong></p>
            <p>결제 방식 · <strong>{userInfo?.billing_key ? "월간 정기 결제 (자동 갱신)" : "일반 이용권 (만료 후 종료)"}</strong></p>
            <p>결제일 · {new Date(currentPayment.paid_at).toLocaleDateString("ko-KR")}</p>
            <p>만료일 · {userInfo?.subscription_end_date
              ? new Date(userInfo.subscription_end_date).toLocaleDateString("ko-KR")
              : "-"}</p>
            <p>잔여 기간 · <strong>{remainingDays}일</strong></p>
          </div>
          <div style={{ display: "flex", gap: "10px", marginTop: "20px" }}>
            <button
              className="payment-change-button"
              type="button"
              onClick={() => setIsChangingPlan(true)}
              style={{ marginTop: 0 }}
            >
              플랜 변경하기
            </button>
            {userInfo?.billing_key && (
              <button
                className="payment-stop-billing-button"
                type="button"
                onClick={handleStopRecurring}
                style={{
                  backgroundColor: "#dc3545",
                  color: "#fff",
                  border: "none",
                  padding: "10px 20px",
                  borderRadius: "5px",
                  cursor: "pointer",
                  fontWeight: "bold",
                }}
              >
                정기결제 해지
              </button>
            )}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="payment-page" aria-label="결제 정보">
      {/* 추가 - 플랜 변경 안내 */}
      {isChangingPlan && (
        <div className="payment-change-notice">
          <p>⚠️ 플랜 변경 시 기존 구독이 취소되고 새 플랜으로 변경됩니다.</p>
          <button
            className="payment-back-button"
            type="button"
            onClick={() => setIsChangingPlan(false)}
          >
            돌아가기
          </button>
        </div>
      )}

      <div className="payment-card-list">
        {paymentPlans.map((paymentPlan) => {
          const isSelected = paymentPlan.id === selectedPlanId;
          const isCurrentPlan = currentPayment && currentPayment.amount === paymentPlan.amount;
          const isDisabled = !paymentPlan.isSelectable || isCurrentPlan;

          return (
            <button
              key={paymentPlan.id}
              className={`payment-card ${isSelected ? "payment-card-selected" : ""} ${
                isDisabled ? "payment-card-disabled" : ""
              }`}
              type="button"
              aria-pressed={isSelected}
              disabled={isDisabled}
              onClick={() => handlePlanClick(paymentPlan)}
            >
              <span
                className={`payment-plan-title ${
                  paymentPlan.id !== "special-three-month" ? "payment-plan-title-lowered" : ""
                }`}
              >
                {paymentPlan.title.split("\n").map((titleLine) => (
                  <span key={titleLine}>{titleLine}</span>
                ))}
              </span>

              <span className="payment-price-box">
                {isCurrentPlan ? (
                  <span className="payment-current-badge" style={{
                    fontSize: "14px",
                    color: "#fff",
                    backgroundColor: "#007bff",
                    padding: "4px 10px",
                    borderRadius: "12px",
                    fontWeight: "bold"
                  }}>현재 이용 중</span>
                ) : (
                  <>
                    <strong className="payment-price">{paymentPlan.price}</strong>
                    <span className="payment-price-unit">원 / 월</span>
                  </>
                )}
              </span>

              <span className="payment-divider" />

              <span className="payment-feature-list">
                {(paymentPlan.features || paymentFeatures).map((paymentFeature) => (
                  <span className="payment-feature-item" key={paymentFeature}>
                    <span className="payment-check-mark" aria-hidden="true" />
                    <span>{paymentFeature}</span>
                  </span>
                ))}
              </span>
            </button>
          );
        })}
      </div>

      <button
        className="payment-submit-button"
        type="button"
        disabled={isPaying}
        onClick={handlePaymentClick}
      >
        {/* 수정 - 플랜 변경 모드일 때 버튼 텍스트 변경 */}
        {isPaying ? "결제 처리 중" : isChangingPlan ? "플랜 변경 결제하기" : "결제하기"}
      </button>
    </section>
  );
}

export default Payment;
