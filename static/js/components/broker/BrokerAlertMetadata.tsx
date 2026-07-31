import { useState } from "react";

import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

const useStyles = makeStyles()((theme) => ({
  root: { marginTop: theme.spacing(1) },
  chips: {
    display: "flex",
    gap: theme.spacing(0.5),
    flexWrap: "wrap",
    alignItems: "center",
  },
  toggle: { marginTop: theme.spacing(0.5), padding: 0, minWidth: 0 },
  table: { maxHeight: "16rem", overflow: "auto" },
  key: {
    fontFamily: "monospace",
    fontSize: "0.75rem",
    padding: "1px 8px 1px 0",
    whiteSpace: "nowrap",
    borderBottom: "none",
    color: theme.palette.text.secondary,
    width: "45%",
  },
  value: {
    fontFamily: "monospace",
    fontSize: "0.75rem",
    padding: "1px 0",
    wordBreak: "break-word",
    borderBottom: "none",
  },
}));

// ML scores fritz's alerts page surfaced as their own columns. `drb` lives on
// the candidate (`reliability` for LSST); the rest sit under `classifications`.
const ML_SCORE_KEYS = [
  "braai",
  "acai_h",
  "acai_n",
  "acai_o",
  "acai_v",
  "acai_b",
  "btsbot",
];

// Shown first in the field table; the rest follow alphabetically.
const PRIORITY_FIELDS = [
  "jd",
  "ra",
  "dec",
  "band",
  "fid",
  "magpsf",
  "sigmapsf",
  "diffmaglim",
  "isdiffpos",
  "drb",
  "reliability",
  "snr_psf",
  "programid",
];

const flatten = (entry: Record<string, any>) => {
  const flat: Record<string, any> = {};
  Object.entries(entry || {}).forEach(([k, v]) => {
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      Object.entries(v).forEach(([sk, sv]) => {
        flat[`${k}.${sk}`] = sv;
      });
    } else {
      flat[k] = v;
    }
  });
  return flat;
};

const fmt = (v: any) => {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  if (typeof v === "number" && !Number.isInteger(v)) return v.toFixed(5);
  return String(v);
};

const scoreColor = (v: number) => {
  if (v >= 0.8) return "success" as const;
  if (v >= 0.5) return "warning" as const;
  return "default" as const;
};

interface BrokerAlertMetadataProps {
  alert: any;
}

/**
 * Per-alert metadata for a broker alert: the ML scores fritz's alerts page
 * showed as columns, plus the full candidate document behind a toggle. Field
 * names are provider-specific, so everything past the known scores is rendered
 * generically from whatever the broker returned.
 */
const BrokerAlertMetadata = ({ alert }: BrokerAlertMetadataProps) => {
  const { classes } = useStyles();
  const [open, setOpen] = useState(false);

  if (!alert) return null;

  // Providers either nest the alert body under `candidate` (ZTF-style) or
  // return it flat; fall back to the alert itself so both render.
  const candidate = alert.candidate ?? alert;
  const classifications = alert.classifications ?? {};

  // Real-bogus score: `drb` (ZTF), `reliability` (LSST), `rb` (older ZTF).
  const scores: { key: string; value: number }[] = [];
  const rbKey = ["drb", "reliability", "rb"].find(
    (k) => typeof candidate[k] === "number",
  );
  if (rbKey) scores.push({ key: rbKey, value: candidate[rbKey] });
  ML_SCORE_KEYS.forEach((key) => {
    const value = classifications[key];
    if (typeof value === "number") scores.push({ key, value });
  });

  const flat = flatten(candidate);
  // `classifications` is a sibling of `candidate`, so fold it in to keep the
  // scores visible in the table too.
  Object.entries(flatten(classifications)).forEach(([k, v]) => {
    flat[`classifications.${k}`] = v;
  });
  const keys = Object.keys(flat).filter((k) => !k.startsWith("_"));
  const priority = PRIORITY_FIELDS.filter((k) => keys.includes(k));
  const rest = keys.filter((k) => !PRIORITY_FIELDS.includes(k)).sort();
  const ordered = [...priority, ...rest];

  if (!ordered.length) return null;

  return (
    <div className={classes.root}>
      <div className={classes.chips}>
        {scores.length > 0 ? (
          scores.map(({ key, value }) => (
            <Tooltip key={key} title={String(value)}>
              <Chip
                size="small"
                variant="outlined"
                color={scoreColor(value)}
                label={`${key} ${value.toFixed(3)}`}
              />
            </Tooltip>
          ))
        ) : (
          <Typography variant="caption" color="text.secondary">
            No ML scores in this alert
          </Typography>
        )}
      </div>
      <Button
        size="small"
        className={classes.toggle}
        onClick={() => setOpen(!open)}
      >
        {open ? "Hide metadata" : `Show metadata (${ordered.length})`}
      </Button>
      <Collapse in={open} unmountOnExit>
        <TableContainer className={classes.table}>
          <Table size="small">
            <TableBody>
              {ordered.map((k) => (
                <TableRow key={k}>
                  <TableCell className={classes.key}>{k}</TableCell>
                  <TableCell className={classes.value}>
                    {fmt(flat[k])}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Collapse>
    </div>
  );
};

export default BrokerAlertMetadata;
