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
  const useAMPM = preferences?.useAMPM || false;
  const useRefMag = preferences?.useRefMag || false;
  const showBotComments = preferences?.showBotComments || false;
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

  const useAMPMToggled = (event) => {
    const prefs = {
      useAMPM: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const useRefMagToggled = (event) => {
    const prefs = {
      useRefMag: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const showBotCommentsToggled = (event) => {
    const prefs = {
      showBotComments: event.target.checked,
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

  const useAMPMSwitch = (
    <Switch
      value="Use 24 hour or AM/PM"
      checked={useAMPM}
      onChange={useAMPMToggled}
    />
  );

  const useRefMagSwitch = (
    <Switch
      value="Plot Total Magnitude / Flux (including reference)"
      checked={useRefMag}
      onChange={useRefMagToggled}
    />
  );

  const showBotCommentsSwitch = (
    <Switch
      value="Show Bot Comments by default"
      checked={showBotComments}
      onChange={showBotCommentsToggled}
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
        <FormControlLabel control={useAMPMSwitch} label="24 Hour or AM/PM" />
        <FormControlLabel
          control={useRefMagSwitch}
          label="Use Reference Magnitude"
        />
        <FormControlLabel
          control={showBotCommentsSwitch}
          label="Bot Comments"
        />
      </FormGroup>
    </div>
  );
};

export default UIPreferences;
