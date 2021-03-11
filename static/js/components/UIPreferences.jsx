import React from "react";
import { useSelector, useDispatch } from "react-redux";

import FormGroup from "@material-ui/core/FormGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Switch from "@material-ui/core/Switch";
import Typography from "@material-ui/core/Typography";

// import { useTheme } from '@material-ui/core/styles';

import * as profileActions from "../ducks/profile";

const UIPreferences = () => {
  const preferences = useSelector((state) => state.profile.preferences);
  const currentTheme = preferences?.theme;
  const invertThumbnails = preferences?.invertThumbnails || false;
  const dispatch = useDispatch();

  const themeToggled = (event) => {
    const prefs = {
      theme: event.target.checked ? "dark" : "light",
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const thumbnailInvertToggled = (event) => {
    const prefs = {
      invertThumbnails: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const themeSwitch = (
    <Switch
      value="Dark Mode"
      checked={currentTheme === "dark"}
      onChange={themeToggled}
    />
  );

  const thumbnailInvertSwitch = (
    <Switch
      value="Invert thumbnails"
      checked={invertThumbnails}
      onChange={thumbnailInvertToggled}
    />
  );

  /* To get hold of the current theme:

  const themeCtx = useTheme();
  console.log(themeCtx.palette.type);

  */

  return (
    <div>
      <Typography variant="h6">UI Preferences</Typography>
      <FormGroup row>
        <FormControlLabel control={themeSwitch} label="Dark mode" />
        <FormControlLabel
          control={thumbnailInvertSwitch}
          label="Invert thumbnails"
        />
      </FormGroup>
    </div>
  );
};

export default UIPreferences;
