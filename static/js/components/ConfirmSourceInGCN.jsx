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

import * as SourceInGcnAction from "../ducks/confirmedsourcesingcn";

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

const ConfirmSourceInGCN = ({
  dateobs,
  localization_name,
  localization_cumprob,
  source_id,
  start_date,
  end_date,
  sources_id_list,
}) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const { permissions } = useSelector((state) => state.profile);
  const [open, setOpen] = useState(false);

  const sourcesingcn = useSelector((state) => state.sourcesingcn.sourcesingcn);

  const handleClose = () => {
    setOpen(false);
  };

  let currentState = "unknown";
  if (
    sourcesingcn?.length > 0 &&
    sourcesingcn.filter((s) => s.obj_id === source_id).length !== 0
  ) {
    if (
      sourcesingcn.filter((s) => s.obj_id === source_id)[0]?.confirmed === true
    ) {
      currentState = "confirmed";
    } else if (
      sourcesingcn.filter((s) => s.obj_id === source_id)[0].confirmed === false
    ) {
      currentState = "rejected";
    }
  }

  const handleUpdate = () => {
    dispatch(
      SourceInGcnAction.fetchSourcesInGcn(dateobs, {
        localizationName: localization_name,
        sourcesIdList: sources_id_list,
      })
    );
  };

  const handleConfirm = () => {
    if (currentState === "unknown") {
      dispatch(
        SourceInGcnAction.submitSourceInGcn(dateobs, {
          source_id,
          start_date,
          end_date,
          localization_name,
          localization_cumprob,
          confirmed: true,
        })
      ).then((response) => {
        if (response.status === "success") {
          handleUpdate();
          handleClose();
        }
      });
    } else if (currentState === "rejected") {
      dispatch(
        SourceInGcnAction.patchSourceInGcn(dateobs, source_id, {
          confirmed: true,
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
    if (currentState === "unknown") {
      dispatch(
        SourceInGcnAction.submitSourceInGcn(dateobs, {
          source_id,
          start_date,
          end_date,
          localization_name,
          localization_cumprob,
          confirmed: false,
        })
      ).then((response) => {
        if (response.status === "success") {
          handleUpdate();
          handleClose();
        }
      });
    } else if (currentState === "confirmed") {
      dispatch(
        SourceInGcnAction.patchSourceInGcn(dateobs, source_id, {
          confirmed: false,
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
      dispatch(SourceInGcnAction.deleteSourceInGcn(dateobs, source_id)).then(
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
              Confirm/Reject Source {source_id} in GCN {dateobs}
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

ConfirmSourceInGCN.propTypes = {
  dateobs: PropTypes.string.isRequired,
  localization_name: PropTypes.string.isRequired,
  source_id: PropTypes.string.isRequired,
  start_date: PropTypes.string.isRequired,
  end_date: PropTypes.string.isRequired,
  localization_cumprob: PropTypes.string.isRequired,
  sources_id_list: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default ConfirmSourceInGCN;
