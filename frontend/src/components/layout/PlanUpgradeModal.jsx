import { useEffect, useState } from "react";
import { Check, X, ArrowRight, Crown, Sparkles } from "lucide-react";
import { apiRequest } from "../../services/api";
import { useNavigate } from "react-router-dom";
import "./PlanUpgradeModal.css";

const PLANS = [
  {
    id: "pro",
    name: "Pro",
    price: "₹499",
    description: "More room for growing teams.",
    icon: Sparkles,
    features: [
      "10 owned workspaces",
      "10 Admin memberships",
      "10 Member memberships",
      "25 members per workspace",
      "Unlimited projects and issues",
      "10 GB storage",
      "90 days activity history",
    ],
  },
  {
    id: "business",
    name: "Business",
    price: "₹1,499",
    description: "Scale your project operations.",
    icon: Crown,
    features: [
      "Unlimited owned workspaces",
      "Unlimited Admin and Member memberships",
      "100 members per workspace",
      "Unlimited projects and issues",
      "100 GB storage",
      "365 days activity history",
    ],
  },
];

export default function PlanUpgradeModal({ currentPlan = "free", onClose }) {
  const [action, setAction] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape" && !action) onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [action, onClose]);

  const availablePlans = PLANS.filter((plan) => {
    if (currentPlan === "free") return true;
    if (currentPlan === "pro") return plan.id === "business";
    return false;
  });

  async function handleUpgrade(plan) {
    setAction(plan);
    setError("");
    try {
      const result = await apiRequest("/billing/checkout/", {
        method: "POST",
        body: JSON.stringify({ plan }),
      });

      if (!result.checkout_url) {
        throw new Error("Stripe did not return a Checkout URL.");
      }

      window.location.assign(result.checkout_url);
    } catch (err) {
      setError(err.message || "Unable to start checkout. Please try again.");
      setAction("");
    }
  }

  return (
    <div
      className="plan-upgrade-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !action) onClose();
      }}
    >
      <section
        className="plan-upgrade-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="plan-upgrade-title"
      >
        <button
          type="button"
          className="plan-upgrade-close"
          onClick={onClose}
          disabled={Boolean(action)}
          aria-label="Close upgrade dialog"
        >
          <X size={19} />
        </button>

        <div className="plan-upgrade-heading">
          <span className="plan-upgrade-eyebrow">NEXVIA PLANS</span>
          <h2 id="plan-upgrade-title">Choose your next level</h2>
          <p>
            You're currently on the {currentPlan} plan. Upgrade to unlock
            higher account limits as your team grows.
          </p>
        </div>

        {availablePlans.length ? (
          <div className="plan-upgrade-options">
            {availablePlans.map((plan) => {
              const Icon = plan.icon;
              return (
                <article className="plan-upgrade-card" key={plan.id}>
                  <div className="plan-upgrade-card-heading">
                    <span className="plan-upgrade-icon"><Icon size={19} /></span>
                    <div>
                      <h3>{plan.name}</h3>
                      <p>{plan.description}</p>
                    </div>
                  </div>

                  <div className="plan-upgrade-price">
                    <strong>{plan.price}</strong>
                    <span>/ month</span>
                  </div>

                  <ul>
                    {plan.features.map((feature) => (
                      <li key={feature}>
                        <Check size={15} />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <button
                    type="button"
                    className="plan-upgrade-action"
                    onClick={() => handleUpgrade(plan.id)}
                    disabled={Boolean(action)}
                  >
                    {action === plan.id ? "Redirecting..." : `Upgrade to ${plan.name}`}
                    <ArrowRight size={16} />
                  </button>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="plan-upgrade-highest">
            You're already on our highest plan.
          </div>
        )}

        {error && <p className="plan-upgrade-error" role="alert">{error}</p>}

        <div className="plan-upgrade-footer">
          <span>Need to manage an existing subscription?</span>
          <button
            type="button"
            onClick={() => {
              onClose();
              navigate("/billing");
            }}
          >
            Manage billing
          </button>
        </div>
      </section>
    </div>
  );
}
