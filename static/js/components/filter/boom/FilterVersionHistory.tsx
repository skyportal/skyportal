import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography, { TypographyProps } from "@mui/material/Typography";
import Timeline from "@mui/lab/Timeline";
import TimelineConnector from "@mui/lab/TimelineConnector";
import TimelineContent from "@mui/lab/TimelineContent";
import TimelineDot from "@mui/lab/TimelineDot";
import TimelineItem from "@mui/lab/TimelineItem";
import TimelineOppositeContent, {
  timelineOppositeContentClasses,
} from "@mui/lab/TimelineOppositeContent";
import TimelineSeparator from "@mui/lab/TimelineSeparator";
import HistoryIcon from "@mui/icons-material/History";
import EditIcon from "@mui/icons-material/EditOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import PlayCircleIcon from "@mui/icons-material/PlayCircleOutlineOutlined";
import PauseCircleIcon from "@mui/icons-material/PauseCircleOutlineOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";

import { useUpdateBoomFilterFlagsMutation } from "../../../ducks/boom_filter";
import {
  DiffLines,
  changesLabel,
  countChanges,
  diffPipelines,
} from "./FilterVersionDiff";
import { ValidationChip, VersionId } from "./FilterVersionLabel";
import {
  formatVersionDate,
  newestFirst,
  shortFid,
  toTimestamp,
  versionInfo,
} from "./filterVersions";

const Caption = (props: TypographyProps) => (
  <Typography
    variant="caption"
    color="text.secondary"
    component="div"
    {...props}
  />
);

const When = ({ value }: { value: any }) => (
  <TimelineOppositeContent sx={{ pt: 1.5 }}>
    <Typography variant="body2" sx={{ fontWeight: 500 }}>
      {formatVersionDate(value, "MMM D, YYYY")}
    </Typography>
    <Caption component="span">{formatVersionDate(value, "HH:mm:ss")}</Caption>
  </TimelineOppositeContent>
);

const VersionComment = ({
  filterId,
  fid,
  comment,
  onSaved,
}: {
  filterId: number;
  fid: string;
  comment?: string;
  onSaved: () => any;
}) => {
  const [updateFlags, { isLoading }] = useUpdateBoomFilterFlagsMutation();
  const [draft, setDraft] = useState<string | null>(null);

  const save = async () => {
    const result = await updateFlags({
      filter_id: filterId,
      fid,
      comment: draft?.trim() || null,
    });
    if ("error" in result) return;
    await onSaved();
    setDraft(null);
  };

  if (draft !== null) {
    return (
      <Box sx={{ mt: 1 }}>
        <TextField
          autoFocus
          multiline
          fullWidth
          size="small"
          minRows={2}
          placeholder="What changed and why?"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) save();
            if (e.key === "Escape") {
              e.stopPropagation();
              setDraft(null);
            }
          }}
        />
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          <Button
            size="small"
            variant="contained"
            onClick={save}
            disabled={isLoading}
          >
            Save
          </Button>
          <Button size="small" onClick={() => setDraft(null)}>
            Cancel
          </Button>
        </Stack>
      </Box>
    );
  }
  if (!comment) {
    return (
      <Link
        component="button"
        variant="body2"
        onClick={() => setDraft("")}
        sx={{ display: "block", textAlign: "left", mt: 0.5 }}
      >
        Add a comment
      </Link>
    );
  }
  return (
    <Box sx={{ mt: 1, display: "flex", alignItems: "flex-start", gap: 0.5 }}>
      <Typography
        variant="body2"
        sx={{
          flexGrow: 1,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          borderLeft: 3,
          borderColor: "divider",
          pl: 1,
        }}
      >
        {comment}
      </Typography>
      <Tooltip title="Edit comment">
        <IconButton size="small" onClick={() => setDraft(comment)}>
          <EditIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    </Box>
  );
};

const VersionChanges = ({
  version,
  previous,
}: {
  version: any;
  previous?: any;
}) => {
  const [open, setOpen] = useState(false);
  const rows = useMemo(
    () =>
      open && previous
        ? diffPipelines(previous.pipeline, version.pipeline)
        : null,
    [open, previous, version],
  );
  const changed = rows && countChanges(rows);

  if (!previous) return <Caption sx={{ mt: 0.5 }}>First version</Caption>;
  if (previous.pipeline === version.pipeline || changed === 0) {
    return (
      <Caption sx={{ mt: 0.5 }}>
        Same pipeline as {shortFid(previous.fid)}
      </Caption>
    );
  }
  return (
    <>
      <Link
        component="button"
        variant="body2"
        onClick={() => setOpen(!open)}
        sx={{
          display: "inline-flex",
          alignItems: "center",
          textAlign: "left",
          mt: 0.5,
        }}
      >
        {`${changed == null ? "Changes" : changesLabel(changed)} since ${shortFid(previous.fid)}`}
        {open ? (
          <ExpandLessIcon fontSize="small" />
        ) : (
          <ExpandMoreIcon fontSize="small" />
        )}
      </Link>
      <Collapse in={open} unmountOnExit>
        <Box sx={{ mt: 1 }}>
          <DiffLines rows={rows ?? []} />
        </Box>
      </Collapse>
    </>
  );
};

const VersionItem = ({
  filter,
  version,
  previous,
  isLast,
  onChange,
}: {
  filter: any;
  version: any;
  previous?: any;
  isLast: boolean;
  onChange: () => any;
}) => {
  const { comment, created_by: author } = versionInfo(
    filter.altdata,
    version.fid,
  );
  const isActiveVersion = version.fid === filter.active_fid;
  const live = isActiveVersion && !!filter.active;

  return (
    <TimelineItem>
      <When value={version.created_at} />
      <TimelineSeparator>
        <TimelineDot
          color={isActiveVersion ? "primary" : "grey"}
          variant={live ? "filled" : "outlined"}
        />
        {!isLast && <TimelineConnector />}
      </TimelineSeparator>
      <TimelineContent sx={{ pb: 3, minWidth: 0 }}>
        <Stack
          direction="row"
          spacing={1}
          sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
        >
          <VersionId fid={version.fid} />
          {isActiveVersion && (
            <Chip
              size="small"
              color="primary"
              variant={live ? "filled" : "outlined"}
              label={live ? "Active" : "Active version, filter off"}
            />
          )}
          <ValidationChip
            verdict={filter.altdata?.boom?.validations?.[version.fid]}
          />
          {author && <Caption>by {author}</Caption>}
        </Stack>
        <VersionComment
          filterId={filter.id}
          fid={version.fid}
          comment={comment}
          onSaved={onChange}
        />
        <VersionChanges version={version} previous={previous} />
      </TimelineContent>
    </TimelineItem>
  );
};

const ActivationItem = ({ event, isLast }: { event: any; isLast: boolean }) => (
  <TimelineItem>
    <When value={event.at} />
    <TimelineSeparator>
      <TimelineDot
        variant="outlined"
        color={event.active ? "success" : "grey"}
        sx={{ p: 0.25 }}
      >
        {event.active ? (
          <PlayCircleIcon sx={{ fontSize: 16 }} />
        ) : event.switched ? (
          <SwapHorizIcon sx={{ fontSize: 16 }} />
        ) : (
          <PauseCircleIcon sx={{ fontSize: 16 }} />
        )}
      </TimelineDot>
      {!isLast && <TimelineConnector />}
    </TimelineSeparator>
    <TimelineContent sx={{ pb: 3 }}>
      <Typography variant="body2" sx={{ pt: 1 }}>
        {event.switched
          ? "Switched to "
          : event.active
            ? "Activated "
            : "Turned off "}
        <VersionId fid={event.fid} />
        {event.switched && (event.active ? ", filter on" : ", filter off")}
      </Typography>
      <Caption>by {event.by}</Caption>
    </TimelineContent>
  </TimelineItem>
);

const FilterVersionHistory = ({
  filter,
  onChange,
}: {
  filter: any;
  onChange: () => any;
}) => {
  const [open, setOpen] = useState(false);
  const items = useMemo(() => {
    const ordered = newestFirst(filter.fv ?? []);
    return [
      ...ordered.map((version, index) => ({
        key: version.fid,
        time: toTimestamp(version.created_at),
        version,
        previous: ordered[index + 1],
      })),
      ...(filter.altdata?.boom?.activations ?? []).map((event: any) => ({
        key: `${event.at}-${event.fid}`,
        time: toTimestamp(event.at),
        event,
      })),
    ].sort((a, b) => b.time - a.time);
  }, [filter.fv, filter.altdata]);

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<HistoryIcon />}
        onClick={() => setOpen(true)}
      >
        History
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Version history of {filter.name}</DialogTitle>
        <DialogContent>
          <Timeline
            sx={{
              p: 0,
              m: 0,
              [`& .${timelineOppositeContentClasses.root}`]: {
                flex: { xs: 0.35, md: 0.2 },
              },
            }}
          >
            {items.map((item, index) =>
              item.event ? (
                <ActivationItem
                  key={item.key}
                  event={item.event}
                  isLast={index === items.length - 1}
                />
              ) : (
                <VersionItem
                  key={item.key}
                  filter={filter}
                  version={item.version}
                  previous={item.previous}
                  isLast={index === items.length - 1}
                  onChange={onChange}
                />
              ),
            )}
          </Timeline>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default FilterVersionHistory;
