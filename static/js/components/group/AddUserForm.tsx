import { useState } from "react";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Box from "@mui/material/Box";
import SearchableSelect from "../SearchableSelect";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
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

const CHECKBOXES = [
  { name: "canSave", label: "Can save to this group?" },
  {
    name: "canSharePhotometry",
    label: "Can share photometry data to other groups?",
  },
  { name: "admin", label: "Group Admin?" },
] as const;

const AddUserForm = ({ group_id }: { group_id: number }) => {
  const dispatch = useAppDispatch();
  const [addGroupUser] = useAddGroupUserMutation();
  const { data: usersData } = useGetUsersQuery();
  const [formState, setFormState] = useState<FormState>(defaultState);
  const [isError, setIsError] = useState(false);

  const allUsers = usersData?.users ?? [];
  if (!allUsers.length) return <CircularProgress />;

  const nonMemberUsers = allUsers.filter(
    (user: any) => !user.groups?.some((group: any) => group.id === group_id),
  );

  const handleClickSubmit = async () => {
    if (!formState.userID) {
      setIsError(true);
      return;
    }
    const { error } = await addGroupUser({ group_id, ...formState } as any);
    if (error) return;
    setFormState(defaultState);
    dispatch(showNotification("Successfully added user to group."));
  };

  return (
    <Box>
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
          data-testid="newGroupUser"
          value={
            nonMemberUsers.find((u: any) => u.id === formState.userID) ?? null
          }
          onChange={(_event, newValue: any) => {
            setFormState({ ...formState, userID: newValue?.id });
            setIsError(false);
          }}
          selectOnFocus
          clearOnBlur
          handleHomeEndKeys
          options={nonMemberUsers}
          getOptionLabel={(option: any) => option.username}
          sx={{ width: 300 }}
          error={isError}
          helperText={isError ? "Please select a user" : ""}
          textFieldProps={{ "data-testid": "newGroupUserTextInput" }}
        />
        {CHECKBOXES.map(({ name, label }) => (
          <FormControlLabel
            key={name}
            control={
              <Checkbox
                checked={formState[name]}
                onChange={(event) =>
                  setFormState({ ...formState, [name]: event.target.checked })
                }
                data-testid={`${name}Checkbox`}
              />
            }
            label={label}
          />
        ))}
      </Box>
      <Button secondary onClick={handleClickSubmit} sx={{ mt: 2 }}>
        Add user
      </Button>
    </Box>
  );
};

export default AddUserForm;
