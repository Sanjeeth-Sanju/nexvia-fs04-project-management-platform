import { useCallback, useEffect, useState } from "react";
import {
  CalendarDays, Check, ChevronLeft, ChevronRight, Edit3,
  Plus, Trash2, X, RotateCcw, Calendar as CalendarIcon,
} from "lucide-react";

import { useToast } from "../../../context/ToastContext";
import Modal from "../../../components/ui/Modal";
import BoardSelect from "./BoardSelect";
import {
  getSprints, createSprint, updateSprint, deleteSprint,
} from "../sprintService";

const emptyForm = {
  name: "", goal: "", start_date: "", end_date: "", status: "planned",
};

function asList(response) {
  return Array.isArray(response) ? response : response?.results || [];
}

function formatDate(value) {
  if (!value) return "Not scheduled";
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    day: "numeric", month: "short", year: "numeric",
  });
}

function dateValue(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function SprintDatePicker({ label, value, onChange, min }) {
  const [open, setOpen] = useState(false);
  const [visibleMonth, setVisibleMonth] = useState(() => {
    const initial = value ? new Date(`${value}T00:00:00`) : new Date();
    return new Date(initial.getFullYear(), initial.getMonth(), 1);
  });

  useEffect(() => {
    if (value) {
      const date = new Date(`${value}T00:00:00`);
      setVisibleMonth(new Date(date.getFullYear(), date.getMonth(), 1));
    }
  }, [value]);

  const year = visibleMonth.getFullYear();
  const month = visibleMonth.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const days = new Date(year, month + 1, 0).getDate();
  const monthLabel = visibleMonth.toLocaleDateString(undefined, {
    month: "long", year: "numeric",
  });
  const cells = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: days }, (_, i) => i + 1),
  ];
  while (cells.length % 7) cells.push(null);

  return (
    <div className="sprint-date-picker">
      <span className="sprint-field-label">{label}</span>
      <button
        type="button"
        className={`sprint-date-trigger${open ? " is-open" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <CalendarIcon size={16} />
        <span>{value ? formatDate(value) : "Choose a date"}</span>
        <ChevronRight size={15} />
      </button>
      {open && (
        <div className="sprint-calendar" role="dialog" aria-label={label}>
          <div className="sprint-calendar__header">
            <button type="button" onClick={() =>
              setVisibleMonth(new Date(year, month - 1, 1))
            } aria-label="Previous month"><ChevronLeft size={17} /></button>
            <strong>{monthLabel}</strong>
            <button type="button" onClick={() =>
              setVisibleMonth(new Date(year, month + 1, 1))
            } aria-label="Next month"><ChevronRight size={17} /></button>
          </div>
          <div className="sprint-calendar__grid">
            {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) =>
              <span className="sprint-calendar__weekday" key={day}>{day}</span>
            )}
            {cells.map((day, index) => {
              if (!day) return <span key={`blank-${index}`} />;
              const date = new Date(year, month, day);
              const iso = dateValue(date);
              const disabled = Boolean(min && iso < min);
              const selected = iso === value;
              return (
                <button
                  type="button"
                  key={iso}
                  disabled={disabled}
                  className={selected ? "selected" : ""}
                  onClick={() => { onChange(iso); setOpen(false); }}
                >{day}</button>
              );
            })}
          </div>
          <div className="sprint-calendar__footer">
            <button type="button" onClick={() => {
              onChange(""); setOpen(false);
            }}>Clear date</button>
            <button type="button" onClick={() => {
              const today = dateValue(new Date());
              if (!min || today >= min) onChange(today);
              setOpen(false);
            }}>Today</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SprintManager({
  projectId, canManage, readOnly = false,
}) {
  const toast = useToast();
  const [sprints, setSprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [sprintToDelete, setSprintToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const loadSprints = useCallback(async () => {
    if (!projectId) {
      setSprints([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setSprints(asList(await getSprints(projectId)));
    } catch (error) {
      toast.error(error.message || "Unable to load sprints.");
    } finally {
      setLoading(false);
    }
  }, [projectId, toast]);

  useEffect(() => { loadSprints(); }, [loadSprints]);

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(emptyForm);
  }

  function openCreate() {
    if (readOnly || !canManage) return;
    setEditingId(null);
    setForm(emptyForm);
    setShowForm(true);
  }

  function openEdit(sprint) {
    if (readOnly || !canManage) return;
    setEditingId(sprint.id);
    setForm({
      name: sprint.name || "",
      goal: sprint.goal || "",
      start_date: sprint.start_date || "",
      end_date: sprint.end_date || "",
      status: sprint.status || "planned",
    });
    setShowForm(true);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (readOnly || !canManage) return;
    if (!form.name.trim()) {
      toast.error("Enter a sprint name.");
      return;
    }
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      toast.error("End date cannot be before start date.");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        ...form,
        name: form.name.trim(),
        goal: form.goal.trim(),
        project: Number(projectId),
        start_date: form.start_date || null,
        end_date: form.end_date || null,
      };
      if (editingId) {
        await updateSprint(editingId, payload);
        toast.success("Sprint updated.");
      } else {
        await createSprint(payload);
        toast.success("Sprint created.");
      }
      closeForm();
      await loadSprints();
    } catch (error) {
      toast.error(error.message || "Unable to save sprint.");
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(sprint, status) {
    if (readOnly || !canManage) return;
    try {
      await updateSprint(sprint.id, { status });
      const messages = {
        active: sprint.status === "completed" ? "Sprint reopened." : "Sprint started.",
        completed: "Sprint completed.",
      };
      toast.success(messages[status] || "Sprint status updated.");
      await loadSprints();
    } catch (error) {
      toast.error(error.message || "Unable to update sprint.");
    }
  }

  function handleDelete(sprint) {
    if (readOnly || !canManage) return;
    setSprintToDelete(sprint);
  }

  async function confirmDeleteSprint() {
    if (!sprintToDelete || deleting) return;
    setDeleting(true);
    try {
      await deleteSprint(sprintToDelete.id);
      toast.success("Sprint deleted.");
      setSprintToDelete(null);
      await loadSprints();
    } catch (error) {
      toast.error(error.message || "Unable to delete sprint.");
    } finally {
      setDeleting(false);
    }
  }

  if (!projectId) return null;

  const canEditSprints = canManage && !readOnly;

  return (
    <section className="sprint-manager">
      <div className="sprint-manager__header">
        <div className="sprint-manager__heading">
          <CalendarDays size={19} />
          <div className="sprint-manager__heading-copy">
            <div className="sprint-manager__title-row">
              <h2>Sprints</h2>
              <span className="sprint-manager__count">{sprints.length}</span>
            </div>
            <p>{readOnly ? "Sprint history" : "Organise work into focused delivery cycles"}</p>
          </div>
        </div>
        {canEditSprints && (
          <button type="button" className="sprint-manager__add" onClick={openCreate}>
            <Plus size={16} /> New sprint
          </button>
        )}
      </div>

      {showForm && canEditSprints && (
        <Modal open={showForm} onClose={closeForm} size="large" titleId="sprint-form-title">
          <form className="sprint-form sprint-form--modal" onSubmit={handleSubmit}>
          <div className="sprint-form__top">
            <h3 id="sprint-form-title">
              {editingId ? "Edit sprint" : "Create sprint"}
            </h3>
          </div>

          <label className="sprint-field">
            <span className="sprint-field-label">Sprint name</span>
            <input className="sprint-input" required maxLength={150}
              value={form.name}
              onChange={(e) => setForm((v) => ({ ...v, name: e.target.value }))}
              placeholder="e.g. Sprint 1" />
          </label>

          <label className="sprint-field">
            <span className="sprint-field-label">Sprint goal</span>
            <textarea className="sprint-input sprint-textarea" rows={3}
              value={form.goal}
              onChange={(e) => setForm((v) => ({ ...v, goal: e.target.value }))}
              placeholder="What should the team achieve in this sprint?" />
          </label>

          <div className="sprint-form__dates">
            <SprintDatePicker label="Start date" value={form.start_date}
              onChange={(value) => setForm((v) => ({
                ...v, start_date: value,
                end_date: v.end_date && value && v.end_date < value ? "" : v.end_date,
              }))} />
            <SprintDatePicker label="End date" value={form.end_date}
              min={form.start_date}
              onChange={(value) => setForm((v) => ({ ...v, end_date: value }))} />
          </div>

          <label className="sprint-field">
            <span className="sprint-field-label">Status</span>
            <BoardSelect
              label="Sprint status"
              value={form.status}
              onChange={(value) => setForm((v) => ({ ...v, status: value }))}
              options={[
                { value: "planned", label: "Planned" },
                { value: "active", label: "Active" },
                { value: "completed", label: "Completed" },
              ]}
            />
          </label>

          <div className="sprint-form__actions">
            <button type="button" className="sprint-button sprint-button--secondary"
              onClick={closeForm}>Cancel</button>
            <button type="submit" className="sprint-button sprint-button--primary"
              disabled={saving}>{saving ? "Saving..." : editingId ? "Save changes" : "Create sprint"}</button>
          </div>
          </form>
        </Modal>
      )}

      {loading ? (
        <p className="sprint-manager__message">Loading sprints...</p>
      ) : sprints.length === 0 ? (
        <div className="sprint-manager__empty">
          <CalendarDays size={22} />
          <p>No sprints yet</p>
          <span>{readOnly ? "No sprint history is available for this project." : "Create a sprint to organise this project's work."}</span>
        </div>
      ) : (
        <div className="sprint-list">
          {sprints.map((sprint) => (
            <article className="sprint-card" key={sprint.id}>
              <div className="sprint-card__content">
                <div className="sprint-card__title">
                  <h3>{sprint.name}</h3>
                  <span className={`sprint-status sprint-status--${sprint.status}`}>
                    {sprint.status}
                  </span>
                </div>
                {sprint.goal && <p className="sprint-card__goal">{sprint.goal}</p>}
                <div className="sprint-card__dates">
                  <CalendarIcon size={14} />
                  <span>{formatDate(sprint.start_date)}</span>
                  <span className="sprint-card__date-separator">to</span>
                  <span>{formatDate(sprint.end_date)}</span>
                </div>
              </div>

              {canEditSprints && (
                <div className="sprint-card__actions">
                  {sprint.status === "planned" && (
                    <button type="button" className="sprint-action-button"
                      onClick={() => handleStatusChange(sprint, "active")}
                      title="Start sprint" aria-label="Start sprint"><Check size={16} /></button>
                  )}
                  {sprint.status === "active" && (
                    <button type="button" className="sprint-action-button"
                      onClick={() => handleStatusChange(sprint, "completed")}
                      title="Complete sprint" aria-label="Complete sprint"><Check size={16} /></button>
                  )}
                  {sprint.status === "completed" && (
                    <button type="button" className="sprint-action-button"
                      onClick={() => handleStatusChange(sprint, "active")}
                      title="Reopen sprint" aria-label="Reopen sprint"><RotateCcw size={16} /></button>
                  )}
                  {sprint.status !== "completed" && (
                    <button type="button" className="sprint-action-button"
                      onClick={() => openEdit(sprint)}
                      title="Edit sprint" aria-label="Edit sprint"><Edit3 size={15} /></button>
                  )}
                  <button type="button" className="sprint-action-button sprint-action-button--delete"
                    onClick={() => handleDelete(sprint)}
                    title="Delete sprint" aria-label="Delete sprint"><Trash2 size={15} /></button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      <Modal
        open={Boolean(sprintToDelete)}
        onClose={() => { if (!deleting) setSprintToDelete(null); }}
        size="small"
        titleId="delete-sprint-title"
      >
        <div className="sprint-delete-dialog">
          <div className="sprint-delete-dialog__icon"><Trash2 size={20} /></div>
          <h2 id="delete-sprint-title">Delete sprint?</h2>
          <p>
            Delete <strong>{sprintToDelete?.name}</strong>? Existing issues will
            remain, but their sprint assignment will be cleared.
          </p>
          <div className="sprint-delete-dialog__actions">
            <button type="button" className="sprint-button sprint-button--secondary"
              onClick={() => setSprintToDelete(null)} disabled={deleting}>Cancel</button>
            <button type="button" className="sprint-button sprint-button--danger"
              onClick={confirmDeleteSprint} disabled={deleting}>
              {deleting ? "Deleting..." : "Delete sprint"}
            </button>
          </div>
        </div>
      </Modal>
    </section>
  );
}
