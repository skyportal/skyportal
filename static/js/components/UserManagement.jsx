import React, { useEffect } from "react";
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

import { showNotification } from "baselayer/components/Notifications";

import * as groupsActions from "../ducks/groups";
import * as usersActions from "../ducks/users";
import * as streamsActions from "../ducks/streams";

const UserManagement = () => {
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const { allUsers } = useSelector((state) => state.users);

  useEffect(() => {
    const fetchUsers = () => {
      dispatch(usersActions.fetchUsers());
    };
    if (!allUsers?.length) {
      fetchUsers();
    }
  }, [allUsers, dispatch]);

  if (!currentUser.acls?.includes("System admin")) {
    return <div>Access denied: Insufficient permissions.</div>;
  }

  if (!allUsers?.length || !currentUser?.username?.length) {
    console.log(
      "!allUsers?.length:",
      !allUsers?.length,
      "!currentUser?.username?.length",
      !currentUser?.username?.length
    );
    console.log("allUsers:", allUsers);
    console.log("currentUser:", currentUser);
    return (
      <div>
        <CircularProgress />
      </div>
    );
  }

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

  const handleClickRemoveUserStreamAccess = async (user_id, group_id) => {
    const result = await dispatch(
      streamsActions.deleteUserStream({ user_id, group_id })
    );
    if (result.status === "success") {
      dispatch(showNotification("Stream access successfully revoked."));
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
                    />
                  ))}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </>
  );
};

export default UserManagement;
