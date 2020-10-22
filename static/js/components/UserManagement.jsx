import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import Table from "@material-ui/core/Table";
import TableBody from "@material-ui/core/TableBody";
import TableCell from "@material-ui/core/TableCell";
import TableHead from "@material-ui/core/TableHead";
import TableRow from "@material-ui/core/TableRow";
import Paper from "@material-ui/core/Paper";
import Chip from "@material-ui/core/Chip";
import CircularProgress from "@material-ui/core/CircularProgress";
import Typography from "@material-ui/core/Typography";
import TextareaAutosize from "@material-ui/core/TextareaAutosize";
import Box from "@material-ui/core/Box";
import Autocomplete from "@material-ui/lab/Autocomplete";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import AddCircleIcon from "@material-ui/icons/AddCircle";
import IconButton from "@material-ui/core/IconButton";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import PapaParse from "papaparse";
import { useForm, Controller } from "react-hook-form";

import { showNotification } from "baselayer/components/Notifications";

import FormValidationError from "./FormValidationError";
import * as groupsActions from "../ducks/groups";
import * as usersActions from "../ducks/users";
import * as streamsActions from "../ducks/streams";
import * as inviteUsersActions from "../ducks/inviteUsers";

const sampleCSVText = `example1@gmail.com,1,3,false
example2@gmail.com,1 2 3,2 5 9,false false true`;

const UserManagement = () => {
  const dispatch = useDispatch();
  const { invitationsEnabled } = useSelector((state) => state.sysInfo);
  const currentUser = useSelector((state) => state.profile);
  const { allUsers } = useSelector((state) => state.users);
  const { all: allGroups } = useSelector((state) => state.groups);
  const [csvData, setCsvData] = useState("");
  const [addUserGroupsDialogOpen, setAddUserGroupsDialogOpen] = useState(false);
  const [addGroupsFormUsername, setAddGroupsFormUsername] = useState("");

  const { handleSubmit, errors, reset, control, getValues } = useForm();

  useEffect(() => {
    const fetchUsers = () => {
      dispatch(usersActions.fetchUsers());
    };
    if (!allUsers?.length) {
      fetchUsers();
    }
  }, [allUsers, dispatch]);

  if (
    !allUsers?.length ||
    !currentUser?.username?.length ||
    !allGroups?.length
  ) {
    return (
      <div>
        <CircularProgress />
      </div>
    );
  }

  if (
    !(
      currentUser.acls?.includes("System admin") ||
      currentUser.acls?.includes("Manage users")
    )
  ) {
    return <div>Access denied: Insufficient permissions.</div>;
  }

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.groups.length >= 1;
  };

  const handleAddUserToGroups = async (formData) => {
    const groupIDs = formData.groups.map((g) => g.id);
    const promises = groupIDs.map((gid) =>
      dispatch(
        groupsActions.addGroupUser({
          username: addGroupsFormUsername,
          admin: false,
          group_id: gid,
        })
      )
    );
    const results = await Promise.all(promises);
    if (results.every((result) => result.status === "success")) {
      dispatch(
        showNotification("User successfully added to specified group(s).")
      );
      reset({ groups: [] });
      setAddUserGroupsDialogOpen(false);
      dispatch(usersActions.fetchUsers());
      setAddGroupsFormUsername("");
    }
  };

  const handleClickRemoveUserFromGroup = async (username, group_id) => {
    const result = await dispatch(
      groupsActions.deleteGroupUser({ username, group_id })
    );
    if (result.status === "success") {
      dispatch(
        showNotification("User successfully removed from specified group.")
      );
      dispatch(usersActions.fetchUsers());
    }
  };

  const handleClickRemoveUserStreamAccess = async (user_id, stream_id) => {
    const result = await dispatch(
      streamsActions.deleteStreamUser({ user_id, stream_id })
    );
    if (result.status === "success") {
      dispatch(showNotification("Stream access successfully revoked."));
      dispatch(usersActions.fetchUsers());
    }
  };

  const handleClickAddUsers = async () => {
    let rows = PapaParse.parse(csvData.trim(), {
      delimiter: ",",
      skipEmptyLines: "greedy",
    }).data;
    rows = rows.map((row) => [
      row[0].trim(),
      PapaParse.parse(row[1].trim(), { delimiter: " " }).data[0],
      PapaParse.parse(row[2].trim(), { delimiter: " " }).data[0],
      PapaParse.parse(row[3].trim(), { delimiter: " " }).data[0],
    ]);
    const promises = rows.map((row) =>
      dispatch(
        inviteUsersActions.inviteUser({
          userEmail: row[0],
          streamIDs: row[1],
          groupIDs: row[2],
          groupAdmin: row[3],
        })
      )
    );
    const results = await Promise.all(promises);
    if (results.every((result) => result.status === "success")) {
      dispatch(showNotification("User(s) successfully invited."));
      setCsvData("");
    }
  };

  return (
    <>
      <Typography variant="h5">Manage users</Typography>
      <Paper elevation={1}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Username</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Groups</TableCell>
              <TableCell>Streams</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {allUsers.map((user) => (
              <TableRow key={user.id}>
                <TableCell>
                  {`${user.first_name ? user.first_name : ""} ${
                    user.last_name ? user.last_name : ""
                  }`}
                </TableCell>
                <TableCell>{user.username}</TableCell>
                <TableCell>{user.contact_email}</TableCell>
                <TableCell>
                  <IconButton
                    aria-label="add-group"
                    data-testid={`addUserGroupsButton${user.id}`}
                    onClick={() => {
                      setAddGroupsFormUsername(user.username);
                      setAddUserGroupsDialogOpen(true);
                    }}
                    size="small"
                  >
                    <AddCircleIcon color="disabled" />
                  </IconButton>
                  {user.groups
                    .filter((group) => !group.single_user_group)
                    .map((group) => (
                      <Chip
                        label={group.name}
                        onDelete={() => {
                          handleClickRemoveUserFromGroup(
                            user.username,
                            group.id
                          );
                        }}
                        key={group.id}
                        id={`deleteGroupUserButton_${user.id}_${group.id}`}
                      />
                    ))}
                </TableCell>
                <TableCell>
                  {user.streams.map((stream) => (
                    <Chip
                      label={stream.name}
                      onDelete={() => {
                        handleClickRemoveUserStreamAccess(user.id, stream.id);
                      }}
                      key={stream.id}
                      id={`deleteStreamUserButton_${user.id}_${stream.id}`}
                    />
                  ))}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      <br />
      {invitationsEnabled && (
        <>
          <Typography variant="h5">Bulk Invite New Users</Typography>
          <Paper elevation={1}>
            <Box p={5}>
              <code>
                User Email,Stream IDs,Group IDs,true/false indicating admin
                status for respective groups (list values space-separated, no
                spaces after commas)
              </code>
              <br />
              <TextareaAutosize
                placeholder={sampleCSVText}
                name="bulkInviteCSVInput"
                style={{ height: "15rem", width: "50rem" }}
                onChange={(e) => {
                  setCsvData(e.target.value);
                }}
                value={csvData}
              />
            </Box>
            <Box pl={5} pb={5}>
              <Button variant="contained" onClick={handleClickAddUsers}>
                Add Users
              </Button>
            </Box>
          </Paper>
        </>
      )}
      <Dialog
        open={addUserGroupsDialogOpen}
        onClose={() => {
          setAddUserGroupsDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>{`Add user ${addGroupsFormUsername} to selected groups:`}</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserToGroups)}>
            {!!errors.groups && (
              <FormValidationError message="Please select at least one group" />
            )}
            <Controller
              name="groups"
              id="addUsersFromGroupsSelect"
              as={
                <Autocomplete
                  multiple
                  options={allGroups.filter(
                    (g) =>
                      !allUsers
                        .filter((u) => u.username === addGroupsFormUsername)[0]
                        ?.groups?.map((gr) => gr.id)
                        ?.includes(g.id)
                  )}
                  getOptionLabel={(group) => group.name}
                  filterSelectedOptions
                  data-testid="addUsersFromGroupsSelect"
                  renderInput={(params) => (
                    <TextField
                      // eslint-disable-next-line react/jsx-props-no-spreading
                      {...params}
                      error={!!errors.groups}
                      variant="outlined"
                      label="Select Groups/Users"
                      data-testid="addUsersFromGroupsTextField"
                    />
                  )}
                />
              }
              control={control}
              onChange={([, data]) => data}
              rules={{ validate: validateGroups }}
              defaultValue={[]}
            />
            <div>
              <Button
                variant="contained"
                type="submit"
                name="submitAddFromGroupsButton"
                data-testid="submitAddFromGroupsButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UserManagement;
