import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";

import FormGroup from "@material-ui/core/FormGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Switch from "@material-ui/core/Switch";
import IconButton from "@material-ui/core/IconButton";
import HelpOutlineIcon from "@material-ui/icons/HelpOutline";
import Typography from "@material-ui/core/Typography";
import { makeStyles } from "@material-ui/core/styles";
import Popover from "@material-ui/core/Popover";

import * as profileActions from "../ducks/profile";

const useStyles = makeStyles((theme) => ({
  header: {
    display: "flex",
    alignItems: "center",
    "& > h6": {
      marginRight: "0.5rem",
    },
  },
  typography: {
    padding: theme.spacing(2),
  },
}));

const NotificationPreferences = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();

  const [anchorEl, setAnchorEl] = useState(null);
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);
  const id = open ? "simple-popover" : undefined;

  const prefToggled = (event) => {
    const prefs = {
      [event.target.name]: event.target.checked,
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div>
      <div className={classes.header}>
        <Typography variant="h6" display="inline">
          SMS/Email Notification Preferences
        </Typography>
        <IconButton aria-label="help" size="small" onClick={handleClick}>
          <HelpOutlineIcon />
        </IconButton>
      </div>
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
      >
        <Typography className={classes.typography}>
          Enable these to receive notifications regarding sources triggered by
          other users within your groups.
        </Typography>
      </Popover>
      <FormGroup row>
        <FormControlLabel
          control={
            <Switch
              checked={profile.allowEmailAlerts === true}
              name="allowEmailAlerts"
              onChange={prefToggled}
            />
          }
          label="Email notifications"
        />
        <FormControlLabel
          control={
            <Switch
              checked={profile.allowSMSAlerts === true}
              name="allowSMSAlerts"
              onChange={prefToggled}
            />
          }
          label="SMS notifications"
        />
      </FormGroup>
    </div>
  );
};

export default NotificationPreferences;
