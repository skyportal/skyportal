export type StatusColor =
  "success" | "primary" | "warning" | "error" | "default";

export const STATUS_FILTERS: {
  label: string;
  status: string;
  color: StatusColor;
}[] = [
  { label: "Completed", status: "complete", color: "success" },
  { label: "Submitted", status: "submitted", color: "primary" },
  { label: "Pending", status: "pending", color: "warning" },
  { label: "Failed", status: "failed", color: "error" },
  { label: "Deleted", status: "deleted", color: "default" },
];

export const statusColor = (status: string): StatusColor => {
  if (/fail|reject|error/i.test(status)) return "error";
  if (/complete|committed/i.test(status)) return "success";
  if (/submitted/i.test(status)) return "primary";
  if (/pending/i.test(status)) return "warning";
  return "default";
};
