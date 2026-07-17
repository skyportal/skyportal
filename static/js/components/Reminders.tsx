import { useGetProfileQuery, useIsReadOnly } from "../ducks/profile";
import { useMemo, useState } from "react";
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

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { skipToken } from "@reduxjs/toolkit/query";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../types/hooks";
import Button from "./Button";
import StyledDataGrid, { DataGridToolbar } from "./StyledDataGrid";

import {
  useGetRemindersQuery,
  useSubmitReminderMutation,
  useDeleteReminderMutation,
} from "../ducks/reminders";

dayjs.extend(utc);

const dialogTitleStyles = (theme: any) => ({
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(
  ({ children, classes, onClose }: any) => (
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
  dialogTitleStyles as any,
);

interface NewReminderProps {
  resourceId: string;
  resourceType: string;
  handleClose: (...a: any[]) => void;
  resourceStartDate?: Date;
}

const LEAD_TIME_UNIT_MAP: Record<string, dayjs.ManipulateType> = {
  minutes: "minute",
  hours: "hour",
  days: "day",
  weeks: "week",
};

const NewReminder = ({
  resourceId,
  resourceType,
  handleClose,
  resourceStartDate,
}: NewReminderProps) => {
  const dispatch = useAppDispatch();
  const [submitReminder] = useSubmitReminderMutation();
  const defaultDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const handleSubmit = async ({ formData }: { formData: any }) => {
    if (resourceStartDate) {
      const leadUnit = formData.lead_time_unit || "hours";
      formData.next_reminder = dayjs(resourceStartDate)
        .subtract(formData.lead_time, LEAD_TIME_UNIT_MAP[leadUnit])
        .utc()
        .format("YYYY-MM-DDTHH:mm:ss");
      delete formData.lead_time;
      delete formData.lead_time_unit;
    } else {
      formData.next_reminder = formData.next_reminder
        .replace("+00:00", "")
        .replace(".000Z", "");
    }
    const unit = formData.reminder_delay_unit || "days";
    if (unit === "minutes") {
      formData.reminder_delay = formData.reminder_delay / 1440;
    } else if (unit === "hours") {
      formData.reminder_delay = formData.reminder_delay / 24;
    } else if (unit === "weeks") {
      formData.reminder_delay = formData.reminder_delay * 7;
    }
    delete formData.reminder_delay_unit;
    try {
      await submitReminder({
        resourceId,
        resourceType,
        data: formData,
      }).unwrap();
      dispatch(showNotification("Reminder created"));
      handleClose();
    } catch {
      dispatch(showNotification("Error creating reminder", "error"));
    }
  };

  function validate(formData: any, errors: any) {
    if (formData.text === "") {
      errors.text = "Reminder text is required";
    }
    if (!resourceStartDate) {
      if (
        dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ") > formData.next_reminder
      ) {
        errors.next_reminder.addError(
          "Next reminder date can't be in the past",
        );
      }
    } else if (formData.lead_time <= 0) {
      errors.lead_time.addError("Lead time must be greater than 0");
    }
    if (formData.number_of_reminders <= 0) {
      errors.number_of_reminders.addError(
        "Number of reminders must be greater than 0",
      );
    }
    if (formData.reminder_delay <= 0) {
      errors.reminder_delay.addError("Reminder delay must be greater than 0");
    }
    return errors;
  }

  const shiftFormSchema = {
    type: "object",
    properties: {
      text: { type: "string", title: "Text" },
      lead_time: {
        type: "number",
        title: "Remind me before shift starts",
        default: 1,
      },
      lead_time_unit: {
        type: "string",
        title: "Lead time unit",
        enum: ["minutes", "hours", "days", "weeks"],
        default: "hours",
      },
      number_of_reminders: {
        type: "integer",
        title: "Number of reminders",
        default: 1,
      },
      reminder_delay: {
        type: "number",
        title: "Delay between reminders",
        default: 1,
      },
      reminder_delay_unit: {
        type: "string",
        title: "Unit",
        enum: ["minutes", "hours", "days", "weeks"],
        default: "hours",
      },
    },
    required: [
      "text",
      "lead_time",
      "lead_time_unit",
      "number_of_reminders",
      "reminder_delay",
      "reminder_delay_unit",
    ],
  };

  const genericFormSchema = {
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
        type: "number",
        title: "Delay between reminders",
        default: 1,
      },
      reminder_delay_unit: {
        type: "string",
        title: "Unit",
        enum: ["minutes", "hours", "days", "weeks"],
        default: "days",
      },
    },
    required: [
      "text",
      "next_reminder",
      "number_of_reminders",
      "reminder_delay",
      "reminder_delay_unit",
    ],
  };

  return (
    <Form
      schema={(resourceStartDate ? shiftFormSchema : genericFormSchema) as any}
      validator={validator}
      id="reminder-form"
      onSubmit={handleSubmit as any}
      customValidate={validate}
      liveValidate
    />
  );
};

interface RemindersProps {
  resourceId?: string;
  resourceType?: string;
  resourceStartDate?: Date;
}

const Reminders = ({
  resourceId,
  resourceType,
  resourceStartDate,
}: RemindersProps) => {
  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const [open, setOpen] = useState(false);
  const [deleteReminderMutation] = useDeleteReminderMutation();
  // for now, we'll just show the reminders of the current user.
  // in the future, we'll want to show all reminders for the resource
  // show the users in the reminders list (datatable)
  // and allow to choose users to add to the reminders to in the NewReminder dialog
  const { data: currentUser } = useGetProfileQuery();
  const { data: reminders } = useGetRemindersQuery(
    resourceId && resourceType ? { resourceId, resourceType } : skipToken,
  );
  const remindersList = (reminders ?? []).filter(
    (r: any) => r.user_id === currentUser?.id,
  );

  // Memoized so the toolbar (the "new reminder" button and quick-filter search
  // box) keeps a stable identity across the re-render that happens when the
  // reminders list loads; otherwise MUI remounts it and any element reference a
  // test is interacting with goes stale. Must be declared before the early
  // returns below so the hook runs on every render (rules-of-hooks).
  const CustomToolbar = useMemo(
    () =>
      function RemindersToolbar() {
        return (
          <DataGridToolbar
            showColumns={false}
            quickFilterTestId="reminders-quick-filter"
          >
            {!isReadOnly && (
              <IconButton
                name={`new_reminder_${resourceId}`}
                onClick={() => setOpen(true)}
              >
                <AddIcon />
              </IconButton>
            )}
          </DataGridToolbar>
        );
      },

    [resourceId, isReadOnly],
  );

  if (!resourceType || !resourceId) return <CircularProgress />;
  if (reminders == null) return null;

  const deleteReminder = async (reminderId: any) => {
    try {
      await deleteReminderMutation({
        resourceId,
        resourceType,
        reminderID: reminderId,
      }).unwrap();
      dispatch(showNotification("Reminder deleted"));
    } catch {
      dispatch(showNotification("Error deleting reminder", "error"));
    }
  };

  const columns: any[] = [
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
      valueFormatter: (value: number) => {
        if (!value) return "-";
        const totalMinutes = Math.round(value * 1440);
        if (totalMinutes < 60)
          return `${totalMinutes} minute${totalMinutes !== 1 ? "s" : ""}`;
        const totalHours = Math.round(value * 24);
        if (totalHours < 24)
          return `${totalHours} hour${totalHours !== 1 ? "s" : ""}`;
        const totalDays = Math.round(value);
        if (totalDays < 7)
          return `${totalDays} day${totalDays !== 1 ? "s" : ""}`;
        const totalWeeks = Math.round(value / 7);
        return `${totalWeeks} week${totalWeeks !== 1 ? "s" : ""}`;
      },
    },
    {
      field: "delete",
      headerName: "",
      width: 70,
      sortable: false,
      filterable: false,
      renderCell: (params: any) =>
        isReadOnly ? null : (
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
          getRowId={(row: any) => row.id}
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
            resourceStartDate={resourceStartDate}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Reminders;
