import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm } from "react-hook-form";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";
import TextField from "@mui/material/TextField";
import Button from "../../Button";
import UserPreferencesHeader from "./UserPreferencesHeader";
import * as profileActions from "../../../ducks/profile";
import ClassificationSelect from "../../classification/ClassificationSelect";
import DeletableChips from "../../DeletableChips";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
    maxWidth: "20rem",
  },
  form: {
    display: "flex",
    gap: "1rem",
    flexWrap: "wrap",
    paddingBottom: "1.5rem",
  },
  classificationsMenu: {
    minWidth: "12rem",
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
    const shortcuts = profile?.classificationShortcuts || {};
    shortcuts[formValues.shortcutName] = selectedClassifications;
    const prefs = {
      classificationShortcuts: shortcuts,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    setSelectedClassifications([]);
    reset({
      shortcutName: "",
    });
  };

  const onDelete = (shortcutName) => {
    const shortcuts = profile?.classificationShortcuts;
    delete shortcuts[shortcutName];
    const prefs = {
      classificationShortcuts: shortcuts,
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
            <div>
              <InputLabel htmlFor="shortcutNameInput">Shortcut Name</InputLabel>
              <TextField
                {...register("shortcutName", {
                  required: true,
                  validate: (value) => {
                    if (profile?.classificationShortcuts) {
                      return !(value in profile?.classificationShortcuts);
                    }
                    return null;
                  },
                })}
                name="shortcutName"
                id="shortcutNameInput"
                error={!!errors.shortcutName}
                helperText={
                  errors.shortcutName
                    ? "Required/Shortcut with that name already exists"
                    : ""
                }
              />
            </div>
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
