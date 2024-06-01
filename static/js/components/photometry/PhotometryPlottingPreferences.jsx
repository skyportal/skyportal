import React from "react";
import { makeStyles } from "@mui/styles";

import UserPreferencesHeader from "../user/UserPreferencesHeader";
import SetAutomaticallyVisiblePhotometry from "../SetAutomaticallyVisiblePhotometry";
import PhotometryButtonsForm from "./PhotometryButtonsForm";

const useStyles = makeStyles(() => ({
  photometryPlottingPreferencesHeader: {
    paddingBottom: "1rem",
  },
}));

const PhotometryPlottingPreferences = () => {
  const classes = useStyles();
  return (
    <div>
      <div className={classes.photometryPlottingPreferencesHeader}>
        <UserPreferencesHeader
          variant="h5"
          title="Photometry Plotting Preferences"
        />
      </div>
      <SetAutomaticallyVisiblePhotometry />
      <PhotometryButtonsForm />
    </div>
  );
};

export default PhotometryPlottingPreferences;
