import { useEffect, useState } from "react";

import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Popper from "@mui/material/Popper";
import Paper from "@mui/material/Paper";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import InfoIcon from "@mui/icons-material/InfoOutlined";
import ErrorIcon from "@mui/icons-material/ErrorOutlineOutlined";
import WarningIcon from "@mui/icons-material/WarningAmberOutlined";
import SuccessIcon from "@mui/icons-material/CheckCircleOutlineOutlined";
import CloseIcon from "@mui/icons-material/Close";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweepOutlined";

import { useAppSelector } from "../types/hooks";

interface Note {
  id?: string | number;
  note?: string;
  type?: string;
}

type Severity = "error" | "warning" | "success";

const POPPER_MODIFIERS = [
  { name: "offset", options: { offset: [0, 8] } },
  { name: "preventOverflow", options: { padding: 8 } },
];

const severityOf = (type?: string): Severity =>
  type === "error" ? "error" : type === "warning" ? "warning" : "success";

const severityIcon = {
  error: <ErrorIcon />,
  warning: <WarningIcon />,
  success: <SuccessIcon />,
};

// TEMP: demo rows to eyeball the styling, remove before merging
const DEMO_NOTES: Note[] = [
  {
    id: "demo-1",
    note: "Source ZTF26aaaqrst saved to group ZTF Partnership",
    type: "info",
  },
  { id: "demo-2", note: "Classification submitted", type: "info" },
  { id: "demo-3", note: "Classification submitted", type: "info" },
  { id: "demo-4", note: "Classification submitted", type: "info" },
  {
    id: "demo-5",
    note: "Photometry upload partially failed: 3 of 128 points were rejected",
    type: "warning",
  },
  {
    id: "demo-6",
    note: "Error uploading spectrum: instrument Keck1/LRIS not found",
    type: "error",
  },
];

const Notes = () => {
  const [notes, setNotes] = useState<Note[]>(DEMO_NOTES);
  const NotesState = useAppSelector(
    (state) => (state as any).notifications.notes,
  ) as Note[];
  const [anchorEl, setAnchorEl] = useState<any>(null);
  const [seenCount, setSeenCount] = useState(0);
  const open = Boolean(anchorEl);
  const unseenCount = Math.max(0, notes.length - seenCount);

  useEffect(() => {
    const uniqueNotes = new Set(
      [...notes, ...NotesState].filter(
        (note) => !note.note?.includes("No WebSocket connection"),
      ),
    );
    setNotes([...uniqueNotes]);
  }, [NotesState]);

  useEffect(() => {
    if (open) setSeenCount(notes.length);
  }, [open, notes.length]);

  const handleClickOpen = (event: any) => {
    setAnchorEl(anchorEl ? null : event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };

  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") handleClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);
  const deleteAllNotes = () => {
    setNotes([]);
    handleClose();
  };

  const deleteNote = (indexToDel: number, nbNoteToDel: number) => {
    if (nbNoteToDel + 1 === notes.length) {
      handleClose();
      setNotes([]);
    } else {
      let firstDuplication = indexToDel - nbNoteToDel;
      setNotes(
        notes.filter(
          (_, index) => index > indexToDel || index < firstDuplication,
        ),
      );
    }
  };

  const groups: { note: Note; index: number; count: number }[] = [];
  for (const [index, note] of notes.entries()) {
    const previous = groups[groups.length - 1];
    if (previous && previous.note.note === note.note) {
      previous.count += 1;
      previous.index = index;
    } else {
      groups.push({ note, index, count: 0 });
    }
  }

  const worstSeverity: Severity = notes.some((note) => note.type === "error")
    ? "error"
    : notes.some((note) => note.type === "warning")
      ? "warning"
      : "success";

  return (
    <>
      <Tooltip title={open ? "" : "Alerts"}>
        <IconButton
          onClick={handleClickOpen}
          data-testid="notesButton"
          size="large"
          style={{ padding: 0, margin: 0 }}
        >
          <Badge
            badgeContent={unseenCount}
            overlap="circular"
            color={worstSeverity}
            data-testid="notesBadge"
          >
            <InfoIcon fontSize="large" color="primary" />
          </Badge>
        </IconButton>
      </Tooltip>
      <Popper
        open={open}
        anchorEl={anchorEl}
        placement="bottom"
        modifiers={POPPER_MODIFIERS}
        sx={{ zIndex: (theme) => theme.zIndex.modal }}
      >
        <ClickAwayListener onClickAway={handleClose}>
          <Paper
            elevation={8}
            sx={{
              borderRadius: 2,
              width: "26rem",
              maxWidth: "calc(100vw - 1rem)",
              overflow: "hidden",
            }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                px: 2,
                py: 1.25,
                bgcolor: "action.hover",
              }}
            >
              <Typography sx={{ fontWeight: 600 }}>Alerts</Typography>
              <Box sx={{ flexGrow: 1 }} />
              {notes.length > 0 && (
                <Tooltip title="Delete all">
                  <IconButton size="small" onClick={deleteAllNotes}>
                    <DeleteSweepIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
            <Divider />
            {notes.length === 0 ? (
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 1,
                  px: 3,
                  py: 4,
                }}
              >
                <InfoIcon sx={{ color: "text.disabled" }} />
                <Typography variant="body2" color="text.secondary">
                  No alerts
                </Typography>
              </Box>
            ) : (
              <List
                disablePadding
                sx={{ maxHeight: "60vh", overflowY: "auto" }}
              >
                {groups.map(({ note, index, count }, position) => {
                  const severity = severityOf(note.type);
                  return (
                    <ListItem
                      key={note.id}
                      divider={position < groups.length - 1}
                      sx={{
                        alignItems: "flex-start",
                        gap: 1.5,
                        px: 2,
                        py: 1.5,
                        borderLeft: 3,
                        borderLeftColor: `${severity}.main`,
                        bgcolor: (theme) =>
                          alpha(theme.palette[severity].main, 0.14),
                      }}
                    >
                      <Box
                        sx={{
                          flexShrink: 0,
                          display: "flex",
                          color: `${severity}.main`,
                          "& svg": { fontSize: "1.25rem" },
                        }}
                      >
                        {severityIcon[severity]}
                      </Box>
                      <Box
                        sx={{
                          flexGrow: 1,
                          minWidth: 0,
                          fontSize: "0.875rem",
                          lineHeight: 1.45,
                          overflowWrap: "anywhere",
                        }}
                      >
                        {note.note}
                      </Box>
                      {count > 0 && (
                        <Chip
                          label={`×${count + 1}`}
                          size="small"
                          data-testid="notesBadge"
                          sx={{
                            flexShrink: 0,
                            height: "1.25rem",
                            fontSize: "0.7rem",
                            fontWeight: 600,
                          }}
                        />
                      )}
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          data-testid={`deleteNoteButton${note.id}`}
                          onClick={() => deleteNote(index, count)}
                          sx={{ flexShrink: 0, mt: -0.5, mr: -0.5 }}
                        >
                          <CloseIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </ListItem>
                  );
                })}
              </List>
            )}
          </Paper>
        </ClickAwayListener>
      </Popper>
    </>
  );
};

export default Notes;
