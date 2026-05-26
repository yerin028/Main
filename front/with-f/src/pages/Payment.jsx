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
  },
  {
    id: "standard",
    title: "스탠다드",
    price: "4,900",
    amount: 4900,
    periodMonth: 1,
    isDefault: true,
    isSelectable: true,
  },
  {
    id: "special-three-month",
    title: "특별할인\n3개월",
    price: "9,900",
    amount: 9900,
    periodMonth: 3,
    isDefault: false,
    isSelectable: true,
  },
];

const paymentFeatures = ["수어 학습", "수어 퀴즈", "수어 통역 서비스"];

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

  const selectedPlan = useMemo(
    () => paymentPlans.find((paymentPlan) => paymentPlan.id === selectedPlanId),
    [selectedPlanId],
  );

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
          }),
        });

        if (!response.ok) {
          throw new Error("결제 승인에 실패했습니다.");
        }

        alert("결제가 완료되었습니다.");
        window.history.replaceState(null, "", window.location.pathname);
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

    setIsPaying(true);

    try {
      const orderId = createOrderId();

      await fetch(`${apiBaseUrl}/api/v1/payment`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          amount: selectedPlan.amount,
          payment_status: "READY",
          payment_method: "CARD",
          toss_order_id: orderId,
        }),
      });

      const TossPayments = await loadTossPaymentSdk();
      const tossPayments = TossPayments(tossClientKey);
      const payment = tossPayments.payment({ customerKey: getCustomerKey() });
      const currentUrl = window.location.origin;

      await payment.requestPayment({
        method: "CARD",
        amount: {
          currency: "KRW",
          value: selectedPlan.amount,
        },
        orderId,
        orderName: `WITH ${selectedPlan.title.replace("\n", " ")} 이용권`,
        successUrl: `${currentUrl}/payment?result=success`,
        failUrl: `${currentUrl}/payment?result=fail`,
      });
    } catch (error) {
      alert(error.message || "결제창 호출에 실패했습니다.");
      setIsPaying(false);
    }
  };

  return (
    <section className="payment-page" aria-label="결제 정보">
      <div className="payment-card-list">
        {paymentPlans.map((paymentPlan) => {
          const isSelected = paymentPlan.id === selectedPlanId;
          const isDisabled = !paymentPlan.isSelectable;

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
              <span className="payment-plan-title">
                {paymentPlan.title.split("\n").map((titleLine) => (
                  <span key={titleLine}>{titleLine}</span>
                ))}
              </span>

              <span className="payment-price-box">
                <strong className="payment-price">{paymentPlan.price}</strong>
                <span className="payment-price-unit">원 / 월</span>
              </span>

              <span className="payment-divider" />

              <span className="payment-feature-list">
                {paymentFeatures.map((paymentFeature) => (
                  <span className="payment-feature-item" key={paymentFeature}>
                    <span className="payment-check-mark" aria-hidden="true">
                      ✓
                    </span>
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
        {isPaying ? "결제 처리 중" : "결제하기"}
      </button>
    </section>
  );
}

export default Payment;
