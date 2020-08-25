import React, { useEffect, useState } from "react";
import { useHistory, useParams } from "react-router-dom";
import PropTypes from "prop-types";

import { useDispatch, useSelector } from "react-redux";
import { makeStyles, useTheme } from "@material-ui/core/styles";
import Button from "@material-ui/core/Button";
import DeleteIcon from "@material-ui/icons/Delete";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemSecondaryAction from "@material-ui/core/ListItemSecondaryAction";
import ListItemText from "@material-ui/core/ListItemText";
import IconButton from "@material-ui/core/IconButton";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";

import Accordion from "@material-ui/core/Accordion";
import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import Typography from "@material-ui/core/Typography";

import Dialog from "@material-ui/core/Dialog";
import DialogActions from "@material-ui/core/DialogActions";
import DialogContent from "@material-ui/core/DialogContent";
import DialogContentText from "@material-ui/core/DialogContentText";
import DialogTitle from "@material-ui/core/DialogTitle";
import useMediaQuery from "@material-ui/core/useMediaQuery";
import TextField from "@material-ui/core/TextField";
import OpenInNewIcon from "@material-ui/icons/OpenInNew";

import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import FormHelperText from "@material-ui/core/FormHelperText";
import FormControl from "@material-ui/core/FormControl";
import Select from "@material-ui/core/Select";
import Divider from "@material-ui/core/Divider";
import Chip from "@material-ui/core/Chip";
import CircularProgress from "@material-ui/core/CircularProgress";

import { useForm, Controller } from "react-hook-form";
import { showNotification } from "baselayer/components/Notifications";

import * as groupActions from "../ducks/group";
import * as groupsActions from "../ducks/groups";
import * as streamsActions from "../ducks/streams";
import * as filterActions from "../ducks/filter";
import NewGroupUserForm from "./NewGroupUserForm";

const useStyles = makeStyles((theme) => ({
  padding_bottom: {
    paddingBottom: "2em",
  },
  paper: {
    width: "100%",
    padding: theme.spacing(1),
    textAlign: "left",
    color: theme.palette.text.primary,
  },
  nested: {
    paddingLeft: theme.spacing(2),
  },
  heading: {
    fontSize: theme.typography.pxToRem(17),
    fontWeight: 500,
  },
  accordion_details: {
    flexDirection: "column",
  },
  button_add: {
    maxWidth: "140px",
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
  const history = useHistory();

  const { register, handleSubmit, control } = useForm();

  const [groupLoadError, setGroupLoadError] = useState("");

  const [panelMembersExpanded, setPanelMembersExpanded] = React.useState(
    "panel-members"
  );
  const [panelStreamsExpanded, setPanelStreamsExpanded] = React.useState(
    "panel-streams"
  );
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const fullScreen = useMediaQuery(theme.breakpoints.down("md"));

  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const [addStreamOpen, setAddStreamOpen] = useState(false);

  const handleDialogClose = () => {
    setDialogOpen(false);
  };

  const handleClickDialogOpen = () => {
    setDialogOpen(true);
  };

  const handleConfirmDeleteDialogClose = () => {
    setConfirmDeleteOpen(false);
  };

  const handleAddStreamOpen = () => {
    setAddStreamOpen(true);
  };

  const handleAddStreamClose = () => {
    setAddStreamOpen(false);
  };

  const handlePanelMembersChange = (panel) => (event, isExpanded) => {
    setPanelMembersExpanded(isExpanded ? panel : false);
  };
  const handlePanelStreamsChange = (panel) => (event, isExpanded) => {
    setPanelStreamsExpanded(isExpanded ? panel : false);
  };

  const { id } = useParams();
  const loadedId = useSelector((state) => state.group.id);

  useEffect(() => {
    const fetchGroup = async () => {
      const data = await dispatch(groupActions.fetchGroup(id));
      if (data.status === "error") {
        setGroupLoadError(data.message);
      }
    };
    fetchGroup();
  }, [id, loadedId, dispatch]);

  const group = useSelector((state) => state.group);
  const currentUser = useSelector((state) => state.profile);

  // fetch streams:
  const streams = useSelector((state) => state.streams);

  useEffect(() => {
    const fetchStreams = async () => {
      const data = await dispatch(streamsActions.fetchStreams());
      if (data.status === "error") {
        setGroupLoadError(data.message);
      }
    };
    fetchStreams();
  }, [currentUser, dispatch]);

  // forms
  // add stream to group
  const onSubmitAddStream = async (data) => {
    const result = await dispatch(
      streamsActions.addGroupStream({
        group_id: group.id,
        stream_id: data.stream_id,
      })
    );
    if (result.status === "success") {
      dispatch(showNotification("Added stream to group"));
    }
    setAddStreamOpen(false);
  };
  // add filter to group
  const onSubmitAddFilter = async (data) => {
    const result = await dispatch(
      filterActions.addGroupFilter({
        name: data.filter_name,
        group_id: group.id,
        stream_id: data.filter_stream_id,
      })
    );
    if (result.status === "success") {
      dispatch(showNotification("Added filter to group"));
    }
    handleDialogClose();
    dispatch(groupActions.fetchGroup(loadedId));
  };

  if (groupLoadError) {
    return <div>{groupLoadError}</div>;
  }

  // renders
  if (!group) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  // currentUser may not have the "Group admin" role, but can still be the group admin?
  const currentGroupUser = group?.users?.filter(
    (group_user) => group_user.username === currentUser.username
  )[0];

  const isAdmin = (aUser, aGroup) =>
    aUser &&
    aGroup.group_users &&
    aGroup.group_users.filter(
      (group_user) => group_user.user_id === aUser.id
    )[0].admin;

  let numAdmins = 0;
  group?.group_users?.forEach((groupUser) => {
    if (groupUser?.admin) {
      numAdmins += 1;
    }
  });

  const groupStreamIds = group.streams?.map((stream) => stream.id);

  const isStreamIdInStreams = (sid) =>
    streams?.map((stream) => stream.id).includes(sid);

  return (
    <div>
      <Typography variant="h5" style={{ paddingBottom: 10 }}>
        Group:&nbsp;&nbsp;{group.name}
      </Typography>

      <Accordion
        expanded={panelMembersExpanded === "panel-members"}
        onChange={handlePanelMembersChange("panel-members")}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="panel-members-content"
          id="panel-members-header"
          style={{ borderBottom: "1px solid rgba(0, 0, 0, .125)" }}
        >
          <Typography className={classes.heading}>Members</Typography>
        </AccordionSummary>
        <AccordionDetails className={classes.accordion_details}>
          <List
            component="nav"
            aria-label="main mailbox folders"
            className={classes.paper}
            dense
          >
            {group?.users?.map((user) => (
              <ListItem
                button
                component={
                  currentUser.acls.includes("Manage users") ? "a" : false
                }
                key={user.id}
                href={`/user/${user.id}`}
              >
                <ListItemText primary={user.username} />
                {isAdmin(user, group) && (
                  <div
                    style={{ display: "inline-block" }}
                    id={`${user.id}-admin-chip`}
                  >
                    <Chip label="Admin" size="small" color="secondary" />
                    &nbsp;&nbsp;
                  </div>
                )}
                {(currentUser.roles.includes("Super admin") ||
                  (currentUser.roles.includes("Group admin") &&
                    isAdmin(currentGroupUser, group))) &&
                  isAdmin(user, group) &&
                  numAdmins > 1 && (
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        aria-label="delete"
                        onClick={() =>
                          dispatch(
                            groupsActions.deleteGroupUser({
                              username: user.username,
                              group_id: group.id,
                            })
                          )
                        }
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  )}
                {(currentUser.roles.includes("Super admin") ||
                  (currentUser.roles.includes("Group admin") &&
                    isAdmin(currentGroupUser, group))) &&
                  !isAdmin(user, group) && (
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        aria-label="delete"
                        onClick={() =>
                          dispatch(
                            groupsActions.deleteGroupUser({
                              username: user.username,
                              group_id: group.id,
                            })
                          )
                        }
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  )}
              </ListItem>
            ))}
          </List>
          <Divider />
          <div className={classes.paper}>
            {(currentUser.roles.includes("Super admin") ||
              (currentUser.roles.includes("Group admin") &&
                isAdmin(currentGroupUser, group))) && (
                <NewGroupUserForm group_id={group.id} />
            )}
          </div>
        </AccordionDetails>
      </Accordion>

      {streams?.length > 0 && (
        <Accordion
          expanded={panelStreamsExpanded === "panel-streams"}
          onChange={handlePanelStreamsChange("panel-streams")}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="panel-streams-content"
            id="panel-streams-header"
            style={{ borderBottom: "1px solid rgba(0, 0, 0, .125)" }}
          >
            <Typography className={classes.heading}>
              Alert streams and filters
            </Typography>
          </AccordionSummary>
          <AccordionDetails className={classes.accordion_details}>
            <List component="nav" className={classes.padding_bottom}>
              {group.streams?.map((stream) => (
                <div key={stream.name}>
                  <ListItem>
                    <ListItemText primary={stream.name} />
                  </ListItem>
                  <List component="nav" disablePadding>
                    {group.filters?.map(
                      (filter) =>
                        filter.stream_id === stream.id ? (
                          <ListItem
                            button
                            component="a"
                            key={filter.id}
                            href="#"
                          >
                            <ListItemText
                              className={classes.nested}
                              primary={filter.name}
                            />
                            {(currentUser.roles.includes("Super admin") ||
                              (currentUser.roles.includes("Group admin") &&
                                isAdmin(currentGroupUser, group))) && (
                                <ListItemSecondaryAction>
                                  <IconButton
                                    edge="end"
                                    aria-label="delete"
                                    onClick={async () => {
                                      const result = await dispatch(
                                        filterActions.deleteGroupFilter({
                                          filter_id: filter.id,
                                        })
                                      );
                                      if (result.status === "success") {
                                        dispatch(
                                          showNotification(
                                            "Deleted filter from group"
                                          )
                                        );
                                      }
                                      dispatch(groupActions.fetchGroup(loadedId));
                                    }}
                                  >
                                    <DeleteIcon />
                                  </IconButton>
                                </ListItemSecondaryAction>
                            )}
                          </ListItem>
                        ) : (
                          ""
                        )
                    )}
                  </List>
                </div>
              ))}
            </List>

            <div>
              {/* only Super admins can add streams to groups */}
              {currentUser.roles.includes("Super admin") &&
                streams?.length > 0 &&
                group?.streams?.length < streams?.length && (
                  <Button
                    variant="contained"
                    color="primary"
                    className={classes.button_add}
                    onClick={handleAddStreamOpen}
                    style={{ marginRight: 10 }}
                  >
                    Add stream
                  </Button>
                )}

              {(currentUser.roles.includes("Super admin") ||
                (currentUser.roles.includes("Group admin") &&
                  isAdmin(currentGroupUser, group))) &&
                group?.streams?.length > 0 && (
                  <Button
                    variant="contained"
                    color="primary"
                    className={classes.button_add}
                    onClick={handleClickDialogOpen}
                  >
                    Add filter
                  </Button>
                )}
            </div>
          </AccordionDetails>
        </Accordion>
      )}

      <br />
      {(currentUser.roles.includes("Super admin") ||
        (currentUser.roles.includes("Group admin") &&
          isAdmin(currentGroupUser, group))) && (
          <Button
            variant="contained"
            color="secondary"
            onClick={() => setConfirmDeleteOpen(true)}
          >
            Delete Group
          </Button>
      )}

      <Dialog
        fullScreen={fullScreen}
        open={addStreamOpen}
        onClose={handleAddStreamClose}
        aria-labelledby="responsive-dialog-title"
      >
        <form onSubmit={handleSubmit(onSubmitAddStream)}>
          <DialogTitle id="responsive-dialog-title">
            Add alert stream to group
          </DialogTitle>
          <DialogContent dividers>
            <FormControl required className={classes.selectEmpty}>
              <InputLabel name="alert-stream-select-required-label">
                Alert stream
              </InputLabel>
              <Controller
                labelId="alert-stream-select-required-label"
                name="stream_id"
                as={Select}
                defaultValue={0}
                control={control}
                rules={{ validate: isStreamIdInStreams }}
              >
                {streams?.map(
                  (stream) =>
                    // display only streams that are not yet added
                    !groupStreamIds.includes(stream.id) && (
                      <MenuItem value={stream.id}>{stream.name}</MenuItem>
                    )
                )}
              </Controller>
              <FormHelperText>Required</FormHelperText>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button
              type="submit"
              variant="contained"
              color="primary"
              className={classes.button_add}
            >
              Add
            </Button>
            <Button autoFocus onClick={handleAddStreamClose} color="primary">
              Dismiss
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Dialog
        fullScreen={fullScreen}
        open={dialogOpen}
        onClose={handleDialogClose}
        aria-labelledby="responsive-dialog-title"
      >
        <form onSubmit={handleSubmit(onSubmitAddFilter)}>
          <DialogTitle id="responsive-dialog-title">
            Create a new alert stream filter
          </DialogTitle>
          <DialogContent dividers>
            <DialogContentText>
              Please refer to the &nbsp;
              <a
                href="https://fritz-marshal.org/doc/user_guide.html#alert-filters-in-fritz"
                target="_blank"
                rel="noreferrer"
              >
                docs <OpenInNewIcon style={{ fontSize: "small" }} />
              </a>
              &nbsp; for an extensive guide on Alert filters in Fritz.
            </DialogContentText>
            <TextField
              autoFocus
              required
              margin="dense"
              name="filter_name"
              label="Filter Name"
              type="text"
              fullWidth
              inputRef={register({ required: true, minLength: 3 })}
            />
            <FormControl required className={classes.selectEmpty}>
              <InputLabel name="alert-stream-select-required-label">
                Alert stream
              </InputLabel>
              <Controller
                labelId="alert-stream-select-required-label"
                name="filter_stream_id"
                as={Select}
                defaultValue={0}
                control={control}
                rules={{ validate: isStreamIdInStreams }}
              >
                {group.streams?.map((stream) => (
                  <MenuItem key={stream.id} value={stream.id}>
                    {stream.name}
                  </MenuItem>
                ))}
              </Controller>
              <FormHelperText>Required</FormHelperText>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button
              variant="contained"
              color="primary"
              className={classes.button_add}
              type="submit"
            >
              Add
            </Button>
            <Button autoFocus onClick={handleDialogClose} color="primary">
              Dismiss
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Dialog
        fullWidth
        open={confirmDeleteOpen}
        onClose={handleConfirmDeleteDialogClose}
      >
        <DialogTitle>Delete Group?</DialogTitle>
        <DialogContent dividers>
          <DialogContentText>
            Are you sure you want to delete this Group?
            <br />
            Warning! This will delete the group and all of its filters. All
            source data will be transferred to the Site-wide group.
          </DialogContentText>
        </DialogContent>

        <DialogActions>
          <Button autoFocus onClick={() => setConfirmDeleteOpen(false)}>
            Dismiss
          </Button>
          <Button
            color="primary"
            onClick={() => {
              dispatch(groupsActions.deleteGroup(group.id));
              setConfirmDeleteOpen(false);
              history.push("/groups");
            }}
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

Group.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default Group;
