import React from "react";
import { makeStyles } from "@mui/styles";

import UserPreferencesHeader from "./UserPreferencesHeader";
import SpectroscopyButtonsForm from "./SpectroscopyButtonsForm";

const useStyles = makeStyles(() => ({
  spectroscopyPlottingPreferencesHeader: {
    paddingBottom: "1rem",
  },
}));

const SpectroscopyPlottingPreferences = () => {
  const classes = useStyles();
  return (
    <div>
      <div className={classes.spectroscopyPlottingPreferencesHeader}>
        <UserPreferencesHeader
          variant="h5"
          title="Spectroscopy Plotting Preferences"
        />
      </div>
      <SpectroscopyButtonsForm />
    </div>
  );
};

export default SpectroscopyPlottingPreferences;
