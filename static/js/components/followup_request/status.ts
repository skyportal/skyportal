export const STATUS_FILTERS = [
  { label: "Completed", status: "complete", color: "success.main" },
  { label: "Submitted", status: "submitted", color: "primary.main" },
  { label: "Pending", status: "pending", color: "warning.main" },
  { label: "Failed", status: "failed", color: "error.main" },
  { label: "Deleted", status: "deleted", color: "text.secondary" },
];

export const statusColor = (status: string) => {
  if (/fail|reject|error/i.test(status)) return "error";
  if (/complete|committed/i.test(status)) return "success";
  if (/submitted/i.test(status)) return "primary";
  if (/pending/i.test(status)) return "warning";
  return "default";
};
