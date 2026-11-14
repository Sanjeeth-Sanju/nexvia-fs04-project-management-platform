
import { LoaderCircle } from "lucide-react";

function Button({
  children,
  type = "button",
  variant = "primary",
  size = "medium",
  loading = false,
  disabled = false,
  fullWidth = false,
  className = "",
  ...props
}) {
  const buttonClasses = [
    "btn",
    `btn-${variant}`,
    `btn-${size}`,
    fullWidth ? "btn-full-width" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      {...props}
      type={type}
      className={buttonClasses}
      disabled={disabled || loading}
      aria-busy={loading}
    >
      {loading && <LoaderCircle size={17} className="btn-spinner" />}
      {children}
    </button>
  );
}

export default Button;
