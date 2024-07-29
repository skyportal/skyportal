import React, { useEffect, useState } from "react";

import Badge from "@mui/material/Badge";
import InfoIcon from "@mui/icons-material/Info";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import makeStyles from "@mui/styles/makeStyles";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Divider from "@mui/material/Divider";
import ReactMarkdown from "react-markdown";
import Button from "./Button";
import { useSelector } from "react-redux";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: 360,
    backgroundColor: theme.palette.background.paper,
  },
  centered: {
    display: "flex",
    justifyContent: "center",
  },
}));

const Notes = () => {
  const classes = useStyles();
  const [notes, setNotes] = useState([]);
  const NotesState = useSelector((state) => state.notifications.notes);
  const [anchorEl, setAnchorEl] = useState(null);

  useEffect(() => {
    if (NotesState.length > 0) {
      setNotes((prevNotes) => [...prevNotes, ...NotesState]);
    }
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

  const deleteNote = (index) => {
    setNotes((prevNotes) => prevNotes.filter((_, i) => i !== index));
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
                <div key={index}>
                  <ListItem data-testid={`note_${index}`}>
                    <ReactMarkdown>{note.note}</ReactMarkdown>
                  </ListItem>
                  <ListItem className={classes.centered}>
                    <Button
                      data-testid={`deleteNoteButton${index}`}
                      size="small"
                      onClick={() => {
                        deleteNote(index);
                      }}
                    >
                      Delete
                    </Button>
                  </ListItem>
                  <Divider />
                </div>
              ))}
            {notes && notes.length > 0 && (
              <Button
                onClick={deleteAllNotes}
                data-testid="deleteAllNotesButton"
              >
                Delete all
              </Button>
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
