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
import IconButton from "@mui/material/IconButton";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import Popover from "@mui/material/Popover";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import makeStyles from "@mui/styles/makeStyles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import * as invitationsActions from "../../ducks/invitations";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
  userExpirationDate: {
    display: "flex",
    alignItems: "flex-end",
    "& > div": {
      minWidth: "12rem",
    },
  },
  typography: {
    padding: theme.spacing(1),
  },
}));

const defaultState = {
  newUserEmail: "",
  role: "Full user",
  admin: false,
  canSave: true,
  userExpirationDate: null,
};

const InviteNewGroupUserForm = ({ group_id }) => {
  const dispatch = useDispatch();
  const [formState, setFormState] = useState(defaultState);
  const [confirmDialogOpen, setConfirmDialogOpen] = React.useState(false);
  const classes = useStyles();

  const [anchorEl, setAnchorEl] = useState(null);
  const handleClickExpirationDateHelp = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleCloseExpirationDateHelp = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);
  const id = open ? "expiration-date-popover" : undefined;

  const handleClickSubmit = async () => {
    // Admin should always be false for view-only users
    let admin = false;
    if (formState.role === "Full user") {
      admin = formState.admin;
    }
    const data = {
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

  const handleRoleChange = (event) => {
    setFormState({
      ...formState,
      role: event.target.value,
    });
  };

  const handleExpirationDateChange = (date) => {
    setFormState({
      ...formState,
      userExpirationDate: date,
    });
  };

  const toggleCheckbox = (event) => {
    setFormState({
      ...formState,
      [event.target.name]: event.target.checked,
    });
  };

  return (
    <div>
      <Typography className={classes.heading}>
        Invite a new user to the site and add them to this group
      </Typography>
      <div style={{ paddingBottom: "1rem" }}>
        <TextField
          id="newUserEmail"
          data-testid="newUserEmail"
          value={formState?.newUserEmail || ""}
          onChange={(event) =>
            setFormState({ ...formState, newUserEmail: event.target.value })
          }
          label="Enter user email"
        />
      </div>
      <div style={{ paddingBottom: "0.5rem" }}>
        <InputLabel id="roleSelectLabel">Site-wide user role</InputLabel>
        <Select
          defaultValue="Full user"
          onChange={handleRoleChange}
          labelId="roleSelectLabel"
        >
          {["Full user", "View only"].map((role) => (
            <MenuItem key={role} value={role}>
              {role}
            </MenuItem>
          ))}
        </Select>
      </div>
      <div className={classes.userExpirationDate}>
        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <DatePicker
            value={formState.userExpirationDate}
            onChange={handleExpirationDateChange}
            slotProps={{ textField: { variant: "outlined" } }}
            label="Expiration date (UTC)"
            showTodayButton={false}
          />
        </LocalizationProvider>
        <IconButton
          aria-label="help"
          size="small"
          onClick={handleClickExpirationDateHelp}
        >
          <HelpOutlineIcon />
        </IconButton>
        <Popover
          id={id}
          open={open}
          anchorEl={anchorEl}
          onClose={handleCloseExpirationDateHelp}
          anchorOrigin={{
            vertical: "middle",
            horizontal: "right",
          }}
          transformOrigin={{
            vertical: "middle",
            horizontal: "left",
          }}
        >
          <Typography className={classes.typography}>
            This is the expiration date assigned to the new user account. After
            this date, the user account will be deactivated and will be unable
            to access the application.
          </Typography>
        </Popover>
      </div>
      {formState.role === "Full user" && (
        <>
          <input
            type="checkbox"
            checked={formState.canSave}
            onChange={toggleCheckbox}
            name="canSave"
          />
          Can save to this group &nbsp;&nbsp;
        </>
      )}
      {formState.role === "Full user" && formState.canSave && (
        <>
          <input
            type="checkbox"
            checked={formState.admin}
            onChange={toggleCheckbox}
            name="admin"
          />
          Group Admin &nbsp;&nbsp;
        </>
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
        onClose={() => {
          setConfirmDialogOpen(false);
        }}
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
          <Button
            onClick={() => {
              setConfirmDialogOpen(false);
            }}
          >
            Cancel
          </Button>
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
    </div>
  );
};
InviteNewGroupUserForm.propTypes = {
  group_id: PropTypes.number.isRequired,
};

export default InviteNewGroupUserForm;
