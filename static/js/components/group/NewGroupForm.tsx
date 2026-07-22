import React, { useState } from "react";

import Box from "@mui/material/Box";
import Select from "@mui/material/Select";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import InputLabel from "@mui/material/InputLabel";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useAddNewGroupMutation } from "../../ducks/groups";
import { useGetUsersQuery } from "../../ducks/users";
import Button from "../Button";
import Paper from "../Paper";

const NewGroupForm = () => {
  const theme = useTheme();
  const [addNewGroup] = useAddNewGroupMutation();
  const { data: usersData } = useGetUsersQuery();
  const allUsers = usersData?.users ?? [];

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

  const userIDToName: Record<number, string> = {};
  allUsers?.forEach((u: any) => {
    userIDToName[u.id] = u.username;
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
    <Paper sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
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
            sx={{ width: { xs: "100%", sm: "50%" } }}
          />
        </Box>
        <Box>
          <TextField
            label="Nickname"
            name="nickname"
            value={formState.nickname}
            onChange={handleChange}
            sx={{ width: { xs: "100%", sm: "50%" } }}
          />
        </Box>
        <Box>
          <TextField
            label="Description"
            name="description"
            value={formState.description}
            onChange={handleChange}
            sx={{ width: { xs: "100%", sm: "50%" } }}
          />
        </Box>
        <Box>
          <FormControl sx={{ width: { xs: "100%", sm: "50%" } }}>
            <InputLabel id="select-admins-label">Group Admins</InputLabel>
            <Select
              labelId="select-admins-label"
              label="Group Admins"
              id="groupAdminsSelect"
              name="group_admins"
              multiple
              onChange={handleChange}
              renderValue={(selected: any) => (
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                  {selected.map((value: number) => (
                    <Chip
                      key={value}
                      label={userIDToName[value]}
                      sx={{ margin: "0.1rem" }}
                    />
                  ))}
                </Box>
              )}
              defaultValue={[]}
            >
              {allUsers.map((user: any) => (
                <MenuItem
                  key={user.id}
                  value={user.id}
                  sx={{
                    fontWeight: formState.group_admins.includes(user.id)
                      ? theme.typography.fontWeightMedium
                      : theme.typography.fontWeightRegular,
                  }}
                >
                  {user.username}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
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
    </Paper>
  );
};

export default NewGroupForm;
