import { useState } from "react";
import TextField from "@mui/material/TextField";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Box from "@mui/material/Box";

import { useAddGroupUserMutation } from "../../ducks/groups";
import { useGetUsersQuery } from "../../ducks/users";
import Button from "../Button";

const filter = createFilterOptions<any>();

interface FormState {
  userID: number | null;
  admin: boolean;
  canSave: boolean;
}

const defaultState: FormState = {
  userID: null,
  admin: false,
  canSave: true,
};

interface AddUserFormProps {
  group_id: number;
}

const AddUserForm = ({ group_id }: AddUserFormProps) => {
  const [addGroupUser] = useAddGroupUserMutation();
  const { data: usersData } = useGetUsersQuery();
  const allUsers = usersData?.users ?? [];
  const [formState, setFormState] = useState<FormState>(defaultState);
  const [isError, setIsError] = useState(false);

  const nonMemberUsers = allUsers.filter(
    (user: any) =>
      !(user.groups ?? []).map((ug: any) => ug.id).includes(group_id),
  );

  const handleClickSubmit = async () => {
    if (!formState.userID) {
      setIsError(true);
      return;
    }
    try {
      await addGroupUser({
        group_id,
        ...formState,
      } as any).unwrap();
      setFormState(defaultState);
    } catch {
      // error notification handled by the API layer
    }
  };

  const toggleCheckbox = (event: any) => {
    setFormState({
      ...formState,
      [event.target.name]: event.target.checked,
    });
  };

  if (!allUsers?.length) return <CircularProgress />;

  return (
    <Box sx={{ width: "100%" }}>
      <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
        Add an existing user to this group.
      </Typography>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 2,
        }}
      >
        <Autocomplete
          data-testid="newGroupUser"
          onChange={(_event: any, newValue: any) => {
            setFormState({ ...formState, userID: newValue?.id });
            setIsError(false);
          }}
          filterOptions={(options, params) => filter(options, params)}
          selectOnFocus
          clearOnBlur
          handleHomeEndKeys
          options={nonMemberUsers}
          getOptionLabel={(option: any) => option.username}
          sx={{ width: 300 }}
          defaultValue={null}
          renderInput={(params) => (
            <TextField
              {...params}
              error={isError}
              helperText={isError ? "Please select a user" : ""}
              label="Username"
              data-testid="newGroupUserTextInput"
            />
          )}
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={formState.canSave}
              onChange={toggleCheckbox}
              name="canSave"
              data-testid="canSaveCheckbox"
            />
          }
          label="Can save to this group?"
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={formState.admin}
              onChange={toggleCheckbox}
              name="admin"
              data-testid="adminCheckbox"
            />
          }
          label="Group Admin?"
        />
      </Box>
      <Button secondary onClick={handleClickSubmit} sx={{ mt: 2 }}>
        Add user
      </Button>
    </Box>
  );
};

export default AddUserForm;
