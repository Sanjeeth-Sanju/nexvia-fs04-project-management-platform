import { MessageSquare } from "lucide-react";

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function CommentList({ comments = [] }) {
  if (!comments.length) {
    return (
      <div className="issue-empty-inline">
        <MessageSquare size={20} />
        <p>No comments yet. Start the conversation.</p>
      </div>
    );
  }

  return (
    <div className="issue-comment-list">
      {comments.map((comment) => {
        const author = comment.author || "Workspace member";
        const initials = String(author)
          .trim()
          .split(/\s+/)
          .slice(0, 2)
          .map((part) => part[0])
          .join("")
          .toUpperCase();

        return (
          <article className="issue-comment" key={comment.id}>
            <div className="issue-comment-avatar" aria-hidden="true">
              {initials || "M"}
            </div>
            <div className="issue-comment-content">
              <div className="issue-comment-meta">
                <strong>{author}</strong>
                <time dateTime={comment.created_at}>
                  {formatDate(comment.created_at)}
                  {comment.updated_at && comment.updated_at !== comment.created_at
                    ? " · edited"
                    : ""}
                </time>
              </div>
              <p>{comment.body}</p>
            </div>
          </article>
        );
      })}
    </div>
  );
}
