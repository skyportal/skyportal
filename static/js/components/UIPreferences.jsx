import React from "react";
import { useSelector, useDispatch } from "react-redux";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";

import * as profileActions from "../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";

const UIPreferences = () => {
  const preferences = useSelector((state) => state.profile.preferences);
  const currentTheme = preferences?.theme;
  const invertThumbnails = preferences?.invertThumbnails || false;
  const compactComments = preferences?.compactComments || false;
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

  const commentsToggled = (event) => {
    const prefs = {
      compactComments: event.target.checked,
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
      value="Invert grayscale thumbnails"
      checked={invertThumbnails}
      onChange={thumbnailInvertToggled}
    />
  );

  const commpactCommentsSwitch = (
    <Switch
      value="Compact Comments"
      checked={compactComments}
      onChange={commentsToggled}
    />
  );

  /* To get hold of the current theme:

  const themeCtx = useTheme();
  console.log(themeCtx.palette.mode);

  */

  return (
    <div>
      <UserPreferencesHeader title="UI Preferences" />
      <FormGroup row>
        <FormControlLabel control={themeSwitch} label="Dark mode" />
        <FormControlLabel
          control={thumbnailInvertSwitch}
          label="Invert thumbnails"
        />
        <FormControlLabel
          control={commpactCommentsSwitch}
          label="Compact Comments"
        />
      </FormGroup>
    </div>
  );
};

export default UIPreferences;
