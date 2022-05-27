import React from "react";
import { makeStyles } from "@material-ui/core";

import UserPreferencesHeader from "./UserPreferencesHeader";
import SetAutomaticallyVisiblePhotometry from "./SetAutomaticallyVisiblePhotometry";
import PhotometryButtonsForm from "./PhotometryButtonsForm";
import DataPointSizeForm from "./DataPointSizeForm";

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
      <DataPointSizeForm />
    </div>
  );
};

export default PhotometryPlottingPreferences;
