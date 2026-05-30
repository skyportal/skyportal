import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { withStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import DeleteIcon from "@mui/icons-material/Delete";

import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Close from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import { grey } from "@mui/material/colors";
import { GridToolbarContainer, GridToolbarQuickFilter } from "@mui/x-data-grid";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import StyledDataGrid from "./StyledDataGrid";

import * as Actions from "../ducks/reminders";

dayjs.extend(utc);

const dialogTitleStyles = (theme) => ({
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(
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
  dialogTitleStyles,
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

  // Memoized so the toolbar (the "new reminder" button and quick-filter search
  // box) keeps a stable identity across the re-render that happens when the
  // reminders list loads; otherwise MUI remounts it and any element reference a
  // test is interacting with goes stale. Must be declared before the early
  // returns below so the hook runs on every render (rules-of-hooks).
  const CustomToolbar = useMemo(
    () =>
      function RemindersToolbar() {
        return (
          <GridToolbarContainer>
            <IconButton
              name={`new_reminder_${resourceId}`}
              onClick={() => setOpen(true)}
            >
              <AddIcon />
            </IconButton>
            <div data-testid="reminders-quick-filter">
              <GridToolbarQuickFilter />
            </div>
          </GridToolbarContainer>
        );
      },

    [resourceId],
  );

  if (!resourceType || !resourceId) return <CircularProgress />;
  if (
    !reminders ||
    reminders.resourceType !== resourceType ||
    reminders.resourceId !== resourceId
  )
    return null;

  const deleteReminder = (reminderId) => {
    dispatch(Actions.deleteReminder(resourceId, resourceType, reminderId)).then(
      (response) => {
        if (response.status === "success") {
          dispatch(showNotification("Reminder deleted"));
          dispatch(Actions.fetchReminders(resourceId, resourceType));
        } else {
          dispatch(showNotification("Error deleting reminder", "error"));
        }
      },
    );
  };

  const columns = [
    { field: "text", headerName: "Text", flex: 1, minWidth: 160 },
    {
      field: "next_reminder",
      headerName: "Next Reminder (UTC)",
      flex: 1,
      minWidth: 180,
    },
    {
      field: "number_of_reminders",
      headerName: "Number of Reminders",
      flex: 1,
      minWidth: 160,
    },
    {
      field: "reminder_delay",
      headerName: "Reminder Delay",
      flex: 1,
      minWidth: 140,
    },
    {
      field: "delete",
      headerName: "",
      width: 70,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Button onClick={() => deleteReminder(params.row.id)}>
          <DeleteIcon />
        </Button>
      ),
    },
  ];

  return (
    <div data-testid="reminders-table">
      <Typography variant="h6">Reminders</Typography>
      <Box sx={{ width: "100%" }}>
        <StyledDataGrid
          autoHeight
          rows={remindersList}
          columns={columns}
          getRowId={(row) => row.id}
          initialState={{
            pagination: { paginationModel: { pageSize: 5 } },
          }}
          pageSizeOptions={[2, 5, 10]}
          slots={{ toolbar: CustomToolbar }}
          showToolbar
        />
      </Box>
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
