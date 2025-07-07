import React, { useEffect, useState } from "react";

import Badge from "@mui/material/Badge";
import InfoIcon from "@mui/icons-material/InfoOutlined";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import makeStyles from "@mui/styles/makeStyles";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Divider from "@mui/material/Divider";
import CancelIcon from "@mui/icons-material/Close";
import Button from "./Button";
import { useSelector } from "react-redux";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: 480,
    backgroundColor: theme.palette.background.paper,
  },
  list: {
    padding: "0.3em",
  },
  centered: {
    display: "flex",
    justifyContent: "center",
  },
  note: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    color: "white",
    fontWeight: 500,
    padding: "0.5em 1em",
    marginBottom: "0.3em",
    width: "100%",
    borderRadius: "12px",
    WebkitBoxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
    MozBoxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
    fontSize: "0.95rem",
    columnGap: "1em",
  },
  duplicateNoteBadge: {
    "& .MuiBadge-badge": {
      color: theme.palette.primary.main,
      backgroundColor: theme.palette.primary.contrastText,
    },
  },
  cancelButton: {
    background: "transparent",
    color: "#ffffff",
    fontSize: "1.2rem",
    fontWeight: 400,
    padding: 0,
    lineHeight: 1,
  },
}));

const Notes = () => {
  const classes = useStyles();
  const [notes, setNotes] = useState([]);
  const NotesState = useSelector((state) => state.notifications.notes);
  const [anchorEl, setAnchorEl] = useState(null);
  let sameNoteCount = 0;

  const noteColor = {
    error: "rgba(244,67,54,0.95)",
    warning: "rgba(255,152,0,0.95)",
    info: "rgba(11,181,119,0.95)",
  };

  useEffect(() => {
    const uniqueNotes = new Set(
      [...notes, ...NotesState].filter(
        (note) => !note.note?.includes("No WebSocket connection"),
      ),
    );
    setNotes([...uniqueNotes]);
  }, [NotesState]);

  const handleClickOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const deleteAllNotes = () => {
    setNotes([]);
    handleClose();
  };

  const deleteNote = (indexToDel, nbNoteToDel) => {
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

  return (
    <>
      <IconButton
        onClick={handleClickOpen}
        data-testid="notesButton"
        size="large"
        style={{ padding: 0, margin: 0 }}
      >
        <Badge
          badgeContent={notes.length}
          overlap="circular"
          color={notes.length > 0 ? "secondary" : "primary"}
          data-testid="notesBadge"
        >
          <InfoIcon fontSize="large" color="primary" />
        </Badge>
      </IconButton>
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "center",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "center",
        }}
        disableScrollLock
      >
        <div className={classes.root}>
          <List className={classes.list}>
            {notes?.map((note, index) => {
              if (
                index + 1 === notes.length ||
                notes[index + 1].note !== note.note
              ) {
                const noteCount = sameNoteCount;
                sameNoteCount = 0;
                return (
                  <div key={note.id}>
                    <div
                      className={classes.note}
                      style={{ background: noteColor[note.type] }}
                    >
                      {note.note}
                      <div style={{ display: "flex", alignItems: "center" }}>
                        {noteCount > 0 && (
                          <Badge
                            badgeContent={noteCount + 1}
                            overlap="circular"
                            data-testid="notesBadge"
                            className={classes.duplicateNoteBadge}
                          />
                        )}
                      </div>
                      <Button
                        data-testid={`deleteNoteButton${note.id}`}
                        size="small"
                        onClick={() => {
                          deleteNote(index, noteCount);
                        }}
                      >
                        <CancelIcon className={classes.cancelButton} />
                      </Button>
                    </div>
                  </div>
                );
              } else {
                sameNoteCount++;
              }
            })}
            {notes && notes.length > 0 && (
              <>
                <Divider />
                <div className={classes.centered}>
                  <Button
                    onClick={deleteAllNotes}
                    data-testid="deleteAllNotesButton"
                  >
                    Delete all
                  </Button>
                </div>
              </>
            )}
            {(!notes || notes.length === 0) && (
              <ListItem className={classes.centered}>
                <em>No notes</em>
              </ListItem>
            )}
          </List>
        </div>
      </Popover>
    </>
  );
};

export default Notes;
