import { useState } from "react";
import { Send } from "lucide-react";

export default function CommentForm({ onSubmit, disabled = false }) {
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const value = body.trim();
    if (!value || disabled || submitting) return;

    setSubmitting(true);
    try {
      await onSubmit(value);
      setBody("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="issue-comment-form" onSubmit={handleSubmit}>
      <textarea
        value={body}
        onChange={(event) => setBody(event.target.value)}
        placeholder={disabled ? "Comments are disabled for this project." : "Write a comment..."}
        rows={3}
        maxLength={5000}
        disabled={disabled || submitting}
        aria-label="Write a comment"
      />
      <div className="issue-comment-form-footer">
        <span>{body.length}/5000</span>
        <button
          type="submit"
          className="issue-action-button issue-action-primary"
          disabled={disabled || submitting || !body.trim()}
        >
          <Send size={15} />
          {submitting ? "Posting..." : "Post comment"}
        </button>
      </div>
    </form>
  );
}
