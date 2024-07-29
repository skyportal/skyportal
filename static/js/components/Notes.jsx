import React, { useEffect, useState } from "react";

import Badge from "@mui/material/Badge";
import InfoIcon from "@mui/icons-material/Info";
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
    paddingTop: "0.1em",
    width: "100%",
    maxWidth: 480,
    backgroundColor: theme.palette.background.paper,
  },
  centered: {
    display: "flex",
    justifyContent: "center",
  },
  note: {
    display: "flex",
    justifyContent: "space-between",
    color: "white",
    fontWeight: "bold",
    paddingTop: "0.8em",
    paddingBottom: "0.8em",
    paddingLeft: "1em",
    marginBottom: 5,
    width: "100%",
    WebkitBoxShadow: "0 0 5px black",
    MozBoxShadow: "0 0 5px black",
    boxShadow: "0 0 5px black",
  },
  duplicateNote: {
    position: "relative",
    borderBottom: "1px solid grey",
    top: "-5px",
    width: "100%",
    height: "3px",
  },
}));

const Notes = () => {
  const classes = useStyles();
  const [notes, setNotes] = useState([]);
  const NotesState = useSelector((state) => state.notifications.notes);
  const [anchorEl, setAnchorEl] = useState(null);

  const noteColor = {
    error: "Crimson",
    warning: "Orange",
    info: "MediumAquaMarine",
  };

  useEffect(() => {
    const uniqueNotes = new Set([...notes, ...NotesState]);
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

  const deleteNote = (idToDel) => {
    setNotes((prevNotes) => prevNotes.filter((note) => note.id !== idToDel));
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
          <List className={classes.root}>
            {notes &&
              notes.map((note, index) => (
                <div key={note.id}>
                  {index === 0 || notes[index - 1].note !== note.note ? (
                    <>
                      <div
                        className={classes.note}
                        style={{ background: noteColor[note.type] }}
                      >
                        <div>{note.note}</div>
                        <Button
                          data-testid={`deleteNoteButton${note.id}`}
                          size="small"
                          onClick={() => {
                            deleteNote(note.id);
                          }}
                        >
                          <CancelIcon style={{ color: "white" }} />
                        </Button>
                      </div>
                      <Divider />
                    </>
                  ) : (
                    <div
                      className={classes.duplicateNote}
                      style={{ background: noteColor[note.type] }}
                    ></div>
                  )}
                </div>
              ))}
            {notes && notes.length > 0 && (
              <div className={classes.centered}>
                <Button
                  onClick={deleteAllNotes}
                  data-testid="deleteAllNotesButton"
                >
                  Delete all
                </Button>
              </div>
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
