import {
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import {
  Check,
  CheckCircle,
  Circle,
  Copy,
  SpinnerGap,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import type { RecordingStatus } from "./domain";

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "icon";
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className={`sf-button sf-button--${variant} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
export function GlassPanel({
  children,
  className = "",
  label,
}: {
  children: ReactNode;
  className?: string;
  label?: string;
}) {
  return (
    <section className={`sf-panel ${className}`} aria-label={label}>
      {children}
    </section>
  );
}
export function StatusChip({ status }: { status: RecordingStatus }) {
  const Icon =
    status === "ready"
      ? CheckCircle
      : status === "processing"
        ? SpinnerGap
        : status === "failed"
          ? WarningCircle
          : Circle;
  const labels = {
    ready: "Ready",
    processing: "Processing",
    recorded: "Recorded",
    failed: "Failed",
  };
  return (
    <span className={`sf-status sf-status--${status}`}>
      <Icon size={15} weight={status === "ready" ? "fill" : "regular"} />
      {labels[status]}
    </span>
  );
}
export function CopyId({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  return (
    <button
      type="button"
      className="sf-copy"
      aria-label={`Copy ${value}`}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          clearTimeout(timer.current);
          timer.current = setTimeout(() => setCopied(false), 1800);
        } catch {
          setCopied(false);
        }
      }}
    >
      <span>{value}</span>
      {copied ? <Check size={14} /> : <Copy size={14} />}
      <span className="sf-sr" role="status">
        {copied ? "Copied" : ""}
      </span>
    </button>
  );
}
export function ProfileIdentity({
  name,
  handle,
  compact = false,
  photo,
}: {
  name: string;
  handle: string;
  compact?: boolean;
  photo?: string;
}) {
  return (
    <div className={`sf-identity ${compact ? "sf-identity--compact" : ""}`}>
      <span className="sf-avatar">
        {photo ? (
          <img src={photo} alt="Your profile photo" />
        ) : (
          name
            .split(" ")
            .map((n) => n[0])
            .slice(0, 2)
            .join("")
        )}
      </span>
      <span>
        <strong>{name}</strong>
        <small>@{handle}</small>
      </span>
    </div>
  );
}
export function Segments<T extends string>({
  items,
  value,
  onChange,
  label,
}: {
  items: { id: T; label: string; count?: number }[];
  value: T;
  onChange: (id: T) => void;
  label: string;
}) {
  return (
    <div className="sf-segments" role="group" aria-label={label}>
      {items.map((item) => (
        <button
          type="button"
          key={item.id}
          aria-pressed={value === item.id}
          onClick={() => onChange(item.id)}
        >
          {item.label}
          {item.count !== undefined && <span>{item.count}</span>}
        </button>
      ))}
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
  className = "",
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null),
    id = useId();
  useEffect(() => {
    const dialog = ref.current!;
    const previous = document.activeElement as HTMLElement | null;
    dialog.showModal();
    return () => {
      dialog.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={id}
      className={`sf-dialog ${className}`}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <header>
        <h2 id={id}>{title}</h2>
        <Button variant="icon" aria-label="Close dialog" onClick={onClose}>
          <X size={21} />
        </Button>
      </header>
      {children}
    </dialog>
  );
}
export function SectionHeading({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="sf-section-heading">
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}
export function MetricCard({
  label,
  value,
  note,
}: {
  label: string;
  value: ReactNode;
  note?: string;
}) {
  return (
    <div className="sf-metric">
      <dt>{label}</dt>
      <dd>{value}</dd>
      {note && <small>{note}</small>}
    </div>
  );
}
export function Notice({
  children,
  danger = false,
}: {
  children: ReactNode;
  danger?: boolean;
}) {
  return (
    <p
      className={`sf-notice ${danger ? "sf-notice--danger" : ""}`}
      role={danger ? "alert" : "status"}
    >
      <WarningCircle size={19} />
      <span>{children}</span>
    </p>
  );
}
