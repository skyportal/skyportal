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
import Button from "@material-ui/core/Button";
import PapaParse from "papaparse";

import { showNotification } from "baselayer/components/Notifications";

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
  const [csvData, setCsvData] = useState("");

  useEffect(() => {
    const fetchUsers = () => {
      dispatch(usersActions.fetchUsers());
    };
    if (!allUsers?.length) {
      fetchUsers();
    }
  }, [allUsers, dispatch]);

  if (!allUsers?.length || !currentUser?.username?.length) {
    return (
      <div>
        <CircularProgress />
      </div>
    );
  }

  if (!currentUser.acls?.includes("System admin")) {
    return <div>Access denied: Insufficient permissions.</div>;
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
    </>
  );
};

export default UserManagement;
