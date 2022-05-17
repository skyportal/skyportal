import React from "react";
import { useSelector, useDispatch } from "react-redux";

import FormGroup from "@material-ui/core/FormGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Switch from "@material-ui/core/Switch";
import Typography from "@material-ui/core/Typography";
import { makeStyles } from "@material-ui/core/styles";

import * as profileActions from "../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";

const useStyles = makeStyles((theme) => ({
  typography: {
    padding: theme.spacing(2),
  },
}));

const FavoriteSourcesNotificationPreferences = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();

  const prefToggled = (event) => {
    const prefs = {
      favorite_sources_activity_notifications: {
        [event.target.name]: event.target.checked,
      },
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const prefToggledSlack = (event) => {
    const prefs = {
      slack_integration: {
        [event.target.name]: event.target.checked,
      },
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div>
      <UserPreferencesHeader
        title="Notifications For Favorite Source Activity"
        popupText="Enable these to receive notifications for the selected activity types
          regarding sources you have starred/favorited."
      />
      <FormGroup row>
        <Typography className={classes.typography}>Browser:</Typography>
        <FormControlLabel
          control={
            <Switch
              checked={
                profile.favorite_sources_activity_notifications?.comments ===
                true
              }
              name="comments"
              onChange={prefToggled}
            />
          }
          label="New Comments"
        />
        <FormControlLabel
          control={
            <Switch
              checked={
                profile.favorite_sources_activity_notifications?.spectra ===
                true
              }
              name="spectra"
              onChange={prefToggled}
            />
          }
          label="New Spectra"
        />
        <FormControlLabel
          control={
            <Switch
              checked={
                profile.favorite_sources_activity_notifications
                  ?.classifications === true
              }
              name="classifications"
              onChange={prefToggled}
            />
          }
          label="New Classifications"
        />
      </FormGroup>
      {profile.slack_integration?.active && (
        <FormGroup row>
          <FormControlLabel
            control={
              <Switch
                checked={profile.slack_integration?.favorite_sources === true}
                name="favorite_sources"
                onChange={prefToggledSlack}
                data-testid="slack_also_push"
              />
            }
            label="Also Push to Slack"
          />
        </FormGroup>
      )}
    </div>
  );
};

export default FavoriteSourcesNotificationPreferences;
