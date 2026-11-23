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

export const bubbleSx = (
  theme: Theme,
  mine: boolean,
  side: "left" | "right" = "left",
) => ({
  padding: "0.375rem 0.75rem",
  borderRadius: side === "left" ? "4px 16px 16px 16px" : "16px 4px 16px 16px",
  fontSize: "0.875rem",
  lineHeight: 1.5,
  overflowWrap: "anywhere",
  backgroundColor: mine
    ? alpha(
        theme.palette.primary.main,
        theme.palette.mode === "dark" ? 0.3 : 0.12,
      )
    : alpha(theme.palette.text.primary, 0.06),
  "& p": { margin: 0 },
  "& p + p": { marginTop: "0.4em" },
  "& pre": { whiteSpace: "pre-wrap" },
});

export const composerSx = (theme: Theme, error = false) => ({
  display: "flex",
  alignItems: "flex-end",
  gap: "0.25rem",
  padding: "0.375rem 0.375rem 0.375rem 0.875rem",
  borderRadius: "1.25rem",
  border: `1px solid ${
    error ? theme.palette.error.main : theme.palette.divider
  }`,
  backgroundColor: theme.palette.background.paper,
  transition: "border-color 150ms, box-shadow 150ms",
  "&:focus-within": {
    borderColor: theme.palette.primary.main,
    boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.15)}`,
  },
});

export const sendButtonSx = (theme: Theme) => ({
  flexShrink: 0,
  width: 32,
  height: 32,
  color: theme.palette.primary.contrastText,
  backgroundColor: theme.palette.primary.main,
  "&:hover": { backgroundColor: theme.palette.primary.dark },
  "&.Mui-disabled": {
    color: theme.palette.text.disabled,
    backgroundColor: alpha(theme.palette.text.primary, 0.08),
  },
});

export const pillTabsSx = (theme: Theme) => {
  const dark = theme.palette.mode === "dark";
  return {
    minHeight: 0,
    minWidth: 0,
    "& .MuiTabs-indicator": { display: "none" },
    "& .MuiTabs-list": { gap: "0.25rem" },
    "& .MuiTab-root": {
      minHeight: 28,
      minWidth: 0,
      padding: "0 0.75rem",
      borderRadius: "999px",
      fontSize: "0.8rem",
      fontWeight: 500,
      textTransform: "none",
      color: theme.palette.text.secondary,
      transition: "background-color 150ms, color 150ms",
      "&:hover": {
        color: theme.palette.text.primary,
        backgroundColor: alpha(theme.palette.text.primary, 0.06),
      },
    },
    "& .MuiTab-root.Mui-selected": {
      fontWeight: 600,
      color: dark ? theme.palette.text.primary : theme.palette.primary.main,
      backgroundColor: alpha(theme.palette.primary.main, dark ? 0.3 : 0.12),
    },
  };
};
