
import { LoaderCircle } from "lucide-react";

function Loader({ size = "medium", text = "Loading...", fullPage = false }) {
  return (
    <div className={`loader-container ${fullPage ? "loader-full-page" : ""}`}>
      <LoaderCircle
        className="loader-spinner"
        size={size === "small" ? 18 : size === "large" ? 36 : 26}
      />
      {text && <p className="loader-text">{text}</p>}
    </div>
  );
}

export default Loader;
