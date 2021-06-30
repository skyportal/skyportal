import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import TextField from "@material-ui/core/TextField";
import Button from "@material-ui/core/Button";
import Dialog from "@material-ui/core/Dialog";
import DialogActions from "@material-ui/core/DialogActions";
import DialogContent from "@material-ui/core/DialogContent";
import DialogContentText from "@material-ui/core/DialogContentText";
import DialogTitle from "@material-ui/core/DialogTitle";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import Typography from "@material-ui/core/Typography";
import InputLabel from "@material-ui/core/InputLabel";
import IconButton from "@material-ui/core/IconButton";
import HelpOutlineIcon from "@material-ui/icons/HelpOutline";
import Popover from "@material-ui/core/Popover";
import { DatePicker } from "@material-ui/pickers";
import { makeStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import * as invitationsActions from "../ducks/invitations";

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
    const result = await dispatch(
      invitationsActions.inviteUser({
        userEmail: formState.newUserEmail,
        groupIDs: [group_id],
        groupAdmin: [admin],
        role: formState.role,
        streamIDs: null,
        canSave: [formState.canSave],
        userExpirationDate: formState.userExpirationDate,
      })
    );
    if (result.status === "success") {
      dispatch(
        showNotification(
          `Invitation successfully sent to ${formState.newUserEmail}`
        )
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
      userExpirationDate: date ? dayjs.utc(date) : date,
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
        <DatePicker
          value={formState.userExpirationDate}
          onChange={handleExpirationDateChange}
          label="User expiration date (UTC)"
          format="YYYY/MM/DD"
          disablePast
          clearable
          data-testid="expirationDatePicker"
        />
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
        data-testid="inviteNewUserButton"
        onClick={() => setConfirmDialogOpen(true)}
        variant="contained"
        size="small"
        disableElevation
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
            data-testid="confirmNewUserButton"
            onClick={() => {
              setConfirmDialogOpen(false);
              handleClickSubmit();
            }}
            color="primary"
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
