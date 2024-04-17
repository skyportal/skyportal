import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { makeStyles } from "@mui/styles";
import FilterSelect from "./FilterSelect";
import OriginSelect from "./OriginSelect";
import UserPreferencesHeader from "./user/UserPreferencesHeader";
import * as profileActions from "../ducks/profile";

const useStyles = makeStyles(() => ({
  form: {
    marginBottom: "1rem",
  },
}));

const SetAutomaticallyVisiblePhotometry = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { automaticallyVisibleFilters, automaticallyVisibleOrigins } =
    useSelector((state) => state.profile.preferences);
  const onFilterSelectChange = (event) => {
    const prefs = {
      automaticallyVisibleFilters: event.target.value.includes(
        "Clear selections",
      )
        ? []
        : event.target.value,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };
  const onOriginSelectChange = (event) => {
    const prefs = {
      automaticallyVisibleOrigins: event.target.value.includes(
        "Clear selections",
      )
        ? []
        : event.target.value,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };
  const parent = "AutomaticallyVisiblePhotometry";
  return (
    <div>
      <UserPreferencesHeader
        title="Set Automatically Visible Photometry"
        popupText="Select filters and origins which you would like to automatically be visible on the photometry plot. All other photometry points will be hidden, unless the plot does not contain your selected filters/origins."
      />
      <div className={classes.form}>
        <FilterSelect
          onFilterSelectChange={onFilterSelectChange}
          initValue={automaticallyVisibleFilters}
          parent={parent}
        />
        <OriginSelect
          onOriginSelectChange={onOriginSelectChange}
          initValue={automaticallyVisibleOrigins}
          parent={parent}
        />
      </div>
    </div>
  );
};

export default SetAutomaticallyVisiblePhotometry;
