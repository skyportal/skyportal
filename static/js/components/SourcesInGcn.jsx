import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
  adaptV4Theme,
} from "@mui/material/styles";
import { withStyles, makeStyles } from "@mui/styles";
import CircularProgress from "@mui/material/CircularProgress";
import Button from "@mui/material/Button";
import DeleteIcon from "@mui/icons-material/Delete";
import MUIDataTable from "mui-datatables";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Close from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import grey from "@mui/material/colors/grey";

// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";
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

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme(
    adaptV4Theme({
      palette: theme.palette,
      overrides: {
        MUIDataTablePagination: {
          toolbar: {
            flexFlow: "row wrap",
            justifyContent: "flex-end",
            padding: "0.5rem 1rem 0",
            [theme.breakpoints.up("sm")]: {
              // Cancel out small screen styling and replace
              padding: "0px",
              paddingRight: "2px",
              flexFlow: "row nowrap",
            },
          },
          tableCellContainer: {
            padding: "1rem",
          },
          selectRoot: {
            marginRight: "0.5rem",
            [theme.breakpoints.up("sm")]: {
              marginLeft: "0",
              marginRight: "2rem",
            },
          },
        },
      },
    })
  );

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

const SourcesInGCN = ({ dateobs, localizationName, sourceId, startDate, endDate, currentState }) => {
  console.log("SourcesInGCN:", dateobs, localizationName, sourceId, startDate, endDate, currentState);
  const dispatch = useDispatch();
  const classes = useStyles();
  const [open, setOpen] = useState(false);

  const handleConfirm = () => {
    if (currentState === "pending") {
      dispatch(SourceInGcnAction.submitSourceInGcn(dateobs, {
        sourceId,
        startDate,
        endDate,
        localizationName,
        confirmedOrRejected: true,
      })
      );
      handleClose();
    } else if (currentState === "rejected") {
      dispatch(SourceInGcnAction.patchSourceInGcn(dateobs, sourceId, {
        startDate,
        endDate,
        localizationName,
        confirmedOrRejected: true,
      })
      );
      handleClose();
    } else {
      showNotification("Source already confirmed", "error");
    }
    
  }

  const handleReject = () => {
    if (currentState === "pending") {
      dispatch(SourceInGcnAction.submitSourceInGcn(dateobs, {
        sourceId,
        startDate,
        endDate,
        localizationName,
        confirmedOrRejected: false,
      })
      );
      handleClose();
    } else if (currentState === "confirmed") {
      dispatch(SourceInGcnAction.patchSourceInGcn(dateobs, sourceId, {
        startDate,
        endDate,
        localizationName,
        confirmedOrRejected: false,
      })
      );
      handleClose();
    } else {
      showNotification("Source already rejected", "error");
    }

  }

  const handleUndefined = () => {
    if (currentState === "pending" || currentState === "rejected") {
      dispatch(SourceInGcnAction.deleteSourceInGcn(dateobs, sourceId, {
        startDate,
        endDate,
        localizationName,
      })
      );
      handleClose();
    } else {
      showNotification("Source already undefined", "error");
    }
  }

  const handleClose = () => {
    setOpen(false);
  };

  return (
    <div>
        <Button
        variant="outlined"
        name="gcn_summary"
        onClick={() => setOpen(true)}
      >
        Summary
      </Button>
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
                        <Button
                         onClick={handleConfirm}
                        >
                           CONFIRM
                        </Button>
                        <Button
                          onClick={handleReject}
                        >
                            REJECT
                        </Button>
                        <Button
                          onClick={handleUndefined}
                          >
                            UNDEFINED
                        </Button>
                    </div>
                </DialogContent>
                </Dialog>
            </Paper>
          )}
    </div>
  );
};
SourcesInGCN.proptypes = {
    dateobs: PropTypes.string.isRequired,
    localizationName: PropTypes.string.isRequired,
    sourceId: PropTypes.string.isRequired,
    startDate: PropTypes.string.isRequired,
    endDate: PropTypes.string.isRequired,
};

export default SourcesInGCN;