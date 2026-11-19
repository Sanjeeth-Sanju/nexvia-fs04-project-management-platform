import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  CreditCard,
  Crown,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Users,
  FolderKanban,
  Building2,
  HardDrive,
  Clock3,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { apiRequest } from "../../services/api";
import { useToast } from "../../context/ToastContext";
import "./BillingPage.css";

const PLAN_PRICES = {
  free: 0,
  pro: 499,
  business: 1499,
};

const PLAN_ICONS = {
  free: Building2,
  pro: Sparkles,
  business: Crown,
};

function formatLimit(value, suffix = "") {
  if (value === undefined) return "—";
  if (value === null || value === -1 || value === "unlimited") {
    return "Unlimited";
  }
  return `${value.toLocaleString()}${suffix}`;
}

function formatStorage(mb) {
  if (mb === undefined) return "—";
  if (mb === null) return "Unlimited";
  if (mb >= 1024) return `${mb / 1024} GB`;
  return `${mb} MB`;
}

function getPlanFeatures(plan) {
  const limits = plan?.limits || {};

  return [
    `${formatLimit(limits.workspaces)} owned workspaces`,
    `${formatLimit(limits.admin_memberships)} Admin memberships`,
    `${formatLimit(limits.member_memberships)} Member memberships`,
    `${formatLimit(limits.members_per_workspace)} members per workspace`,
    `${formatLimit(limits.projects_per_workspace)} projects per workspace`,
    `${formatLimit(limits.issues_per_workspace)} issues per workspace`,
    `${formatStorage(limits.storage_mb)} storage`,
    `${formatLimit(limits.audit_retention_days, " days")} activity history`,
  ];
}

function formatDate(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function formatStatus(status) {
  if (!status) return "Active";
  return status.replaceAll("_", " ");
}

function LimitRow({ icon: Icon, label, value }) {
  return (
    <div className="billing-limit-row">
      <span className="billing-limit-icon"><Icon size={17} /></span>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function BillingPage() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [plans, setPlans] = useState([]);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");
  const checkoutToastHandled = useRef(false);

  const loadBilling = useCallback(async () => {
    setLoading(true);
    try {
      const [plansResult, overviewResult] = await Promise.all([
        apiRequest("/billing/plans/"),
        apiRequest("/billing/overview/"),
      ]);
      setPlans(plansResult.plans || []);
      setOverview(overviewResult);
    } catch (error) {
      toast.error(error.message || "Unable to load billing information.");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadBilling();
  }, [loadBilling]);

  useEffect(() => {
    const result = searchParams.get("checkout");
    if (!result) return;

    let cancelled = false;

    if (result === "cancelled") {
      toast.info("Checkout was cancelled. No payment was made.");
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete("checkout");
      setSearchParams(nextParams, { replace: true });
      return;
    }

    if (result === "success") {
      if (!checkoutToastHandled.current) {
        checkoutToastHandled.current = true;
        toast.success("Payment completed. Syncing your subscription...");
      }

      const syncSubscription = async () => {
        // Allow the Stripe webhook time to reach the backend.
        for (let attempt = 0; attempt < 10; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, 2000));

          if (cancelled) return;

          try {
            const latest = await apiRequest("/billing/overview/");
            if (!cancelled) setOverview(latest);
          } catch (error) {
            console.error("Subscription refresh attempt failed:", error);
          }
        }

        if (!cancelled) {
          const nextParams = new URLSearchParams(searchParams);
          nextParams.delete("checkout");
          setSearchParams(nextParams, { replace: true });
        }
      };

      syncSubscription();
    }

    return () => {
      cancelled = true;
    };
  }, [searchParams, setSearchParams, toast]);

  async function handleCheckout(plan) {
    setAction(plan);
    try {
      const result = await apiRequest("/billing/checkout/", {
        method: "POST",
        body: JSON.stringify({ plan }),
      });

      if (!result.checkout_url) {
        throw new Error("Stripe did not return a Checkout URL.");
      }

      window.location.assign(result.checkout_url);
    } catch (error) {
      toast.error(error.message || "Unable to start checkout.");
      setAction("");
    }
  }

  async function handlePortal() {
    setAction("portal");
    try {
      const result = await apiRequest("/billing/portal/", {
        method: "POST",
        body: JSON.stringify({}),
      });

      if (!result.portal_url) {
        throw new Error("Stripe did not return a billing portal URL.");
      }

      window.location.assign(result.portal_url);
    } catch (error) {
      toast.error(error.message || "Unable to open subscription management.");
      setAction("");
    }
  }

  if (loading) {
    return (
      <main className="container phase2-page billing-page">
        <div className="billing-loading">
          <LoaderCircle className="billing-spinner" size={25} />
          <span>Loading your billing information...</span>
        </div>
      </main>
    );
  }

  const currentPlan = overview?.plan || "free";
  const limits = overview?.limits || {};
  const orderedPlans = ["free", "pro", "business"]
    .map((id) => plans.find((plan) => plan.id === id))
    .filter(Boolean);

  return (
    <main className="container phase2-page billing-page">
      <header className="phase2-page-header billing-header">
        <div>
          <p className="phase2-eyebrow">PLAN & SUBSCRIPTION</p>
          <h1>Billing</h1>
          <p className="phase2-description">
            Choose the right plan for your team and manage your subscription.
          </p>
        </div>
        <button
          type="button"
          className="phase2-button phase2-button--secondary"
          onClick={loadBilling}
          disabled={loading || Boolean(action)}
        >
          <RefreshCw size={16} /> Refresh
        </button>
      </header>

      <section className="billing-current-card">
        <div className="billing-current-main">
          <span className="billing-current-icon"><CreditCard size={21} /></span>
          <div>
            <p className="billing-section-eyebrow">CURRENT SUBSCRIPTION</p>
            <div className="billing-current-title">
              <h2>{overview?.plan_name || "Free"} plan</h2>
              <span className="billing-status">
                {formatStatus(overview?.status)}
              </span>
            </div>
            <p className="billing-current-description">
              {overview?.cancel_at_period_end
                ? "Your subscription is set to end at the current period."
                : overview?.current_period_end
                  ? `Current period ends ${formatDate(overview.current_period_end)}`
                  : "You are currently on the free plan."}
            </p>
          </div>
        </div>

        {overview?.stripe_connected && (
          <button
            type="button"
            className="phase2-button phase2-button--secondary"
            onClick={handlePortal}
            disabled={Boolean(action)}
          >
            {action === "portal" ? (
              <LoaderCircle className="billing-spinner" size={16} />
            ) : (
              <CreditCard size={16} />
            )}
            Manage subscription
          </button>
        )}
      </section>

      <section className="billing-usage-section">
        <div className="billing-section-heading">
          <div>
            <h2>Your plan limits</h2>
            <p>Limits currently applied to your account.</p>
          </div>
        </div>
        <div className="billing-limits-grid">
          <LimitRow icon={Building2} label="Workspaces" value={formatLimit(limits.workspaces)} />
          <LimitRow icon={FolderKanban} label="Projects per workspace" value={formatLimit(limits.projects_per_workspace)} />
          <LimitRow icon={Users} label="Members per workspace" value={formatLimit(limits.members_per_workspace)} />
          <LimitRow icon={HardDrive} label="Storage" value={formatStorage(limits.storage_mb)} />
          <LimitRow icon={Clock3} label="Audit history" value={formatLimit(limits.audit_retention_days, " days")} />
        </div>
      </section>

      <section className="billing-plans-section">
        <div className="billing-section-heading">
          <div>
            <h2>Choose your plan</h2>
            <p>Upgrade when your team needs more room to grow.</p>
          </div>
          <span className="billing-billing-cycle">Billed monthly</span>
        </div>

        <div className="billing-plan-grid">
          {orderedPlans.map((plan) => {
            const Icon = PLAN_ICONS[plan.id] || Sparkles;
            const planRank = { free: 0, pro: 1, business: 2 };
            const isCurrent = currentPlan === plan.id;
            const isUpgrade = (planRank[plan.id] ?? -1) > (planRank[currentPlan] ?? 0);
            const isIncluded = (planRank[plan.id] ?? -1) < (planRank[currentPlan] ?? 0);
            const price = PLAN_PRICES[plan.id];

            return (
              <article
                key={plan.id}
                className={`billing-plan-card ${plan.id === "pro" ? "billing-plan-card--featured" : ""} ${isCurrent ? "is-current" : ""}`}
              >
                {plan.id === "pro" && (
                  <span className="billing-popular-tag">POPULAR</span>
                )}
                <div className="billing-plan-icon"><Icon size={20} /></div>
                <h3>{plan.name}</h3>
                <p className="billing-plan-description">{plan.description}</p>

                <div className="billing-plan-price">
                  <strong>{price === 0 ? "Free" : `₹${price.toLocaleString("en-IN")}`}</strong>
                  {price > 0 && <span>/ month</span>}
                </div>

                <div className="billing-plan-divider" />

                <p className="billing-feature-label">WHAT'S INCLUDED</p>
                <ul className="billing-feature-list">
                  {getPlanFeatures(plan).map((feature) => (
                    <li key={feature}><Check size={16} />{feature}</li>
                  ))}
                </ul>

                <div className="billing-plan-action">
                  {isCurrent ? (
                    <span className="billing-plan-current-label">
                      <ShieldCheck size={16} /> Current plan
                    </span>
                  ) : isIncluded ? (
                    <span className="billing-plan-current-label">
                      <Check size={16} /> Included in {overview?.plan_name || currentPlan}
                    </span>
                  ) : isUpgrade ? (
                    <button
                      type="button"
                      className="phase2-button phase2-button--primary"
                      onClick={() => handleCheckout(plan.id)}
                      disabled={Boolean(action)}
                    >
                      {action === plan.id ? (
                        <LoaderCircle className="billing-spinner" size={16} />
                      ) : (
                        <>Upgrade to {plan.name} <ArrowRight size={16} /></>
                      )}
                    </button>
                  ) : (
                    <span className="billing-plan-current-label">
                      <Check size={16} /> Included
                    </span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <footer className="billing-footer-note">
        <ShieldCheck size={17} />
        <p>
          Payments are securely processed by Stripe. Your card details are never
          stored on Nexvia servers. This environment is configured for Stripe test mode.
        </p>
      </footer>
    </main>
  );
}
