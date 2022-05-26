import React from "react";
import UserPreferencesHeader from "./UserPreferencesHeader";

import SetAutomaticallyVisiblePhotometry from "./SetAutomaticallyVisiblePhotometry";
import PhotometryButtonsForm from "./PhotometryButtonsForm";
import DataPointSizeForm from "./DataPointSizeForm";

const PhotometryPlottingPreferences = () => (
  <div>
    <div style={{ paddingBottom: "1rem" }}>
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

export default PhotometryPlottingPreferences;
