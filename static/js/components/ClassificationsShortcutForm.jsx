import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useForm } from "react-hook-form";
import InputLabel from "@material-ui/core/InputLabel";
import Chip from "@material-ui/core/Chip";
import { makeStyles } from "@material-ui/core/styles";
import { Button, TextField, Typography } from "@material-ui/core";
import UserPreferencesHeader from "./UserPreferencesHeader";
import * as profileActions from "../ducks/profile";
import ClassificationSelect from "./ClassificationSelect";

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
  const { handleSubmit, register, errors, reset } = useForm();
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
                inputRef={register({
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
          <Button
            variant="contained"
            type="submit"
            data-testid="addShortcutButton"
          >
            Add Shortcut
          </Button>
        </form>
        {profile?.classificationShortcuts && (
          <div>
            <Typography>Shortcuts</Typography>
            {Object.keys(profile?.classificationShortcuts)?.map(
              (shortcutName) => (
                <Chip
                  key={shortcutName}
                  label={shortcutName}
                  onDelete={() => onDelete(shortcutName)}
                />
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ClassificationsShortcutForm;
