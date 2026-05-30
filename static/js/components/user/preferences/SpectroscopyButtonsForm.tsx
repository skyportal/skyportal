import React from "react";
import { makeStyles } from "tss-react/mui";
import { useForm } from "react-hook-form";
import TextField from "@mui/material/TextField";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import { useAppDispatch, useAppSelector } from "../../../types/hooks";
import Button from "../../Button";
import UserPreferencesHeader from "./UserPreferencesHeader";
import * as profileActions from "../../../ducks/profile";

const useStyles = makeStyles()(() => ({
  submitButton: {
    margin: "0.5rem 0 0 0",
  },
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
    flexWrap: "wrap",
    paddingBottom: "1.5rem",
    justifyContent: "center",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    flexWrap: "wrap",
    maxWidth: "40rem",
  },
  chips: {
    display: "flex",
    gap: "1rem",
    flexWrap: "wrap",
  },
}));

const SpectroscopyButtonsForm = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const colorPalette = useAppSelector((state) => state.config.colorPalette);
  const { spectroscopyButtons } = useAppSelector(
    (state) => state.profile.preferences,
  ) as any;
  const {
    handleSubmit,
    register,
    reset,
    formState: { errors },
  } = useForm();

  const onSubmit = (formValues: any) => {
    const currSpectroscopyButtons = {
      ...(spectroscopyButtons || {}),
      [formValues.spectroscopyButtonName]: {
        color: formValues.spectroscopyColorSelect,
        wavelengths: formValues.spectroscopyButtonWavelengths
          .split(",")
          .map(Number),
      },
    };
    const prefs = {
      spectroscopyButtons: currSpectroscopyButtons,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    reset({
      spectroscopyButtonName: "",
      spectroscopyButtonWavelengths: "",
    });
  };

  const onDelete = (buttonName: string) => {
    const { [buttonName]: _removed, ...currSpectroscopyButtons } =
      spectroscopyButtons || {};
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
      <div className={classes.root}>
        {spectroscopyButtons && (
          <div className={classes.chips}>
            {Object.entries(spectroscopyButtons).map(
              ([key, value]: [string, any]) => (
                <Chip
                  key={key}
                  label={key}
                  onDelete={() => onDelete(key)}
                  color="primary"
                  style={{ backgroundColor: value.color[0] }}
                />
              ),
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className={classes.form}>
            <div>
              <InputLabel htmlFor="spectroscopyColorSelect">Color</InputLabel>
              <Select
                fullWidth
                name="spectroscopyColorSelect"
                id="spectroscopyColorSelectInput"
                {...register("spectroscopyColorSelect", { required: true })}
                error={!!errors.spectroscopyColorSelect}
              >
                {(colorPalette || []).map((color: any) => (
                  <MenuItem key={color} value={color}>
                    <div
                      style={{
                        width: "1rem",
                        height: "1rem",
                        background: color,
                      }}
                    />
                  </MenuItem>
                ))}
              </Select>
            </div>
            <TextField
              label="Name"
              {...register("spectroscopyButtonName", {
                required: "Name is required",
                validate: (value) =>
                  spectroscopyButtons && value in spectroscopyButtons
                    ? "A button with this name already exists"
                    : true,
              })}
              name="spectroscopyButtonName"
              id="spectroscopyButtonNameInput"
              error={!!errors.spectroscopyButtonName}
              helperText={errors.spectroscopyButtonName?.message as any}
            />
            <TextField
              label="Wavelengths"
              {...register("spectroscopyButtonWavelengths", {
                required: "Wavelengths are required",
              })}
              name="spectroscopyButtonWavelengths"
              id="spectroscopyButtonWavelengthInput"
              error={!!errors.spectroscopyButtonWavelengths}
              helperText={errors.spectroscopyButtonWavelengths?.message as any}
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
      </div>
    </div>
  );
};

export default SpectroscopyButtonsForm;
