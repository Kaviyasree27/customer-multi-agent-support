const MAP = {
  // order status
  placed: "bg-slate/10 text-slate",
  processing: "bg-amber-light text-amber",
  confirmed: "bg-amber-light text-amber",
  shipped: "bg-teal-light text-teal-dark",
  delivered: "bg-teal-light text-teal-dark",
  cancelled: "bg-coral-light text-coral",
  // ticket status
  open: "bg-amber-light text-amber",
  in_progress: "bg-teal-light text-teal-dark",
  resolved: "bg-teal-light text-teal-dark",
  closed: "bg-slate/10 text-slate",
  escalated: "bg-coral-light text-coral",
  // priority
  low: "bg-slate/10 text-slate",
  medium: "bg-amber-light text-amber",
  high: "bg-coral-light text-coral",
  critical: "bg-coral text-white",
};

export default function StatusBadge({ value }) {
  const cls = MAP[value] || "bg-slate/10 text-slate";
  const label = (value || "").replace(/_/g, " ");
  return <span className={`badge ${cls}`}>{label}</span>;
}
