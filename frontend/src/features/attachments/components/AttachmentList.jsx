import { FileText, Download, Trash2, Paperclip } from "lucide-react";

function formatSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ""
    : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

export default function AttachmentList({
  attachments = [],
  canDelete,
  onDelete,
}) {
  if (!attachments.length) {
    return (
      <div className="issue-empty-inline">
        <Paperclip size={20} />
        <p>No files attached to this issue.</p>
      </div>
    );
  }

  return (
    <div className="issue-attachment-list">
      {attachments.map((attachment) => {
        const rawUrl = attachment.file;
        const apiBase = (
          import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"
        ).replace(/\/+$/, "");
        const fileUrl = rawUrl
          ? (/^https?:\/\//i.test(rawUrl)
              ? rawUrl
              : `${apiBase.replace(/\/api$/, "")}${rawUrl.startsWith("/") ? "" : "/"}${rawUrl}`)
          : null;

        return (
          <article className="issue-attachment" key={attachment.id}>
            <div className="issue-attachment-icon">
              <FileText size={19} />
            </div>
            <div className="issue-attachment-info">
              <strong title={attachment.filename}>
                {attachment.filename || "Attached file"}
              </strong>
              <span>
                {attachment.uploaded_by || "Workspace member"}
                {attachment.uploaded_at ? ` · ${formatDate(attachment.uploaded_at)}` : ""}
                {attachment.file_size ? ` · ${formatSize(attachment.file_size)}` : ""}
              </span>
            </div>
            <div className="issue-attachment-actions">
              {fileUrl && (
                <a
                  className="issue-attachment-icon-button"
                  href={fileUrl}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={`Download ${attachment.filename || "attachment"}`}
                  title="Open file"
                >
                  <Download size={16} />
                </a>
              )}
              {canDelete(attachment) && (
                <button
                  type="button"
                  className="issue-attachment-icon-button issue-attachment-delete"
                  onClick={() => onDelete(attachment)}
                  aria-label={`Delete ${attachment.filename || "attachment"}`}
                  title="Delete attachment"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}
