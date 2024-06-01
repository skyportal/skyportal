import React from "react";
import { useDispatch, useSelector } from "react-redux";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";

import * as profileActions from "../ducks/profile";
import UserPreferencesHeader from "./user/UserPreferencesHeader";

const UIPreferences = () => {
  const preferences = useSelector((state) => state.profile.preferences);
  const currentTheme = preferences?.theme;
  const invertThumbnails = preferences?.invertThumbnails || false;
  const compactComments = preferences?.compactComments || false;
  const useAMPM = preferences?.useAMPM || false;
  const useRefMag = preferences?.useRefMag || false;
  const showBotComments = preferences?.showBotComments || false;
  const hideMLClassifications = preferences?.hideMLClassifications || false;
  const showSimilarSources = preferences?.showSimilarSources || false;
  const hideSourceSummary = preferences?.hideSourceSummary || false;
  const showAISourceSummary = preferences?.showAISourceSummary || false;

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

  const hideMLClassificationsToggled = (event) => {
    const prefs = {
      hideMLClassifications: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const showSimilarSourcesToggled = (event) => {
    const prefs = {
      showSimilarSources: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const hideSourceSummaryToggled = (event) => {
    const prefs = {
      hideSourceSummary: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const showAISourceSummaryToggled = (event) => {
    const prefs = {
      showAISourceSummary: event.target.checked,
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

  const hideMLClassificationsSwitch = (
    <Switch
      value="Hide ML-based Classifications by default"
      checked={hideMLClassifications}
      onChange={hideMLClassificationsToggled}
    />
  );

  const showSimilarSourcesSwitch = (
    <Switch
      value="Show Similar Sources (based on AI summaries) by default"
      checked={showSimilarSources}
      onChange={showSimilarSourcesToggled}
    />
  );

  const hideSourceSummarySwitch = (
    <Switch
      value="Hide Source Summaries (by default)"
      checked={hideSourceSummary}
      onChange={hideSourceSummaryToggled}
    />
  );

  const showAISourceSummarySwitch = (
    <Switch
      value="Show AI Source Summaries (by default)"
      checked={showAISourceSummary}
      onChange={showAISourceSummaryToggled}
    />
  );

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
        <FormControlLabel
          control={hideMLClassificationsSwitch}
          label="Hide ML-based Classifications"
        />
        <FormControlLabel
          control={showSimilarSourcesSwitch}
          label="Show Similar Sources"
        />
        <FormControlLabel
          control={hideSourceSummarySwitch}
          label="Hide Source Summaries on Source page"
        />
        {hideSourceSummary !== true && (
          <FormControlLabel
            control={showAISourceSummarySwitch}
            label="Show AI Source Summaries on Source page"
          />
        )}
      </FormGroup>
    </div>
  );
};

export default UIPreferences;
