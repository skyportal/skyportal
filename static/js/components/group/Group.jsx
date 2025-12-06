import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { useTheme } from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";

import Button from "../Button";
import GroupUsers from "./GroupUsers";
import GroupFiltersStreams from "./GroupFiltersStreams";

import * as groupActions from "../../ducks/group";
import * as groupsActions from "../../ducks/groups";
import * as streamsActions from "../../ducks/streams";

const useStyles = makeStyles((theme) => ({
  nested: {
    paddingLeft: theme.spacing(2),
  },
  button_add: {
    maxWidth: "8.75rem",
  },
  selectEmpty: {
    width: "100%",
    marginTop: theme.spacing(2),
  },
}));

const Group = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const theme = useTheme();
  const navigate = useNavigate();
  const { id } = useParams();

  const [groupLoadError, setGroupLoadError] = useState("");
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const group = useSelector((state) => state.group);
  const currentUser = useSelector((state) => state.profile);
  const [dataFetched, setDataFetched] = useState(false);

  useEffect(() => {
    const fetchGroup = async () => {
      const result = await dispatch(groupActions.fetchGroup(id));
      if (result.status === "error") {
        setGroupLoadError(result.message);
      }
    };
    if (!dataFetched) {
      fetchGroup();
      setDataFetched(true);
    }
  }, [id, group, dataFetched, dispatch]);

  useEffect(() => {
    const fetchStreams = async () => {
      const data = await dispatch(streamsActions.fetchStreams());
      if (data.status === "error") {
        setGroupLoadError(data.message);
      }
    };
    fetchStreams();
  }, [currentUser, dispatch]);

  const handleDeleteGroup = async () => {
    const result = await dispatch(groupsActions.deleteGroup(group.id));
    if (result.status === "success") {
      dispatch(groupsActions.fetchGroups(true));
      setConfirmDeleteOpen(false);
      navigate("/groups");
    }
  };

  if (groupLoadError) return groupLoadError;

  if (!group) return <CircularProgress />;

  const isAdmin = (aUser) => {
    const currentGroupUser = group?.users?.filter(
      (group_user) => group_user.id === aUser.id,
    )[0];
    return (
      (currentGroupUser && currentGroupUser.admin) ||
      aUser.permissions?.includes("System admin") ||
      aUser.permissions?.includes("Manage groups")
    );
  };

  return (
    <div>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
        }}
      >
        <Box>
          <Typography variant="h5">
            <b>Group: </b>
            {group.name}
            {group.nickname ? ` (${group.nickname})` : ""}
          </Typography>
          {group.description && (
            <Typography sx={{ padding: 0.5 }}>{group.description}</Typography>
          )}
        </Box>
        {isAdmin(currentUser) && (
          <Button
            variant="outlined"
            color="error"
            onClick={() => setConfirmDeleteOpen(true)}
            sx={{ marginRight: 2 }}
          >
            Delete Group
          </Button>
        )}
      </Box>
      <Link to={`/group_sources/${group.id}`}>
        <Button secondary sx={{ my: 2 }}>
          Group sources
        </Button>
      </Link>
      <GroupUsers
        group={group}
        currentUser={currentUser}
        theme={theme}
        isAdmin={isAdmin}
      />
      <GroupFiltersStreams
        group={group}
        classes={classes}
        currentUser={currentUser}
        isAdmin={isAdmin}
        theme={theme}
      />
      <Dialog
        open={confirmDeleteOpen}
        onClose={() => setConfirmDeleteOpen(false)}
      >
        <DialogTitle>Delete Group?</DialogTitle>
        <DialogContent dividers>
          <DialogContentText>
            Are you sure you want to delete this Group?
            <br />
            <Typography variant="caption" color="warning.dark">
              (This will delete the group and all of its filters. All source
              data will be transferred to the Sitewide group.)
            </Typography>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            secondary
            autoFocus
            onClick={() => setConfirmDeleteOpen(false)}
          >
            Dismiss
          </Button>
          <Button primary onClick={handleDeleteGroup}>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default Group;
