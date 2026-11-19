import React, { useState } from "react";

import Box from "@mui/material/Box";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { useAddNewGroupMutation } from "../../ducks/groups";
import { useGetUsersQuery } from "../../ducks/users";
import Button from "../Button";
import SearchableValueSelect from "../SearchableValueSelect";
import { compareUsersByLastName, userLabel } from "../../utils/format";

const NewGroupForm = ({ onCreated }: { onCreated?: () => void }) => {
  const [addNewGroup] = useAddNewGroupMutation();
  const { data: usersData } = useGetUsersQuery();
  const allUsers = [...(usersData?.users ?? [])].sort(compareUsersByLastName);

  const [formState, setState] = useState<{
    name: string;
    nickname: string;
    description: string;
    group_admins: number[];
    auto_accept_requests: boolean;
  }>({
    name: "",
    nickname: "",
    description: "",
    group_admins: [],
    auto_accept_requests: false,
  });

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      await addNewGroup(formState).unwrap();
      setState({
        name: "",
        nickname: "",
        description: "",
        group_admins: [],
        auto_accept_requests: false,
      });
      onCreated?.();
    } catch {
      // error notification handled by the API layer
    }
  };

  const handleChange = (event: any) => {
    const newState: Record<string, any> = {};
    newState[event.target.name] = event.target.value;
    setState({
      ...formState,
      ...newState,
    });
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Typography variant="h6">Create New Group</Typography>
      <form
        onSubmit={handleSubmit}
        style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
      >
        <Box>
          <TextField
            label="Group Name"
            name="name"
            value={formState.name}
            onChange={handleChange}
            fullWidth
          />
        </Box>
        <Box>
          <TextField
            label="Nickname"
            name="nickname"
            value={formState.nickname}
            onChange={handleChange}
            fullWidth
          />
        </Box>
        <Box>
          <TextField
            label="Description"
            name="description"
            value={formState.description}
            onChange={handleChange}
            fullWidth
          />
        </Box>
        <Box>
          <SearchableValueSelect
            id="groupAdminsSelect"
            label="Group Admins"
            multiple
            options={allUsers}
            value={formState.group_admins}
            onChange={(ids: number[]) =>
              setState({ ...formState, group_admins: ids })
            }
            getOptionLabel={(user: any) => userLabel(user, true)}
            fullWidth
          />
        </Box>
        <Box>
          <FormControlLabel
            control={
              <Checkbox
                name="auto_accept_requests"
                checked={formState.auto_accept_requests}
                onChange={(event) =>
                  setState({
                    ...formState,
                    auto_accept_requests: event.target.checked,
                  })
                }
                data-testid="autoAcceptRequestsCheckbox"
              />
            }
            label="Automatically accept requests to join this group"
          />
        </Box>
        <Box>
          <Button primary type="submit">
            Create Group
          </Button>
        </Box>
      </form>
    </Box>
  );
};

export default NewGroupForm;
