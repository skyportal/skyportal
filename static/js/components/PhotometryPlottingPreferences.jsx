import React from "react";
import UserPreferencesHeader from "./UserPreferencesHeader";

import SetAutomaticallyVisiblePhotometry from "./SetAutomaticallyVisiblePhotometry";
import PhotometryButtonsForm from "./PhotometryButtonsForm";
import DataPointSizeForm from "./DataPointSizeForm";

const PhotometryPlottingPreferences = () => {
  return (
    <div>
      <UserPreferencesHeader
        variant="h5"
        title="Photometry Plotting Preferences"
      />
      <SetAutomaticallyVisiblePhotometry />
      <PhotometryButtonsForm />
      <DataPointSizeForm />
    </div>
  );
};

export default PhotometryPlottingPreferences;
