import React from "react";
import UserPreferencesHeader from "./UserPreferencesHeader";

import SetAutomaticallyVisiblePhotometry from "./SetAutomaticallyVisiblePhotometry";
import PhotometryButtonsForm from "./PhotometryButtonsForm";
import DataPointSizeForm from "./DataPointSizeForm";

const PhotometryPlottingPreferences = () => {
  // const [isSubmitting, setIsSubmitting] = useState(false);
  // const [filtersList, setFiltersList] = useState([]);
  // const [originsList, setOriginsList] = useState([]);
  // const profile = useSelector((state) => state.profile.preferences);

  // useEffect(() => {
  //   reset({
  //     photometryPlottingPreferencesName:
  //       profile.photometryPlottingPreferencesName,
  //   });
  // }, [reset, profile]);

  // const handleChangeFilters = (event) => {
  //   if (event.target.value.includes("Clear selections")) {
  //     setFiltersList([]);
  //   } else {
  //     setFiltersList(event.target.value);
  //   }
  // };

  // const handleChangeOrigins = (event) => {
  //   if (event.target.value.includes("Clear origins")) {
  //     setOriginsList([]);
  //   } else {
  //     setOriginsList(event.target.value);
  //   }
  // };

  // const handleClickSubmit = (event) => {
  //   console.log("handleClickSubmit");
  // };

  // const onSubmit = async (initialValues) => {
  //   let formIsValid = true;
  //   if (initialValues?.photometryPlottingPreferencesName?.length === 0) {
  //   }
  //   console.log(
  //     "initialValues",
  //     initialValues?.photometryPlottingPreferencesName?.length
  //   );
  //   setIsSubmitting(true);
  //   const prefs = {
  //     photometryPlotting: {
  //       Name: initialValues.photometryPlottingPreferencesName,
  //       Filters: filtersList,
  //       Origins: originsList,
  //     },
  //   };
  //   const result = await dispatch(
  //     profileActions.updateUserPhotometryPreferences(prefs)
  //   );
  //   if (result.status === "success") {
  //     dispatch(showNotification("Profile data saved"));
  //   }
  //   setIsSubmitting(false);
  // };

  // const onDelete = (shortcutName) => {
  //   const shortcuts = profile?.photometryPlottingFilters;
  //   delete shortcuts[shortcutName];
  //   const prefs = {
  //     photometryPlottingFilters: shortcuts,
  //   };
  //   dispatch(profileActions.updateUserPreferences(prefs));
  // };

  //let photometryData = photometry_to_filters(photometry);

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
