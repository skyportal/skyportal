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

import { showNotification } from "baselayer/components/Notifications";

import * as Actions from "../ducks/reminders";

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
    <MuiDialogTitle disableTypography className={classes.root}>
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

const RemindersTable = ({ reminders, resourceId, resourceType }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const theme = useTheme();
  const [open, setOpen] = useState(false);

  const handleClose = () => {
    setOpen(false);
  };

  const renderReminderText = (dataIndex) => {
    const reminder = reminders[dataIndex];
    return reminder.text;
  };

  const renderNextReminder = (dataIndex) => {
    const reminder = reminders[dataIndex];
    return reminder.next_reminder;
  };

  const renderNbReminders = (dataIndex) => {
    const reminder = reminders[dataIndex];
    return reminder.number_of_reminders;
  };

  const renderReminderDelay = (dataIndex) => {
    const reminder = reminders[dataIndex];
    return reminder.reminder_delay;
  };

  const deleteReminder = (dataIndex) => {
    const reminder = reminders[dataIndex];
    dispatch(
      Actions.deleteReminder(resourceId, resourceType, reminder.id)
    ).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification("Reminder deleted"));
        dispatch(Actions.fetchReminders(resourceId, resourceType));
      } else {
        dispatch(showNotification("Error deleting reminder", "error"));
      }
    });
  };

  const columns = [
    {
      name: "text",
      label: "Text",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderReminderText,
      },
    },
    {
      name: "next_reminder",
      label: "Next Reminder",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderNextReminder,
      },
    },
    {
      name: "number_of_reminders",
      label: "Number of Reminders",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderNbReminders,
      },
    },
    {
      name: "reminder_delay",
      label: "Reminder Delay",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderReminderDelay,
      },
    },
    {
      name: "",
      options: {
        filter: false,
        sort: false,
        empty: true,
        customBodyRenderLite: (dataIndex) => (
          <div className={classes.buttons}>
            <Button
              className={classes.button}
              onClick={() => deleteReminder(dataIndex)}
            >
              <DeleteIcon className={classes.buttonIcon} />
            </Button>
          </div>
        ),
      },
    },
  ];

  const options = {
    search: true,
    selectableRows: "none",
    elevation: 0,
    rowsPerPage: 5,
    rowsPerPageOptions: [2, 5, 10],
    jumpToPage: true,
    pagination: true,
    download: false,
    print: false,
    filter: false,
    customToolbar: () => (
      <IconButton
        name={`new_reminder_${resourceId}`}
        onClick={() => {
          setOpen(true);
        }}
      >
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div>
      {reminders && resourceType && resourceId ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title="Reminders"
                data={reminders}
                options={options}
                columns={columns}
              />
            </ThemeProvider>
          </StyledEngineProvider>
          {open && (
            <Dialog
              open={open}
              onClose={handleClose}
              style={{ position: "fixed" }}
              maxWidth="md"
            >
              <DialogTitle onClose={handleClose}>
                New Reminder on {resourceType}
              </DialogTitle>
              <DialogContent dividers>
                <div className={classes.dialogContent}>
                  New Reminder Form - Not implemented yet
                </div>
              </DialogContent>
            </Dialog>
          )}
        </Paper>
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

RemindersTable.propTypes = {
  reminders: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      number_of_reminders: PropTypes.number,
      reminder_delay: PropTypes.number,
      next_reminder: PropTypes.string,
      text: PropTypes.string,
    })
  ),
  resourceId: PropTypes.string,
  resourceType: PropTypes.string,
};
RemindersTable.defaultProps = {
  reminders: null,
  resourceId: null,
  resourceType: null,
};

const Reminders = ({ resourceId, resourceType }) => {
  const dispatch = useDispatch();
  const reminders = useSelector((state) => state.reminders);

  useEffect(() => {
    if (
      resourceId !== reminders.resourceId ||
      resourceType !== reminders.resourceType ||
      reminders.remindersList.length === 0
    ) {
      dispatch(Actions.fetchReminders(resourceId, resourceType));
    }
  }, [resourceType, resourceId]);

  return (
    <div>
      {resourceType === reminders.resourceType &&
      resourceId === reminders.resourceId ? (
        <RemindersTable
          reminders={reminders.remindersList}
          resourceId={resourceId}
          resourceType={resourceType}
        />
      ) : null}
    </div>
  );
};

Reminders.propTypes = {
  resourceId: PropTypes.string,
  resourceType: PropTypes.string,
};
Reminders.defaultProps = {
  resourceId: null,
  resourceType: null,
};

export default Reminders;
