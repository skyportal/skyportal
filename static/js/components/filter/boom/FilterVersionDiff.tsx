import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import { diffJson, diffLines } from "diff";

const parse = (pipeline: any) => {
  try {
    return JSON.parse(pipeline);
  } catch {
    return null;
  }
};

const diffPipelines = (before: any, after: any) => {
  const [a, b] = [parse(before), parse(after)];
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
  validations?: Record<
    string,
    { passed?: boolean; message?: string; pending?: boolean }
  >;
}

const FilterVersionDiff = ({
  versions,
  activeFid,
  validations,
}: FilterVersionDiffProps) => {
  const [open, setOpen] = useState(false);

  const ordered = useMemo(
    () =>
      [...versions].sort((a, b) =>
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

  if (ordered.length < 2) return null;

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<CompareArrowsIcon />}
        onClick={() => setOpen(true)}
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
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              flexWrap: "wrap",
              mb: 2,
            }}
          >
            {(
              [
                ["From", from, setFromFid],
                ["To", to, setToFid],
              ] as const
            ).map(([selectLabel, value, setValue]) => (
              <TextField
                key={selectLabel}
                select
                label={selectLabel}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                sx={{ minWidth: "16rem" }}
              >
                {ordered.map((version) => {
                  const verdict = validations?.[version.fid];
                  const state = verdict?.pending
                    ? ", validating"
                    : verdict?.passed === true
                      ? ", validated"
                      : verdict?.passed === false
                        ? ", failed validation"
                        : "";
                  return (
                    <MenuItem key={version.fid} value={version.fid}>
                      {`${version.fid}: ${version.created_at?.toString().slice(0, 19)}${
                        version.fid === activeFid ? " (active)" : ""
                      }${state}`}
                    </MenuItem>
                  );
                })}
              </TextField>
            ))}
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
          <Box
            sx={{
              fontFamily: "monospace",
              fontSize: "0.8rem",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              maxHeight: "60vh",
              overflowY: "auto",
            }}
          >
            {rows.map((row, index) => (
              <Box
                key={`${index}-${row.marker}`}
                sx={(theme) => {
                  const dark = theme.palette.mode === "dark";
                  return {
                    display: "flex",
                    gap: 1,
                    px: 1,
                    ...(row.marker === "+" && {
                      bgcolor: dark ? "rgba(46,160,67,0.3)" : "#e6ffec",
                    }),
                    ...(row.marker === "-" && {
                      bgcolor: dark ? "rgba(248,81,73,0.3)" : "#ffebe9",
                    }),
                  };
                }}
              >
                <Box
                  component="span"
                  sx={{ userSelect: "none", opacity: 0.6, width: "1ch" }}
                >
                  {row.marker}
                </Box>
                <span>{row.text}</span>
              </Box>
            ))}
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default FilterVersionDiff;
