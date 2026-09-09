import { useEffect, useState } from "react";

import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Tooltip from "@mui/material/Tooltip";
import { alpha } from "@mui/material/styles";

import InfoIcon from "@mui/icons-material/InfoOutlined";
import ErrorIcon from "@mui/icons-material/ErrorOutlineOutlined";
import WarningIcon from "@mui/icons-material/WarningAmberOutlined";
import SuccessIcon from "@mui/icons-material/CheckCircleOutlineOutlined";
import CloseIcon from "@mui/icons-material/Close";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweepOutlined";

import HeaderPanel, { PanelEmptyState } from "./HeaderPanel";
import { useAppSelector } from "../types/hooks";

interface Note {
  id?: string | number;
  note?: string;
  type?: string;
}

type Severity = "error" | "warning" | "success";

const severityOf = (type?: string): Severity =>
  type === "error" ? "error" : type === "warning" ? "warning" : "success";

const severityIcon = {
  error: <ErrorIcon />,
  warning: <WarningIcon />,
  success: <SuccessIcon />,
};

const Notes = () => {
  const [notes, setNotes] = useState<Note[]>([]);
  const NotesState = useAppSelector(
    (state) => (state as any).notifications.notes,
  ) as Note[];
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
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

  const close = () => setAnchorEl(null);

  const deleteAllNotes = () => {
    setNotes([]);
    close();
  };

  const deleteNote = (indexToDel: number, nbNoteToDel: number) => {
    if (nbNoteToDel + 1 === notes.length) return deleteAllNotes();
    const firstDuplication = indexToDel - nbNoteToDel;
    setNotes(
      notes.filter(
        (_, index) => index > indexToDel || index < firstDuplication,
      ),
    );
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
          onClick={(event) => setAnchorEl(open ? null : event.currentTarget)}
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
      <HeaderPanel
        anchorEl={anchorEl}
        onClose={close}
        title="Alerts"
        actions={
          notes.length > 0 && (
            <Tooltip title="Delete all">
              <IconButton size="small" onClick={deleteAllNotes}>
                <DeleteSweepIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )
        }
      >
        {notes.length === 0 ? (
          <PanelEmptyState icon={<InfoIcon />} text="No alerts" />
        ) : (
          <List disablePadding>
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
      </HeaderPanel>
    </>
  );
};

export default Notes;
