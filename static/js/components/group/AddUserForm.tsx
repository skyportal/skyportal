import { useState } from "react";
import type { FormEvent } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useAddGroupUserMutation } from "../../ducks/groups";
import { useGetUsersQuery } from "../../ducks/users";
import SearchableSelect from "../SearchableSelect";
import MemberPermissions, { DEFAULT_PERMISSIONS } from "./MemberPermissions";
import type { AddMembersFormProps } from "./GroupAddMembers";

const AddUserForm = ({ groupID, formId, onSuccess }: AddMembersFormProps) => {
  const dispatch = useAppDispatch();
  const [addGroupUser] = useAddGroupUserMutation();
  const { data: usersData } = useGetUsersQuery();
  const [user, setUser] = useState<any>(null);
  const [permissions, setPermissions] = useState(DEFAULT_PERMISSIONS);
  const [isError, setIsError] = useState(false);

  const allUsers = usersData?.users ?? [];
  if (!allUsers.length) return <CircularProgress />;

  const nonMemberUsers = allUsers.filter(
    (u: any) => !u.groups?.some((group: any) => group.id === groupID),
  );

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!user) return setIsError(true);
    const { error } = await addGroupUser({
      group_id: groupID,
      userID: user.id,
      ...permissions,
    } as any);
    if (error) return;
    dispatch(showNotification("Successfully added user to group."));
    onSuccess();
  };

  return (
    <Box
      component="form"
      id={formId}
      onSubmit={handleSubmit}
      sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}
    >
      <SearchableSelect
        label="Username"
        data-testid="newGroupUser"
        value={user}
        onChange={(_event, value) => {
          setUser(value);
          setIsError(false);
        }}
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        fullWidth
        options={nonMemberUsers}
        getOptionLabel={(option: any) => option.username}
        error={isError}
        helperText={isError ? "Please select a user" : ""}
        textFieldProps={{ "data-testid": "newGroupUserTextInput" }}
      />
      <MemberPermissions value={permissions} onChange={setPermissions} />
    </Box>
  );
};

export default AddUserForm;
