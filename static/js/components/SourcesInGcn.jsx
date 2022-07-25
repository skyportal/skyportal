import React, { useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import Paper from "@mui/material/Paper";
import { withStyles, makeStyles } from "@mui/styles";
import Button from "@mui/material/Button";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import EditIcon from "@mui/icons-material/Edit";
import Close from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import grey from "@mui/material/colors/grey";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";

import * as SourceInGcnAction from "../ducks/sourcesingcn";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
  buttons: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  button: {
    maxWidth: "1.2rem",
  },
  buttonIcon: {
    maxWidth: "1.2rem",
  },
}));
const dialogTitleStyles = (theme) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  title: {
    marginRight: theme.spacing(2),
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(dialogTitleStyles)(
  ({ children, classes, onClose }) => (
    <MuiDialogTitle className={classes.root}>
      <Typography variant="h6" className={classes.title}>
        {children}
      </Typography>
      {onClose ? (
        <IconButton
          aria-label="close"
          className={classes.closeButton}
          onClick={onClose}
        >
          <Close />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  )
);

const SourcesInGCN = ({
  dateobs,
  localizationName,
  sourceId,
  startDate,
  endDate,
  localizationCumprob,
  sourcesIdList,
}) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const { permissions } = useSelector((state) => state.profile);
  const [open, setOpen] = useState(false);

  const sourcesingcn = useSelector((state) => state.sourcesingcn.sourcesingcn);

  const handleClose = () => {
    setOpen(false);
  };

  const findCurrentState = () => {
    let state = "pending";
    if (
      sourcesingcn.filter((s) => s.obj_id === sourceId).length !== 0 &&
      sourcesingcn?.length > 0
    ) {
      if (
        sourcesingcn.filter((s) => s.obj_id === sourceId)[0]
          ?.confirmed_or_rejected === true
      ) {
        state = "confirmed";
      } else if (
        sourcesingcn.filter((s) => s.obj_id === sourceId)[0]
          .confirmed_or_rejected === false
      ) {
        state = "rejected";
      }
    }
    return state;
  };

  const currentState = findCurrentState();

  const handleUpdate = () => {
    dispatch(
      SourceInGcnAction.fetchSourcesInGcn(dateobs, {
        localizationName,
        sourcesIdList,
      })
    );
  };

  const handleConfirm = () => {
    if (currentState === "pending") {
      dispatch(
        SourceInGcnAction.submitSourceInGcn(dateobs, {
          sourceId,
          startDate,
          endDate,
          localizationName,
          localizationCumprob,
          confirmedOrRejected: true,
        })
      ).then((response) => {
        if (response.status === "success") {
          handleUpdate();
          handleClose();
        }
      });
    } else if (currentState === "rejected") {
      dispatch(
        SourceInGcnAction.patchSourceInGcn(dateobs, sourceId, {
          startDate,
          endDate,
          confirmedOrRejected: true,
        })
      ).then((response) => {
        if (response.status === "success") {
          handleUpdate();
          handleClose();
        }
      });
    } else {
      dispatch(showNotification("Source already confirmed", "error"));
    }
  };

  const handleReject = () => {
    if (currentState === "pending") {
      dispatch(
        SourceInGcnAction.submitSourceInGcn(dateobs, {
          sourceId,
          startDate,
          endDate,
          localizationName,
          localizationCumprob,
          confirmedOrRejected: false,
        })
      ).then((response) => {
        if (response.status === "success") {
          handleUpdate();
          handleClose();
        }
      });
    } else if (currentState === "confirmed") {
      dispatch(
        SourceInGcnAction.patchSourceInGcn(dateobs, sourceId, {
          startDate,
          endDate,
          confirmedOrRejected: false,
        })
      ).then((response) => {
        if (response.status === "success") {
          handleUpdate();
          handleClose();
        }
      });
    } else {
      dispatch(showNotification("Source already rejected", "error"));
    }
  };

  const handleUndefined = () => {
    if (currentState === "confirmed" || currentState === "rejected") {
      dispatch(SourceInGcnAction.deleteSourceInGcn(dateobs, sourceId)).then(
        (response) => {
          if (response.status === "success") {
            handleUpdate();
            handleClose();
          }
        }
      );
    } else {
      dispatch(showNotification("Source already undefined", "error"));
    }
  };

  return permissions.includes("Manage GCNs") ? (
    <div>
      <IconButton
        aria-label="open"
        className={classes.closeButton}
        onClick={() => setOpen(true)}
      >
        <EditIcon />
      </IconButton>
      {open && (
        <Paper className={classes.container}>
          <Dialog
            open={open}
            onClose={handleClose}
            style={{ position: "fixed" }}
            maxWidth="md"
          >
            <DialogTitle onClose={handleClose}>
              Confirm/Reject Source in GCN
            </DialogTitle>
            <DialogContent dividers>
              <div className={classes.dialogContent}>
                <Button onClick={handleConfirm}>CONFIRM</Button>
                <Button onClick={handleReject}>REJECT</Button>
                <Button onClick={handleUndefined}>UNDEFINED</Button>
              </div>
            </DialogContent>
          </Dialog>
        </Paper>
      )}
    </div>
  ) : null;
};

SourcesInGCN.propTypes = {
  dateobs: PropTypes.string.isRequired,
  localizationName: PropTypes.string.isRequired,
  sourceId: PropTypes.string.isRequired,
  startDate: PropTypes.string.isRequired,
  endDate: PropTypes.string.isRequired,
  localizationCumprob: PropTypes.string.isRequired,
  sourcesIdList: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default SourcesInGCN;
