import { useState } from "react";
import { useForm } from "react-hook-form";
import { makeStyles } from "tss-react/mui";
import TextField from "@mui/material/TextField";
import Button from "../../Button";
import UserPreferencesHeader from "./UserPreferencesHeader";
import { useAppDispatch, useAppSelector } from "../../../types/hooks";
import * as profileActions from "../../../ducks/profile";
import ClassificationSelect from "../../classification/ClassificationSelect";
import DeletableChips from "../../DeletableChips";

const useStyles = makeStyles()(() => ({
  form: {
    display: "flex",
    gap: "1rem",
    flexWrap: "wrap",
    paddingBottom: "1.5rem",
  },
}));

const ClassificationsShortcutForm = () => {
  const { classes } = useStyles();
  const profile = useAppSelector((state) => state.profile.preferences) as any;
  const {
    handleSubmit,
    register,
    reset,
    formState: { errors },
  } = useForm();
  const dispatch = useAppDispatch();

  const [selectedClassifications, setSelectedClassifications] = useState<
    string[]
  >([]);

  const onSubmit = (formValues: any) => {
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

  const onDelete = (shortcutName: string) => {
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
                validate: (value: string) =>
                  !profile?.classificationShortcuts ||
                  !(value in profile.classificationShortcuts) ||
                  "Shortcut with that name already exists",
              })}
              label="Shortcut Name"
              id="shortcutNameInput"
              error={!!errors.shortcutName}
              helperText={
                errors.shortcutName
                  ? (errors.shortcutName.message as string) || "Required"
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
