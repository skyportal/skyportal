import React from "react";
import UserPreferencesHeader from "./UserPreferencesHeader";

import SetAutomaticallyVisiblePhotometry from "./SetAutomaticallyVisiblePhotometry";
import PhotometryButtonsForm from "./PhotometryButtonsForm";
import DataPointSizeForm from "./DataPointSizeForm";
import { makeStyles } from "@material-ui/core/node_modules/@material-ui/styles";

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
