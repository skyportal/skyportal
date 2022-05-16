import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useForm } from "react-hook-form";
import Input from "@material-ui/core/Input";
import InputLabel from "@material-ui/core/InputLabel";
import Chip from "@material-ui/core/Chip";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import { makeStyles } from "@material-ui/core/styles";
import { Button, FormControl, TextField, Typography } from "@material-ui/core";
import UserPreferencesHeader from "./UserPreferencesHeader";
import { allowedClasses } from "./ClassificationForm";
import * as profileActions from "../ducks/profile";

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
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  let classifications = [];
  latestTaxonomyList?.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy)?.map(
      (option) => option.class
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();
  const { handleSubmit, register, errors, reset } = useForm();
  const dispatch = useDispatch();

  const ITEM_HEIGHT = 48;
  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5,
        width: 250,
      },
    },
  };

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
            <div>
              <FormControl className={classes.classificationsMenu}>
                <InputLabel id="classifications-select-label">
                  Classifications
                </InputLabel>
                <Select
                  labelId="classifications-select-label"
                  id="classifications-select"
                  multiple
                  value={selectedClassifications}
                  onChange={(event) => {
                    setSelectedClassifications(event.target.value);
                  }}
                  input={<Input id="classifications-select" />}
                  renderValue={(selected) => (
                    <div className={classes.chips}>
                      {selected?.map((classification) => (
                        <Chip key={classification} label={classification} />
                      ))}
                    </div>
                  )}
                  MenuProps={MenuProps}
                >
                  {classifications?.map((classification) => (
                    <MenuItem key={classification} value={classification}>
                      {classification}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
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
