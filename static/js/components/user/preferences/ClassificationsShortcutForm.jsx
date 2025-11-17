import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm } from "react-hook-form";
import makeStyles from "@mui/styles/makeStyles";
import TextField from "@mui/material/TextField";
import Button from "../../Button";
import UserPreferencesHeader from "./UserPreferencesHeader";
import * as profileActions from "../../../ducks/profile";
import ClassificationSelect from "../../classification/ClassificationSelect";
import DeletableChips from "../../DeletableChips";

const useStyles = makeStyles(() => ({
  form: {
    display: "flex",
    gap: "1rem",
    flexWrap: "wrap",
    paddingBottom: "1.5rem",
  },
}));

const ClassificationsShortcutForm = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile.preferences);
  const {
    handleSubmit,
    register,
    reset,
    formState: { errors },
  } = useForm();
  const dispatch = useDispatch();

  const [selectedClassifications, setSelectedClassifications] = useState([]);

  const onSubmit = (formValues) => {
    const prefs = {
      classificationShortcuts: {
        ...(profile?.classificationShortcuts || {}),
        [formValues.shortcutName]: selectedClassifications,
      },
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    setSelectedClassifications([]);
    reset({ shortcutName: "" });
  };

  const onDelete = (shortcutName) => {
    const prefs = {
      classificationShortcuts: Object.fromEntries(
        Object.entries(profile?.classificationShortcuts || {}).filter(
          ([key]) => key !== shortcutName,
        ),
      ),
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div>
      <UserPreferencesHeader
        title="Classifications Shortcut"
        popupText="Select a group of preexisting classifications, give them a common name, and a shortcut button will appear on the scanning page for selecting those classifications."
      />
      <div className={classes.form}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className={classes.form}>
            <ClassificationSelect
              selectedClassifications={selectedClassifications}
              setSelectedClassifications={setSelectedClassifications}
            />
            <TextField
              {...register("shortcutName", {
                required: true,
                validate: (value) =>
                  !profile?.classificationShortcuts ||
                  !(value in profile.classificationShortcuts) ||
                  "Shortcut with that name already exists",
              })}
              label="Shortcut Name"
              id="shortcutNameInput"
              error={!!errors.shortcutName}
              helperText={
                errors.shortcutName
                  ? errors.shortcutName.message || "Required"
                  : ""
              }
            />
          </div>
          <Button primary type="submit" data-testid="addShortcutButton">
            Add Shortcut
          </Button>
        </form>
        {profile?.classificationShortcuts && (
          <DeletableChips
            items={Object.keys(profile?.classificationShortcuts)}
            onDelete={onDelete}
            title="Shortcuts"
          />
        )}
      </div>
    </div>
  );
};

export default ClassificationsShortcutForm;
