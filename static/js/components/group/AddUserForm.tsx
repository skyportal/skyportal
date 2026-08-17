import { useState } from "react";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Box from "@mui/material/Box";
import SearchableSelect from "../SearchableSelect";

import { useAddGroupUserMutation } from "../../ducks/groups";
import { useGetUsersQuery } from "../../ducks/users";
import Button from "../Button";

interface FormState {
  userID: number | null;
  admin: boolean;
  canSave: boolean;
  canSharePhotometry: boolean;
}

const defaultState: FormState = {
  userID: null,
  admin: false,
  canSave: true,
  canSharePhotometry: false,
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
        <SearchableSelect
          label="Username"
          dataTestId="newGroupUser"
          value={
            nonMemberUsers.find((u: any) => u.id === formState.userID) ?? null
          }
          onChange={(newValue: any) => {
            setFormState({ ...formState, userID: newValue?.id });
            setIsError(false);
          }}
          options={nonMemberUsers}
          getOptionLabel={(option: any) => option.username}
          sx={{ width: 300 }}
          error={isError}
          helperText={isError ? "Please select a user" : ""}
          textFieldProps={{ "data-testid": "newGroupUserTextInput" }}
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
              checked={formState.canSharePhotometry}
              onChange={toggleCheckbox}
              name="canSharePhotometry"
              data-testid="canSharePhotometryCheckbox"
            />
          }
          label="Can share photometry data to other groups?"
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
