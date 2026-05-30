import React from "react";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";

import { useAppDispatch, useAppSelector } from "../../../types/hooks";
import * as profileActions from "../../../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";

const UIPreferences = () => {
  const preferences = useAppSelector(
    (state) => state.profile.preferences,
  ) as any;
  const currentTheme = preferences?.theme;
  const invertThumbnails: boolean = preferences?.invertThumbnails || false;
  const useAMPM: boolean = preferences?.useAMPM || false;
  const useRefMag: boolean = preferences?.useRefMag || false;
  const showBotComments: boolean = preferences?.showBotComments || false;
  const hideMLClassifications: boolean =
    preferences?.hideMLClassifications || false;
  const showSimilarSources: boolean = preferences?.showSimilarSources || false;
  const hideSourceSummary: boolean = preferences?.hideSourceSummary || false;
  const showAISourceSummary: boolean =
    preferences?.showAISourceSummary || false;

  const dispatch = useAppDispatch();

  const themeToggled = (event: any) => {
    const prefs = {
      theme: event.target.checked ? "dark" : "light",
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const thumbnailInvertToggled = (event: any) => {
    const prefs = {
      invertThumbnails: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const useAMPMToggled = (event: any) => {
    const prefs = {
      useAMPM: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const useRefMagToggled = (event: any) => {
    const prefs = {
      useRefMag: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const showBotCommentsToggled = (event: any) => {
    const prefs = {
      showBotComments: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const hideMLClassificationsToggled = (event: any) => {
    const prefs = {
      hideMLClassifications: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const showSimilarSourcesToggled = (event: any) => {
    const prefs = {
      showSimilarSources: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const hideSourceSummaryToggled = (event: any) => {
    const prefs = {
      hideSourceSummary: event.target.checked,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const showAISourceSummaryToggled = (event: any) => {
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
