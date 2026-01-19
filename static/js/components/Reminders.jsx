import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import { withStyles } from "@mui/styles";
import CircularProgress from "@mui/material/CircularProgress";
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

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";

import * as Actions from "../ducks/reminders";

dayjs.extend(utc);

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
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
  });

const dialogTitleStyles = (theme) => ({
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(dialogTitleStyles)(
  ({ children, classes, onClose }) => (
    <MuiDialogTitle component="div" className={classes.root}>
      <Typography variant="h6" className={classes.title}>
        {children}
      </Typography>
      {onClose && (
        <IconButton
          aria-label="close"
          className={classes.closeButton}
          onClick={onClose}
        >
          <Close />
        </IconButton>
      )}
    </MuiDialogTitle>
  ),
);

const NewReminder = ({ resourceId, resourceType, handleClose }) => {
  const dispatch = useDispatch();
  const defaultDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const handleSubmit = ({ formData }) => {
    formData.next_reminder = formData.next_reminder
      .replace("+00:00", "")
      .replace(".000Z", "");
    dispatch(Actions.submitReminder(resourceId, resourceType, formData)).then(
      (response) => {
        if (response.status === "success") {
          dispatch(showNotification("Reminder created"));
          handleClose();
        } else {
          dispatch(showNotification("Error creating reminder", "error"));
        }
      },
    );
  };

  function validate(formData, errors) {
    if (formData.text === "") {
      errors.text = "Reminder text is required";
    }
    if (dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ") > formData.next_reminder) {
      errors.next_reminder.addError("Next reminder date can't be in the past");
    }
    if (formData.number_of_reminders <= 0) {
      errors.number_of_reminders.addError(
        "Number of reminders must be greater than 0",
      );
    }
    if (formData.reminder_delay <= 0) {
      errors.reminder_delay.addError(
        "Reminder delay must be greater than 0 day",
      );
    }
    return errors;
  }

  const reminderFormSchema = {
    type: "object",
    properties: {
      text: {
        type: "string",
        title: "Text",
      },
      next_reminder: {
        type: "string",
        format: "date-time",
        title: "Date",
        default: defaultDate,
      },
      number_of_reminders: {
        type: "integer",
        title: "Number of reminders",
        default: 1,
      },
      reminder_delay: {
        type: "integer",
        title: "Delay between reminders (in days)",
        default: 1,
      },
    },
    required: [
      "text",
      "next_reminder",
      "number_of_reminders",
      "reminder_delay",
    ],
  };
  return (
    <Form
      schema={reminderFormSchema}
      validator={validator}
      id="reminder-form"
      onSubmit={handleSubmit}
      customValidate={validate}
      liveValidate
    />
  );
};

NewReminder.propTypes = {
  resourceId: PropTypes.string.isRequired,
  resourceType: PropTypes.string.isRequired,
  handleClose: PropTypes.func.isRequired,
};

const Reminders = ({ resourceId, resourceType }) => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const [open, setOpen] = useState(false);
  // for now, we'll just show the reminders of the current user.
  // in the future, we'll want to show all reminders for the resource
  // show the users in the reminders list (datatable)
  // and allow to choose users to add to the reminders to in the NewReminder dialog
  const currentUser = useSelector((state) => state.profile);
  const reminders = useSelector((state) => state.reminders);
  const remindersList = reminders.remindersList.filter(
    (r) => r.user_id === currentUser.id,
  );

  useEffect(() => {
    if (
      !reminders?.remindersList?.length ||
      resourceId !== reminders.resourceId ||
      resourceType !== reminders.resourceType
    ) {
      dispatch(Actions.fetchReminders(resourceId, resourceType));
    }
  }, [resourceType, resourceId]);

  if (!resourceType || !resourceId) return <CircularProgress />;
  if (
    !reminders ||
    reminders.resourceType !== resourceType ||
    reminders.resourceId !== resourceId
  )
    return null;

  const deleteReminder = (dataIndex) => {
    dispatch(
      Actions.deleteReminder(
        resourceId,
        resourceType,
        remindersList[dataIndex].id,
      ),
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
      },
    },
    {
      name: "next_reminder",
      label: "Next Reminder (UTC)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "number_of_reminders",
      label: "Number of Reminders",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "reminder_delay",
      label: "Reminder Delay",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "",
      options: {
        filter: false,
        sort: false,
        empty: true,
        customBodyRenderLite: (dataIndex) => (
          <Button onClick={() => deleteReminder(dataIndex)}>
            <DeleteIcon />
          </Button>
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
        onClick={() => setOpen(true)}
      >
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div data-testid="reminders-table">
      <StyledEngineProvider injectFirst>
        <ThemeProvider theme={getMuiTheme(theme)}>
          <MUIDataTable
            title="Reminders"
            data={remindersList}
            options={options}
            columns={columns}
          />
        </ThemeProvider>
      </StyledEngineProvider>
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle onClose={() => setOpen(false)}>
          New Reminder on {resourceType}
        </DialogTitle>
        <DialogContent dividers>
          <NewReminder
            resourceId={resourceId}
            resourceType={resourceType}
            handleClose={() => setOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

Reminders.propTypes = {
  resourceId: PropTypes.string,
  resourceType: PropTypes.string,
};

export default Reminders;
