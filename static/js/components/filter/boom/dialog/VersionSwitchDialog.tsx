import { useMemo, useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";

import {
  changesLabel,
  countChanges,
  diffPipelines,
} from "../FilterVersionDiff";
import { ValidationChip, VersionId } from "../FilterVersionLabel";
import { formatVersionDate, shortFid, versionInfo } from "../filterVersions";

const VersionSummary = ({
  title,
  version,
  altdata,
  verdict,
}: {
  title: string;
  version: any;
  altdata: any;
  verdict?: any;
}) => {
  const { comment, created_by: author } = versionInfo(altdata, version.fid);

  return (
    <Paper variant="outlined" sx={{ p: 1.5 }}>
      <Typography variant="overline" color="text.secondary">
        {title}
      </Typography>
      <Stack
        direction="row"
        spacing={1}
        sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}
      >
        <VersionId fid={version.fid} />
        <ValidationChip verdict={verdict} showNone />
      </Stack>
      <Typography variant="body2" color="text.secondary">
        Saved {formatVersionDate(version.created_at)}
        {author ? ` by ${author}` : ""}
      </Typography>
      <Typography
        variant="body2"
        color={comment ? "text.primary" : "text.secondary"}
        sx={{
          mt: 1,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontStyle: comment ? "normal" : "italic",
        }}
      >
        {comment || "No comment"}
      </Typography>
    </Paper>
  );
};

interface VersionSwitchDialogProps {
  filter: any;
  toFid: string | null;
  verdictOf: (fid: string) => any;
  onCancel: () => void;
  onConfirm: (fid: string) => void;
}

const VersionSwitchDialog = ({
  filter,
  toFid,
  verdictOf,
  onCancel,
  onConfirm,
}: VersionSwitchDialogProps) => {
  const [openedFor, setOpenedFor] = useState(toFid);
  const [shown, setShown] = useState<{
    to: string;
    from: string;
    active: boolean;
  } | null>(null);
  if (toFid !== openedFor) {
    setOpenedFor(toFid);
    if (toFid)
      setShown({ to: toFid, from: filter.active_fid, active: !!filter.active });
  }
  const versions = filter.fv ?? [];
  const from = versions.find((v: any) => v.fid === shown?.from);
  const to = versions.find((v: any) => v.fid === shown?.to);
  const wasActive = !!shown?.active;
  const validated = !!to && !!verdictOf(to.fid)?.passed;
  const changed = useMemo(
    () =>
      from && to ? countChanges(diffPipelines(from.pipeline, to.pipeline)) : 0,
    [from, to],
  );

  return (
    <Dialog open={!!toFid} onClose={onCancel} maxWidth="sm" fullWidth>
      {to && (
        <>
          <DialogTitle>Change to version {shortFid(to.fid)}?</DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ mb: 2 }}>
              {validated
                ? `Version ${shortFid(to.fid)} replaces ${shortFid(shown?.from ?? "")} as the active version${
                    wasActive
                      ? " and runs on live alerts right away."
                      : ". The filter is off, so it runs once you turn it on."
                  }`
                : `Version ${shortFid(to.fid)} has not been validated yet: validate it before the filter can be activated.${
                    wasActive ? " The filter is turned off until then." : ""
                  }`}
            </DialogContentText>
            <Stack spacing={1}>
              {from && (
                <>
                  <VersionSummary
                    title="Current version"
                    version={from}
                    altdata={filter.altdata}
                    verdict={verdictOf(from.fid)}
                  />
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
                  >
                    <ArrowDownwardIcon fontSize="small" />
                    {changed === 0 ? "Same pipeline" : changesLabel(changed)}
                  </Typography>
                </>
              )}
              <VersionSummary
                title="New version"
                version={to}
                altdata={filter.altdata}
                verdict={verdictOf(to.fid)}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={onCancel}>Cancel</Button>
            <Button variant="contained" onClick={() => onConfirm(to.fid)}>
              Change version
            </Button>
          </DialogActions>
        </>
      )}
    </Dialog>
  );
};

export default VersionSwitchDialog;
