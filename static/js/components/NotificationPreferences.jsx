import React from "react";
import { useSelector, useDispatch } from "react-redux";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";

import * as profileActions from "../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";

const NotificationPreferences = () => {
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();

  const prefToggled = (event) => {
    const prefs = {
      [event.target.name]: event.target.checked,
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div>
      <UserPreferencesHeader
        title="SMS/Email Notification Preferences"
        popupText="Enable these to receive notifications regarding sources triggered by other users within your groups."
      />
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
