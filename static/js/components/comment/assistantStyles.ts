import type { Theme } from "@mui/material/styles";
import { alpha } from "@mui/material/styles";

export const markdownSx = (theme: Theme) => ({
  fontSize: "0.875rem",
  lineHeight: 1.6,
  overflowWrap: "anywhere",
  "& > :last-child": { marginBottom: 0 },
  "& p, & ul, & ol, & pre, & table, & blockquote": { margin: "0 0 0.65em" },
  "& ul, & ol": { paddingLeft: "1.25rem" },
  "& li + li": { marginTop: "0.2em" },
  "& h1, & h2, & h3, & h4": {
    fontSize: "0.95rem",
    fontWeight: 600,
    margin: "0.9em 0 0.4em",
  },
  "& a": { color: theme.palette.primary.main },
  "& code": {
    fontSize: "0.8em",
    padding: "0.1em 0.35em",
    borderRadius: "4px",
    backgroundColor: alpha(theme.palette.text.primary, 0.07),
  },
  "& pre": {
    padding: "0.6rem 0.75rem",
    borderRadius: "8px",
    overflowX: "auto",
    backgroundColor: alpha(theme.palette.text.primary, 0.05),
  },
  "& pre code": { padding: 0, backgroundColor: "transparent" },
  "& blockquote": {
    paddingLeft: "0.75rem",
    borderLeft: `3px solid ${theme.palette.divider}`,
    color: theme.palette.text.secondary,
  },
  "& table": {
    display: "block",
    overflowX: "auto",
    borderCollapse: "collapse",
    fontSize: "0.8rem",
  },
  "& th, & td": {
    padding: "0.3rem 0.6rem",
    border: `1px solid ${theme.palette.divider}`,
    textAlign: "left",
  },
  "& th": {
    fontWeight: 600,
    backgroundColor: alpha(theme.palette.text.primary, 0.04),
  },
});

export const cardSx = (theme: Theme) => ({
  display: "flex",
  flexDirection: "column",
  alignItems: "flex-start",
  gap: "0.4rem",
  marginTop: "0.75rem",
  padding: "0.75rem 0.875rem",
  borderRadius: "12px",
  border: `1px solid ${theme.palette.divider}`,
  backgroundColor: alpha(theme.palette.text.primary, 0.02),
});

export const cardTitleSx = { fontSize: "0.8rem", fontWeight: 600 } as const;

export const cardNoteSx = {
  fontSize: "0.75rem",
  color: "text.secondary",
} as const;

export const pillButtonSx = {
  borderRadius: "999px",
  textTransform: "none",
  fontSize: "0.75rem",
  padding: "0.2rem 0.85rem",
} as const;

export const linkButtonSx = (theme: Theme) => ({
  display: "inline-flex",
  alignItems: "center",
  gap: "0.15rem",
  padding: 0,
  border: 0,
  background: "none",
  font: "inherit",
  fontSize: "0.75rem",
  color: theme.palette.text.secondary,
  cursor: "pointer",
  "&:hover": { color: theme.palette.text.primary },
});

export const chevronSx = (open: boolean) => ({
  fontSize: "1rem",
  transition: "transform 150ms",
  transform: open ? "rotate(180deg)" : "none",
});
