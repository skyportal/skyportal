import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { makeStyles } from "@mui/styles";
import { useForm } from "react-hook-form";
import TextField from "@mui/material/TextField";
import Button from "../../Button";
import FilterSelect from "./FilterSelect";
import OriginSelect from "./OriginSelect";
import UserPreferencesHeader from "./UserPreferencesHeader";
import * as profileActions from "../../../ducks/profile";
import DeletableChips from "../../DeletableChips";

const useStyles = makeStyles(() => ({
  submitButton: {
    margin: "1.5rem 0 0 0",
  },
  form: {
    display: "flex",
    gap: "1rem",
    flexWrap: "wrap",
    paddingBottom: "1.5rem",
  },
}));

const PhotometryButtonsForm = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { photometryButtons } = useSelector(
    (state) => state.profile.preferences,
  );
  const {
    handleSubmit,
    register,
    control,
    reset,

    formState: { errors },
  } = useForm();
  const [selectedFilters, setSelectedFilters] = useState([]);
  const [selectedOrigins, setSelectedOrigins] = useState([]);

  const onFilterSelectChange = (event) => {
    setSelectedFilters(
      event.target.value.includes("Clear selections") ? [] : event.target.value,
    );
  };
  const onOriginSelectChange = (event) => {
    setSelectedOrigins(
      event.target.value.includes("Clear selections") ? [] : event.target.value,
    );
  };

  const onSubmit = (formValues) => {
    const currPhotButtons = photometryButtons || {};
    currPhotButtons[formValues.photometryButtonName] = {
      filters: selectedFilters,
      origins: selectedOrigins,
    };
    const prefs = {
      photometryButtons: currPhotButtons,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    setSelectedFilters([]);
    setSelectedOrigins([]);
    reset({
      photometryButtonName: "",
    });
  };

  const onDelete = (buttonName) => {
    const currPhotButtons = photometryButtons;
    delete currPhotButtons[buttonName];
    const prefs = {
      photometryButtons: currPhotButtons,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const parent = "PhotometryButtonsForm";

  return (
    <div>
      <UserPreferencesHeader
        title="Photometry Buttons"
        popupText="Select a group of filters and origins, give them a common name, and a button will appear on photometry plots for showing those filters/origins on the plot. The button will not hide the points already visible on the plot, it will only add the selected filters/origins to the visible points."
      />
      <div className={classes.form}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <div>
            <FilterSelect
              initValue={selectedFilters}
              onFilterSelectChange={onFilterSelectChange}
              control={control}
              parent={parent}
            />
            <OriginSelect
              initValue={selectedOrigins}
              onOriginSelectChange={onOriginSelectChange}
              control={control}
              parent={parent}
            />
            <TextField
              label="Name"
              {...register("photometryButtonName", {
                required: true,
                validate: (value) => {
                  if (photometryButtons) {
                    return !(value in photometryButtons);
                  }
                  return null;
                },
              })}
              name="photometryButtonName"
              id="photometryButtonNameInput"
              error={!!errors.photometryButtonName}
              helperText={
                errors.photometryButtonName
                  ? "Required/Button with that name already exists"
                  : ""
              }
            />
          </div>
          <Button
            primary
            type="submit"
            className={classes.submitButton}
            id="addPhotometryButtonButton"
          >
            Add Photometry Button
          </Button>
        </form>
        {photometryButtons && (
          <DeletableChips
            items={Object.keys(photometryButtons)}
            onDelete={onDelete}
            title="Photometry Buttons"
          />
        )}
      </div>
    </div>
  );
};

export default PhotometryButtonsForm;
