import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import "./BoardSelect.css";

export default function BoardSelect({
  value,
  onChange,
  options = [],
  label = "Select option",
  className = "",
  required = false,
  disabled = false,
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const selected = options.find((option) => String(option.value) === String(value));

  useEffect(() => {
    function handlePointerDown(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <div className={`board-select ${className}${disabled ? " is-disabled" : ""}`} ref={rootRef}>
      <button
        type="button"
        className={`board-select-trigger${open ? " is-open" : ""}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-required={required}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        <span>{selected?.label || label}</span>
        <ChevronDown size={18} />
      </button>

      {open && (
        <div className="board-select-menu" role="listbox" aria-label={label}>
          <p className="board-select-menu-title">{label}</p>
          {options.map((option) => {
            const active = String(option.value) === String(value);
            return (
              <button
                type="button"
                role="option"
                aria-selected={active}
                key={String(option.value)}
                className={`board-select-option${active ? " selected" : ""}`}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
              >
                <span>{option.label}</span>
                {active && <Check size={18} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
