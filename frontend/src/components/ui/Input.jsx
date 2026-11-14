
function Input({
  label,
  name,
  type = "text",
  placeholder,
  value,
  onChange,
  error,
  required = false,
  autoComplete,
  disabled = false,
  ...props
}) {
  const inputId = props.id || name;

  return (
    <div className="form-field">
      {label && (
        <label className="form-label" htmlFor={inputId}>
          {label}
          {required && <span aria-hidden="true"> *</span>}
        </label>
      )}

      <input
        {...props}
        id={inputId}
        name={name}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required={required}
        autoComplete={autoComplete}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${inputId}-error` : undefined}
        className={`form-input ${error ? "form-input-error" : ""} ${
          props.className || ""
        }`}
      />

      {error && (
        <p className="form-error" id={`${inputId}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}

export default Input;
