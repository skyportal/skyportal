import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { makeStyles } from "@mui/styles";
import { useForm } from "react-hook-form";
import { TextField } from "@mui/material";
import Button from "./Button";
import UserPreferencesHeader from "./UserPreferencesHeader";
import SpectroscopyColorSelect from "./SpectroscopyColorSelect";
import DeletableChips from "./DeletableChips";

import * as profileActions from "../ducks/profile";

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

const SpectroscopyButtonsForm = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { spectroscopyButtons } = useSelector(
    (state) => state.profile.preferences
  );
  const {
    handleSubmit,
    register,
    reset,
    control,
    formState: { errors },
  } = useForm();
  const [selectedColor, setSelectedColor] = useState([]);

  const onColorSelectChange = (event) => {
    setSelectedColor(
      event.target.value.includes("Clear selections") ? [] : event.target.value
    );
  };

  const onSubmit = (formValues) => {
    const currSpectroscopyButtons = spectroscopyButtons || {};
    currSpectroscopyButtons[formValues.spectroscopyButtonName] = {
      color: selectedColor,
      wavelengths: formValues.spectroscopyButtonWavelengths
        .split(",")
        .map(Number),
    };
    const prefs = {
      spectroscopyButtons: currSpectroscopyButtons,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    reset({
      spectroscopyButtonName: "",
    });
  };

  const onDelete = (buttonName) => {
    const currSpectroscopyButtons = spectroscopyButtons;
    delete currSpectroscopyButtons[buttonName];
    const prefs = {
      spectroscopyButtons: currSpectroscopyButtons,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div>
      <UserPreferencesHeader
        title="Spectroscopy Extra Wavelengths"
        popupText="Select a group of wavelengths, give them a common name and color, and a button will appear on spectroscopy plots for showing those spectral lines on the plot."
      />
      <div className={classes.form}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <div>
            <TextField
              label="Wavelengths"
              {...register("spectroscopyButtonWavelengths", {
                required: true,
              })}
              name="spectroscopyButtonWavelengths"
              id="spectroscopyButtonWavelengthInput"
            />
            <SpectroscopyColorSelect
              initValue={selectedColor}
              onColorSelectChange={onColorSelectChange}
              control={control}
            />
            <TextField
              label="Name"
              {...register("spectroscopyButtonName", {
                required: true,
                validate: (value) => {
                  if (spectroscopyButtons) {
                    return !(value in spectroscopyButtons);
                  }
                  return null;
                },
              })}
              name="spectroscopyButtonName"
              id="spectroscopyButtonNameInput"
              error={!!errors.spectroscopyButtonName}
              helperText={
                errors.spectroscopyButtonName
                  ? "Required/Button with that name already exists"
                  : ""
              }
            />
          </div>
          <Button
            primary
            type="submit"
            className={classes.submitButton}
            id="addSpectroscopyButtonButton"
          >
            Add Spectroscopy Button
          </Button>
        </form>
        {spectroscopyButtons && (
          <DeletableChips
            items={Object.keys(spectroscopyButtons)}
            onDelete={onDelete}
            title="Spectroscopy Buttons"
          />
        )}
      </div>
    </div>
  );
};

export default SpectroscopyButtonsForm;
