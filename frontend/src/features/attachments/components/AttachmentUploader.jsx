import { useRef, useState } from "react";
import { Paperclip, Upload } from "lucide-react";

export default function AttachmentUploader({ onUpload, disabled = false }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  async function handleChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      window.alert("Please choose a file smaller than 10 MB.");
      event.target.value = "";
      return;
    }

    setUploading(true);
    try {
      await onUpload(file);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <div className="issue-upload-control">
      <input
        ref={inputRef}
        type="file"
        onChange={handleChange}
        disabled={disabled || uploading}
        hidden
      />
      <button
        type="button"
        className="issue-action-button issue-action-secondary"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || uploading}
      >
        {uploading ? <Upload size={15} /> : <Paperclip size={15} />}
        {uploading ? "Uploading..." : "Add attachment"}
      </button>
      <span>Maximum file size: 10 MB</span>
    </div>
  );
}
