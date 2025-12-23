import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
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
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import Tooltip from "@mui/material/Tooltip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import * as invitationsActions from "../../ducks/invitations";

dayjs.extend(utc);

const defaultState = {
  newUserEmail: "",
  role: "Full user",
  admin: false,
  canSave: true,
  userExpirationDate: null,
};

const InviteNewUserForm = ({ groupID }) => {
  const dispatch = useDispatch();
  const [formState, setFormState] = useState(defaultState);
  const [confirmDialogOpen, setConfirmDialogOpen] = React.useState(false);

  const handleClickSubmit = async () => {
    // Admin should always be false for view-only users
    let admin = false;
    if (formState.role === "Full user") {
      admin = formState.admin;
    }
    const data = {
      userEmail: formState.newUserEmail,
      groupIDs: [groupID],
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
    const result = await dispatch(invitationsActions.inviteUser(data));
    if (result.status === "success") {
      dispatch(
        showNotification(
          `Invitation successfully sent to ${formState.newUserEmail}`,
        ),
      );
      setFormState({
        ...defaultState,
        role: formState.role,
      });
    }
  };

  const toggleCheckbox = (event) => {
    setFormState({
      ...formState,
      [event.target.name]: event.target.checked,
    });
  };

  return (
    <Box sx={{ width: "100%" }}>
      <Typography variant="h6">Invite a new user</Typography>
      <Typography variant="body2" color="textSecondary" mb={2}>
        Invite a new user to skyportal and add them to this group
      </Typography>
      <Box
        display="flex"
        justifyContent="space-beetwen"
        alignItems="center"
        gap={2}
      >
        <TextField
          id="newUserEmail"
          value={formState?.newUserEmail || ""}
          onChange={(event) =>
            setFormState({ ...formState, newUserEmail: event.target.value })
          }
          label="Enter user email"
        />
        <FormControl>
          <InputLabel>Sitewide user role</InputLabel>
          <Select
            label="Sitewide user role"
            defaultValue="Full user"
            onChange={(e) =>
              setFormState({ ...formState, role: e.target.value })
            }
          >
            <MenuItem value="Full user">Full user</MenuItem>
            <MenuItem value="View only">View only</MenuItem>
          </Select>
        </FormControl>
        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <DatePicker
            value={formState.userExpirationDate}
            onChange={(e) =>
              setFormState({ ...formState, userExpirationDate: e })
            }
            slotProps={{ textField: { variant: "outlined" } }}
            label="Expiration date (UTC)"
            showTodayButton={false}
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
        <Button
          secondary
          data-testid="inviteNewUserButton"
          onClick={() => setConfirmDialogOpen(true)}
          size="small"
        >
          Invite new user
        </Button>
        <Dialog
          open={confirmDialogOpen}
          onClose={() => setConfirmDialogOpen(false)}
        >
          <DialogTitle>Invite new user and add them to this group?</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Click Confirm to invite specified user and grant them access to
              this group.
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
    </Box>
  );
};
InviteNewUserForm.propTypes = {
  groupID: PropTypes.number.isRequired,
};

export default InviteNewUserForm;
