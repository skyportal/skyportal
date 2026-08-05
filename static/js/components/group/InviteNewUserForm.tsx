import React, { useState } from "react";
import TextField from "@mui/material/TextField";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import HelpOutlineIcon from "@mui/icons-material/HelpOutlineOutlined";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { useInviteUserMutation } from "../../ducks/invitations";

dayjs.extend(utc);

const defaultState: any = {
  newUserEmail: "",
  role: "Full user",
  admin: false,
  canSave: true,
  userExpirationDate: null,
};

interface InviteNewUserFormProps {
  group_id: number;
}

const InviteNewUserForm = ({ group_id }: InviteNewUserFormProps) => {
  const dispatch = useAppDispatch();
  const [inviteUser] = useInviteUserMutation();
  const [formState, setFormState] = useState<any>(defaultState);
  const [confirmDialogOpen, setConfirmDialogOpen] = React.useState(false);

  const handleClickSubmit = async () => {
    // Admin should always be false for view-only users
    let admin = false;
    if (formState.role === "Full user") {
      admin = formState.admin;
    }
    const data: any = {
      userEmail: formState.newUserEmail,
      groupIDs: [group_id],
      groupAdmin: [admin],
      role: formState.role,
      streamIDs: null,
      canSave: [formState.canSave],
    };
    if (formState.userExpirationDate?.length > 0) {
      if (!dayjs.utc(formState.userExpirationDate).isValid()) {
        dispatch(
          showNotification(
            "Invalid date. Please use MM/DD/YYYY format.",
            "error",
          ),
        );
        return;
      }
      data.userExpirationDate = dayjs
        .utc(formState.userExpirationDate)
        .toISOString();
    }
    try {
      await inviteUser(data).unwrap();
      dispatch(
        showNotification(
          `Invitation successfully sent to ${formState.newUserEmail}`,
        ),
      );
      setFormState({
        ...defaultState,
        role: formState.role,
      });
    } catch {
      // error notification handled by the base query
    }
  };

  const handleRoleChange = (event: any) => {
    setFormState({
      ...formState,
      role: event.target.value,
    });
  };

  const handleExpirationDateChange = (date: any) => {
    setFormState({
      ...formState,
      userExpirationDate: date,
    });
  };

  const toggleCheckbox = (event: any) => {
    setFormState({
      ...formState,
      [event.target.name]: event.target.checked,
    });
  };

  return (
    <Box sx={{ width: "100%" }}>
      <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
        Invite a new user to this website and add them to this group
      </Typography>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 2,
        }}
      >
        <TextField
          id="newUserEmail"
          data-testid="newUserEmail"
          value={formState?.newUserEmail || ""}
          onChange={(event) =>
            setFormState({ ...formState, newUserEmail: event.target.value })
          }
          label="Enter user email"
        />
        <FormControl>
          <InputLabel id="roleSelectLabel">User role</InputLabel>
          <Select
            defaultValue="Full user"
            onChange={handleRoleChange}
            labelId="roleSelectLabel"
            label="User role"
          >
            {["Full user", "View only"].map((role) => (
              <MenuItem key={role} value={role}>
                {role}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <DatePicker
            value={formState.userExpirationDate}
            onChange={handleExpirationDateChange}
            slotProps={{ textField: { variant: "outlined" } }}
            label="Expiration date (UTC)"
            {...({ showTodayButton: false } as any)}
          />
        </LocalizationProvider>
        <Tooltip
          title="This is the expiration date assigned to the new user account. After
          this date, the user account will be deactivated and will be unable
          to access the application."
        >
          <HelpOutlineIcon />
        </Tooltip>
        {formState.role === "Full user" && (
          <FormControlLabel
            control={
              <Checkbox
                checked={formState.canSave}
                onChange={toggleCheckbox}
                name="canSave"
              />
            }
            label="Can save to this group?"
          />
        )}
        {formState.role === "Full user" && formState.canSave && (
          <FormControlLabel
            control={
              <Checkbox
                checked={formState.admin}
                onChange={toggleCheckbox}
                name="admin"
              />
            }
            label="Group Admin?"
          />
        )}
      </Box>
      <Button
        secondary
        data-testid="inviteNewUserButton"
        onClick={() => setConfirmDialogOpen(true)}
        sx={{ mt: 2 }}
      >
        Invite new user
      </Button>
      <Dialog
        open={confirmDialogOpen}
        onClose={() => setConfirmDialogOpen(false)}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          Invite new user and add to this group?
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Click Confirm to invite specified user and grant them access to this
            group.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)}>Cancel</Button>
          <Button
            primary
            data-testid="confirmNewUserButton"
            onClick={() => {
              setConfirmDialogOpen(false);
              handleClickSubmit();
            }}
            autoFocus
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default InviteNewUserForm;
