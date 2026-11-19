
import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, X } from "lucide-react";

export default function WorkspaceMultiSelect({
  workspaces = [],
  value = [],
  onChange,
  disabled = false,
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    function handleOutside(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setOpen(false);
      }
    }

    function handleKey(event) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("keydown", handleKey);

    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("keydown", handleKey);
    };
  }, []);

  const selected = workspaces.filter((workspace) =>
    value.includes(String(workspace.id))
  );

  function toggleWorkspace(id) {
    const key = String(id);
    onChange(
      value.includes(key)
        ? value.filter((item) => item !== key)
        : [...value, key]
    );
  }

  function selectAll() {
    onChange(workspaces.map((workspace) => String(workspace.id)));
  }

  function clearAll() {
    onChange([]);
  }

  return (
    <div className="workspace-multi-select" ref={rootRef}>
      <button
        type="button"
        className={`board-select-trigger${open ? " is-open" : ""}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled || workspaces.length === 0}
        onClick={() => setOpen((current) => !current)}
      >
        <span>
          {selected.length
            ? `${selected.length} workspace${selected.length === 1 ? "" : "s"} selected`
            : "Choose workspaces"}
        </span>
        <ChevronDown size={18} />
      </button>

      {selected.length > 0 && (
        <div className="workspace-multi-selected">
          {selected.map((workspace) => (
            <span className="workspace-multi-chip" key={workspace.id}>
              {workspace.name}
              <button
                type="button"
                aria-label={`Remove ${workspace.name}`}
                disabled={disabled}
                onClick={() => toggleWorkspace(workspace.id)}
              >
                <X size={13} />
              </button>
            </span>
          ))}
          <button
            type="button"
            className="workspace-multi-clear"
            onClick={clearAll}
            disabled={disabled}
          >
            Clear
          </button>
        </div>
      )}

      {open && (
        <div
          className="board-select-menu workspace-multi-menu"
          role="listbox"
          aria-label="Select workspaces"
          aria-multiselectable="true"
        >
          <div className="workspace-multi-menu-heading">
            <p className="board-select-menu-title">Select workspaces</p>
            <button type="button" onClick={selectAll} disabled={disabled}>
              Select all
            </button>
          </div>

          {workspaces.map((workspace) => {
            const active = value.includes(String(workspace.id));

            return (
              <button
                type="button"
                role="option"
                aria-selected={active}
                key={workspace.id}
                className={`board-select-option${active ? " selected" : ""}`}
                onClick={() => toggleWorkspace(workspace.id)}
                disabled={disabled}
              >
                <span className="workspace-multi-option">
                  <span className={`workspace-multi-checkbox${active ? " checked" : ""}`}>
                    {active && <Check size={13} />}
                  </span>
                  {workspace.name}
                </span>
                {active && <Check size={18} />}
              </button>
            );
          })}

          {workspaces.length === 0 && (
            <p className="workspace-multi-empty">No workspaces available.</p>
          )}
        </div>
      )}
    </div>
  );
}
