import { makeStyles } from "@material-ui/core";
import React from "react";
import { useForm } from "react-hook-form";
import { useDispatch, useSelector } from "react-redux";
import FilterSelect from "./FilterSelect";
import OriginSelect from "./OriginSelect";
import UserPreferencesHeader from "./UserPreferencesHeader";
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
  console.log(automaticallyVisibleFilters) 
  const onFilterSelectChange = (event) => {
    const prefs = {
      automaticallyVisibleFilters: event.target.value.includes(
        "Clear selections"
      )
        ? []
        : event.target.value,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };
  const onOriginSelectChange = (event) => {
    const prefs = {
      automaticallyVisibleOrigins: event.target.value.includes(
        "Clear selections"
      )
        ? []
        : event.target.value,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };
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
        />
        <OriginSelect
          onOriginSelectChange={onOriginSelectChange}
          initValue={automaticallyVisibleOrigins}
        />
      </div>
    </div>
  );
};

export default SetAutomaticallyVisiblePhotometry;
