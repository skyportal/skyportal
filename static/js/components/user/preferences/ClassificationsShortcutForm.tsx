import { useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import { useForm } from "react-hook-form";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Button from "../../Button";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import ClassificationSelect from "../../classification/ClassificationSelect";
import DeletableChips from "../../DeletableChips";

const ClassificationsShortcutForm = () => {
  const { data: profileData } = useGetProfileQuery();
  const profile = (profileData?.preferences ?? {}) as any;
  const {
    handleSubmit,
    register,
    reset,
    formState: { errors },
  } = useForm();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

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
    updateUserPreferences(prefs);
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
    updateUserPreferences(prefs);
  };

  const shortcuts = Object.keys(profile?.classificationShortcuts ?? {});

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {shortcuts.length > 0 && (
        <DeletableChips items={shortcuts} onDelete={onDelete} />
      )}
      <Box
        component="form"
        onSubmit={handleSubmit(onSubmit)}
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-start",
          gap: 1.5,
        }}
      >
        <Box sx={{ flex: "2 1 16rem" }}>
          <ClassificationSelect
            selectedClassifications={selectedClassifications}
            setSelectedClassifications={setSelectedClassifications}
          />
        </Box>
        <TextField
          {...register("shortcutName", {
            required: true,
            validate: (value: string) =>
              !profile?.classificationShortcuts ||
              !(value in profile.classificationShortcuts) ||
              "Shortcut with that name already exists",
          })}
          label="Shortcut name"
          id="shortcutNameInput"
          error={!!errors["shortcutName"]}
          helperText={
            errors["shortcutName"]
              ? (errors["shortcutName"].message as string) || "Required"
              : ""
          }
          sx={{ flex: "1 1 12rem" }}
        />
        <Button
          primary
          type="submit"
          data-testid="addShortcutButton"
          aria-label="Add shortcut"
          sx={{ minWidth: 56, width: 56, height: 56, padding: 0 }}
        >
          <AddIcon />
        </Button>
      </Box>
    </Box>
  );
};

export default ClassificationsShortcutForm;
