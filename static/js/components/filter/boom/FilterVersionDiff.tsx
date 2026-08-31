import { useMemo, useState } from "react";
import { makeStyles } from "tss-react/mui";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import { diffJson, diffLines } from "diff";

const useStyles = makeStyles()((theme) => ({
  controls: {
    display: "flex",
    alignItems: "center",
    gap: "1rem",
    flexWrap: "wrap",
    marginBottom: "1rem",
  },
  select: {
    minWidth: "16rem",
  },
  diff: {
    fontFamily: "monospace",
    fontSize: "0.8rem",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    border: `1px solid ${theme.palette.divider}`,
    borderRadius: theme.shape.borderRadius,
    maxHeight: "60vh",
    overflowY: "auto",
  },
  line: {
    display: "flex",
    gap: "0.5rem",
    padding: "0 0.5rem",
  },
  marker: {
    userSelect: "none",
    opacity: 0.6,
    width: "1ch",
  },
  added: {
    backgroundColor:
      theme.palette.mode === "dark" ? "rgba(46,160,67,0.3)" : "#e6ffec",
  },
  removed: {
    backgroundColor:
      theme.palette.mode === "dark" ? "rgba(248,81,73,0.3)" : "#ffebe9",
  },
}));

const parse = (pipeline: any) => {
  try {
    return JSON.parse(pipeline);
  } catch {
    return null;
  }
};

/** Diff two versions' pipelines into rendered rows, one per line. */
const diffPipelines = (before: any, after: any) => {
  const [a, b] = [parse(before), parse(after)];
  // diffJson normalizes key order, so a re-save that only reshuffles keys
  // reads as unchanged. Unparseable pipelines fall back to a plain text diff.
  const asText = (pipeline: any, parsed: any) =>
    parsed ? JSON.stringify(parsed, null, 2) : String(pipeline ?? "");
  const parts =
    a && b ? diffJson(a, b) : diffLines(asText(before, a), asText(after, b));
  return parts.flatMap((part) => {
    const marker = part.added ? "+" : part.removed ? "-" : " ";
    return part.value
      .replace(/\n$/, "")
      .split("\n")
      .map((text) => ({ marker, text }));
  });
};

interface FilterVersionDiffProps {
  versions: any[];
  activeFid?: string;
  // Per-fid BOOM validation verdicts, from the filter's altdata.
  validations?: Record<string, { passed?: boolean; message?: string }>;
}

const FilterVersionDiff = ({
  versions,
  activeFid,
  validations,
}: FilterVersionDiffProps) => {
  const { classes, cx } = useStyles();
  const [open, setOpen] = useState(false);

  // Newest first, so the two defaults are the most recent pair.
  const ordered = useMemo(
    () =>
      [...(versions || [])].sort((a, b) =>
        String(b.created_at || "").localeCompare(String(a.created_at || "")),
      ),
    [versions],
  );
  const defaultTo = activeFid || ordered[0]?.fid || "";
  const defaultFrom =
    ordered.find((v) => v.fid !== defaultTo)?.fid ?? defaultTo;
  const [fromFid, setFromFid] = useState<string | null>(null);
  const [toFid, setToFid] = useState<string | null>(null);
  const from = fromFid ?? defaultFrom;
  const to = toFid ?? defaultTo;

  const rows = useMemo(() => {
    const pipeline = (fid: string) =>
      ordered.find((v) => v.fid === fid)?.pipeline;
    return diffPipelines(pipeline(from), pipeline(to));
  }, [ordered, from, to]);

  const changed = rows.filter((row) => row.marker !== " ").length;

  const label = (version: any) => {
    const verdict = validations?.[version.fid];
    const stamp = version?.created_at?.toString().slice(0, 19);
    const state =
      verdict?.passed === true
        ? " — validated"
        : verdict?.passed === false
          ? " — failed validation"
          : "";
    return `${version.fid}: ${stamp}${
      version.fid === activeFid ? " (active)" : ""
    }${state}`;
  };

  if (ordered.length < 2) return null;

  return (
    <>
      <Button
        variant="outlined"
        color="primary"
        startIcon={<CompareArrowsIcon />}
        onClick={() => setOpen(true)}
        data-testid="compareFilterVersions"
      >
        Compare versions
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Compare filter versions</DialogTitle>
        <DialogContent>
          <Box className={classes.controls}>
            <FormControl className={classes.select}>
              <InputLabel id="diff-from-label">From</InputLabel>
              <Select
                labelId="diff-from-label"
                value={from}
                onChange={(e) => setFromFid(e.target.value as string)}
                data-testid="diffFromVersion"
              >
                {ordered.map((version) => (
                  <MenuItem key={version.fid} value={version.fid}>
                    {label(version)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl className={classes.select}>
              <InputLabel id="diff-to-label">To</InputLabel>
              <Select
                labelId="diff-to-label"
                value={to}
                onChange={(e) => setToFid(e.target.value as string)}
                data-testid="diffToVersion"
              >
                {ordered.map((version) => (
                  <MenuItem key={version.fid} value={version.fid}>
                    {label(version)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Chip
              size="small"
              label={
                changed === 0
                  ? "Identical"
                  : `${changed} changed line${changed > 1 ? "s" : ""}`
              }
              color={changed === 0 ? "default" : "primary"}
            />
          </Box>
          {validations?.[to]?.message && (
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {`Validation of ${to}: ${validations[to].message}`}
            </Typography>
          )}
          <Box className={classes.diff} data-testid="filterVersionDiff">
            {rows.map((row, index) => (
              <div
                // Lines repeat, so the index is the only stable key here.
                key={`${index}-${row.marker}`}
                className={cx(classes.line, {
                  [classes.added]: row.marker === "+",
                  [classes.removed]: row.marker === "-",
                })}
              >
                <span className={classes.marker}>{row.marker}</span>
                <span>{row.text}</span>
              </div>
            ))}
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default FilterVersionDiff;
