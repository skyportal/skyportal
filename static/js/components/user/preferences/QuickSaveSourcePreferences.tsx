import AddIcon from "@mui/icons-material/Add";
import { Controller, useForm } from "react-hook-form";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import Button from "../../Button";
import { useGetGroupsQuery } from "../../../ducks/groups";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import { GroupSelect } from "../../candidate/scanFormFields";

interface QuickSaveButtonForm {
  name: string;
  groupIds: number[];
}

const QuickSaveSourcePreferences = () => {
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const { data: groupsData } = useGetGroupsQuery();
  const userAccessibleGroups = groupsData?.userAccessible ?? [];
  const { data: profile } = useGetProfileQuery();
  const quickSaveButtons: Record<string, number[]> =
    (profile?.preferences as any)?.quickSaveButtons ?? {};

  const {
    control,
    handleSubmit,
    register,
    reset,
    formState: { errors },
  } = useForm<QuickSaveButtonForm>({
    defaultValues: { name: "", groupIds: [] },
  });

  const onSubmit = ({ name, groupIds }: QuickSaveButtonForm) => {
    updateUserPreferences({
      quickSaveButtons: { ...quickSaveButtons, [name.trim()]: groupIds },
    })
      .unwrap()
      .then(() => reset())
      .catch(() => {});
  };

  const onDelete = (name: string) => {
    updateUserPreferences({
      quickSaveButtons: Object.fromEntries(
        Object.entries(quickSaveButtons).filter(([key]) => key !== name),
      ),
    });
  };

  if (!groupsData) return null;

  if (userAccessibleGroups.length === 0) {
    return (
      <Typography variant="body2" color="textSecondary">
        You do not have access to any group yet. Ask an administrator or a group
        admin to add you to one.
      </Typography>
    );
  }

  const groupNames = (groupIds: number[]) =>
    userAccessibleGroups
      .filter((group) => groupIds.includes(group.id))
      .map((group) => group.name)
      .join(", ");

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {Object.keys(quickSaveButtons).length > 0 && (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {Object.entries(quickSaveButtons).map(([name, groupIds]) => (
            <Tooltip key={name} title={groupNames(groupIds)}>
              <Chip
                label={name}
                color="primary"
                variant="outlined"
                onDelete={() => onDelete(name)}
              />
            </Tooltip>
          ))}
        </Box>
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
        <Controller
          name="groupIds"
          control={control}
          rules={{ validate: (ids) => ids.length > 0 }}
          render={({ field }) => (
            <GroupSelect
              groups={userAccessibleGroups}
              value={field.value}
              onChange={field.onChange}
              checkboxTestId="quickSaveGroupCheckbox"
              error={Boolean(errors.groupIds)}
              helperText={errors.groupIds ? "Select at least one group." : ""}
              sx={{ flex: "2 1 16rem" }}
            />
          )}
        />
        <TextField
          {...register("name", {
            validate: (value) =>
              value.trim() === ""
                ? "Required"
                : !(value.trim() in quickSaveButtons) ||
                  "Button with that name already exists",
          })}
          label="Button name"
          error={Boolean(errors.name)}
          helperText={errors.name?.message ?? ""}
          sx={{ flex: "1 1 12rem" }}
        />
        <Button
          primary
          type="submit"
          aria-label="Add quick save button"
          sx={{ minWidth: 56, width: 56, height: 56, padding: 0 }}
        >
          <AddIcon />
        </Button>
      </Box>
    </Box>
  );
};

export default QuickSaveSourcePreferences;
