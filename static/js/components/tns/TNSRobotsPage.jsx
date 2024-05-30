import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";

import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";
import ChecklistIcon from "@mui/icons-material/Checklist";
import BugReportIcon from "@mui/icons-material/BugReport";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Chip from "@mui/material/Chip";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import TransferList from "../TransferList";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import * as tnsrobotsActions from "../../ducks/tnsrobots";
import * as streamsActions from "../../ducks/streams";

const useStyles = makeStyles(() => ({
  tnsrobots: {
    width: "100%",
  },
  manageButtons: {
    display: "flex",
    flexDirection: "row",
  },
  groupChipOwner: {
    backgroundColor: "#457B9D",
    color: "white",
  },
  groupChip: {},
}));

const userLabel = (user) => {
  if (!user) {
    return "loading...";
  }
  if (user.is_bot === true) {
    return `${user.username}`;
  }
  if (!(user.first_name && user.last_name)) {
    return `${user.username}${
      user.affiliations?.length > 0 ? ` (${user.affiliations[0]})` : ""
    }`;
  }
  if (user.first_name && user.last_name) {
    // capitalize the first letter of first and last name
    const first_name =
      user?.first_name?.length > 1
        ? user.first_name.charAt(0).toUpperCase() + user.first_name.slice(1)
        : user?.first_name?.toUpperCase();
    const last_name =
      user?.last_name?.length > 1
        ? user.last_name.charAt(0).toUpperCase() + user.last_name.slice(1)
        : user?.last_name?.toUpperCase();

    // 1. remove affiliations that are empty strings or null
    // 2. capitalize the first letter of each affiliation
    // 3. sort the affiliations alphabetically (A-Z)
    let affiliations = (user?.affiliations || []).filter((aff) => aff);
    affiliations = affiliations.map((aff) =>
      aff?.length > 1
        ? aff.charAt(0).toUpperCase() + aff.slice(1)
        : aff.toUpperCase(),
    );
    affiliations.sort();

    return `${first_name} ${last_name}${
      affiliations?.length > 0 ? ` (${affiliations.join(", ")})` : ""
    }`;
  }
  return "loading...";
};

const TNSRobotGroup = ({ tnsrobot_group, groupsLookup, usersLookup }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const [owner, setOwner] = useState(tnsrobot_group.owner || false);
  const [autoreport, setAutoreport] = useState(
    tnsrobot_group.auto_report || false,
  );
  const [autoreport_allow_bots, setAutoreportAllowBots] = useState(
    tnsrobot_group.auto_report_allow_bots || false,
  );
  const [left, setLeft] = useState([]);
  const [right, setRight] = useState([]);
  const [updating, setUpdating] = useState(false);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (open) {
      // we have the groupsLookup and usersLookup, that we'll use to find the users of the selected group
      const group = groupsLookup[tnsrobot_group.group_id];
      // the users in usersLookup have a "groups" field that contain all the groups that the user is part of
      const group_users = Object.values(usersLookup || {}).filter((user) =>
        // groups is a list of group objects, so we check if it includes a group with that id
        user.groups.some((userGroup) => userGroup.id === group.id),
      );

      // on the left are the users that are not autoreporters of the tnsrobot_group
      // meaning there are no autoreporters with user_id equal to the user.id
      const newLeft = group_users.filter(
        (user) =>
          !tnsrobot_group.autoreporters.some(
            (autoreporter) => autoreporter.user_id === user.id,
          ),
      );
      // on the right are the users that are autoreporters of the tnsrobot_group
      // meaning there are autoreporters with user_id equal to the user.id
      const newRight = group_users.filter((user) =>
        tnsrobot_group.autoreporters.some(
          (autoreporter) => autoreporter.user_id === user.id,
        ),
      );
      // we create an entry with only the user id and the label
      setLeft(
        newLeft
          .map((user) => ({ id: user.id, label: userLabel(user) }))
          .sort((a, b) => a?.label?.localeCompare(b?.label)),
      );
      setRight(
        newRight
          .map((user) => ({ id: user.id, label: userLabel(user) }))
          .sort((a, b) => a?.label?.localeCompare(b?.label)),
      );

      if (!initialized) {
        setInitialized(true);
      }
    }
  }, [tnsrobot_group, groupsLookup, usersLookup, open, initialized]);

  const updateGroup = async () => {
    setUpdating(true);
    if (
      owner !== tnsrobot_group.owner ||
      autoreport !== tnsrobot_group.auto_report ||
      autoreport_allow_bots !== tnsrobot_group.auto_report_allow_bots
    ) {
      await dispatch(
        tnsrobotsActions.editTNSRobotGroup(
          tnsrobot_group.tnsrobot_id,
          tnsrobot_group.group_id,
          {
            owner,
            auto_report: autoreport,
            auto_report_allow_bots: autoreport_allow_bots,
          },
        ),
      ).then((response) => {
        if (response.status === "success") {
          dispatch(
            showNotification(
              `Successfully updated group ${tnsrobot_group.group_id}`,
            ),
          );
        } else {
          dispatch(
            showNotification(
              `Failed to update group ${tnsrobot_group.group_id}`,
              "error",
            ),
          );
        }
      });
    }

    // next we need to update the autoreporters
    // for that we want to find the users that are in the right list but not in the existing autoreporters
    // and the users that are in the existing autoreporters but not in the right list
    const newAutoreporters = right.map((user) => user.id);
    const oldAutoreporters = tnsrobot_group.autoreporters.map(
      (autoreporter) => autoreporter.user_id,
    );
    const toAdd = newAutoreporters.filter(
      (user) => !oldAutoreporters.includes(user),
    );
    const toRemove = oldAutoreporters.filter(
      (user) => !newAutoreporters.includes(user),
    );

    // ADD
    if (toAdd?.length > 0) {
      await dispatch(
        tnsrobotsActions.addTNSRobotGroupAutoReporters(
          tnsrobot_group.tnsrobot_id,
          tnsrobot_group.group_id,
          toAdd,
        ),
      ).then((response) => {
        if (response.status === "success") {
          dispatch(showNotification(`Successfully added autoreporters`));
        } else {
          dispatch(showNotification(`Failed to add autoreporters`, "error"));
        }
      });
    }

    // REMOVE
    if (toRemove?.length > 0) {
      await dispatch(
        tnsrobotsActions.deleteTNSRobotGroupAutoReporters(
          tnsrobot_group.tnsrobot_id,
          tnsrobot_group.group_id,
          toRemove,
        ),
      ).then((response) => {
        if (response.status === "success") {
          dispatch(showNotification(`Successfully removed autoreporters`));
        } else {
          dispatch(showNotification(`Failed to remove autoreporters`, "error"));
        }
      });
    }

    setUpdating(false);
  };

  const deleteGroup = () => {
    dispatch(
      tnsrobotsActions.deleteTNSRobotGroup(
        tnsrobot_group.tnsrobot_id,
        tnsrobot_group.group_id,
      ),
    ).then((response) => {
      if (response.status === "success") {
        dispatch(
          showNotification(`Successfully remove access to TNSRobot from group`),
        );
        setOpen(false);
      } else {
        dispatch(
          showNotification(
            `Failed to remove access to TNSRobot from group`,
            "error",
          ),
        );
      }
    });
  };

  return (
    <div key={tnsrobot_group.id}>
      <Chip
        size="small"
        label={groupsLookup[tnsrobot_group.group_id]?.name || "loading..."}
        className={
          tnsrobot_group.owner ? classes.groupChipOwner : classes.groupChip
        }
        onClick={() => {
          setOpen(true);
        }}
      />
      <Dialog
        open={open}
        onClose={() => {
          setOpen(false);
        }}
        aria-labelledby="form-dialog-title"
        maxWidth="lg"
      >
        <DialogTitle id="form-dialog-title">
          Set Group Parameters and Autoreporters
        </DialogTitle>
        <DialogContent>
          <InputLabel>Owner</InputLabel>
          <Switch
            checked={owner}
            onChange={(e) => setOwner(e.target.checked)}
          />
          <InputLabel>Autoreport</InputLabel>
          <Switch
            checked={autoreport}
            onChange={(e) => setAutoreport(e.target.checked)}
          />
          {autoreport && (
            <>
              <InputLabel>Allow bots to autoreport</InputLabel>
              <Switch
                checked={autoreport_allow_bots}
                onChange={(e) => setAutoreportAllowBots(e.target.checked)}
              />
            </>
          )}
          {initialized && (
            <div>
              <Typography>Autoreporters</Typography>
              <div style={{ padding: "0.5rem 0 1rem 0", minWidth: "70vw" }}>
                <TransferList
                  left={left}
                  right={right}
                  setLeft={setLeft}
                  setRight={setRight}
                  leftLabel="Group Users"
                  rightLabel="Autoreporters"
                />
              </div>
            </div>
          )}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-start",
              flexWrap: "wrap",
              gap: "0.5rem",
            }}
          >
            <Button primary onClick={updateGroup} disabled={updating}>
              Save
            </Button>

            <Button
              secondary
              onClick={() => setDeleteOpen(true)}
              disabled={updating}
            >
              Delete
            </Button>
            <Button onClick={() => setOpen(false)} disabled={updating}>
              Cancel
            </Button>
          </div>
        </DialogContent>
        <ConfirmDeletionDialog
          deleteFunction={deleteGroup}
          dialogOpen={deleteOpen}
          closeDialog={() => setDeleteOpen(false)}
          resourceName="TNSRobot Group"
        />
      </Dialog>
    </div>
  );
};

TNSRobotGroup.propTypes = {
  tnsrobot_group: PropTypes.shape({
    id: PropTypes.number,
    tnsrobot_id: PropTypes.number,
    group_id: PropTypes.number,
    owner: PropTypes.bool,
    auto_report: PropTypes.bool,
    auto_report_allow_bots: PropTypes.bool,
    autoreporters: PropTypes.arrayOf(
      PropTypes.shape({
        tnsrobot_group_id: PropTypes.number,
        group_user_id: PropTypes.number,
        user_id: PropTypes.number,
      }),
    ),
  }).isRequired,
  groupsLookup: PropTypes.shape({}).isRequired,
  usersLookup: PropTypes.shape({}).isRequired,
};

const NewTNSRobotGroup = ({ tnsrobot, groupsLookup }) => {
  // here we want to have a chip with a + sign that opens a dialog to create a new tnsrobot group
  // the dialog will show a drop down with all the groups that the user has access to
  // a switch to set the owner
  // and that are not already in the tnsrobot group list
  // and ADD and CANCEL buttons
  const [open, setOpen] = useState(false);
  const [group, setGroup] = useState(null);
  const [owner, setOwner] = useState(false);
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);

  const groupOptions = Object.values(groupsLookup).filter(
    (group) => !tnsrobot.groups.some((g) => g.group_id === group.id), // eslint-disable-line no-shadow
  );

  const handleAdd = () => {
    setLoading(true);
    dispatch(
      tnsrobotsActions.addTNSRobotGroup(tnsrobot.id, {
        group_id: group,
        owner,
        auto_report: false,
        auto_report_allow_bots: false,
      }),
    ).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification(`Successfully added group`));
      } else {
        dispatch(showNotification(`Failed to add group`, "error"));
      }
      setLoading(false);
      setOpen(false);
    });
  };

  return (
    <div>
      <Chip
        size="small"
        label="+"
        onClick={() => {
          setOpen(true);
        }}
      />
      <Dialog
        open={open}
        onClose={() => {
          setOpen(false);
        }}
        aria-labelledby="form-dialog-title"
      >
        <DialogTitle id="form-dialog-title">Add Group</DialogTitle>
        <DialogContent
          style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
        >
          <div>
            <InputLabel>Group</InputLabel>
            <Select
              value={group}
              onChange={(e) => setGroup(e.target.value)}
              style={{ minWidth: "20vw" }}
            >
              {groupOptions
                .sort((a, b) => a?.name?.localeCompare(b?.name))
                .map(
                  (
                    group, // eslint-disable-line no-shadow
                  ) => (
                    <MenuItem key={group.id} value={group.id}>
                      {group.name || "loading..."}
                    </MenuItem>
                  ),
                )}
            </Select>
          </div>
          <div>
            <InputLabel>Owner</InputLabel>
            <Switch
              checked={owner}
              onChange={(e) => setOwner(e.target.checked)}
            />
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              gap: "0.5rem",
              justifyContent: "space-between",
            }}
          >
            <Button primary onClick={handleAdd} disabled={loading}>
              Add
            </Button>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

NewTNSRobotGroup.propTypes = {
  tnsrobot: PropTypes.shape({
    id: PropTypes.number,
    groups: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        tnsrobot_id: PropTypes.number,
        group_id: PropTypes.number,
        owner: PropTypes.bool,
        auto_report: PropTypes.bool,
        auto_report_allow_bots: PropTypes.bool,
      }),
    ),
  }).isRequired,
  groupsLookup: PropTypes.shape({}).isRequired,
};

const TNSRobotCoauthor = ({ tnsrobot_id, tnsrobot_coauthor, usersLookup }) => {
  const dispatch = useDispatch();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const user = usersLookup[tnsrobot_coauthor.user_id];

  const deleteCoauthor = () => {
    dispatch(
      tnsrobotsActions.deleteTNSRobotCoauthor(tnsrobot_id, user.id),
    ).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification(`Successfully removed user`));
      } else {
        dispatch(showNotification(`Failed to remove user`, "error"));
      }
      setDeleteOpen(false);
    });
  };

  const label = (
    <div>
      {userLabel(user)}
      <IconButton onClick={() => setDeleteOpen(true)}>
        <DeleteIcon fontSize="small" />
      </IconButton>
    </div>
  );

  return (
    <>
      <Chip label={label} size="small" style={{ margin: "0.2rem" }} />
      <ConfirmDeletionDialog
        deleteFunction={deleteCoauthor}
        dialogOpen={deleteOpen}
        closeDialog={() => setDeleteOpen(false)}
        resourceName="TNSRobot Coauthor"
      />
    </>
  );
};

TNSRobotCoauthor.propTypes = {
  tnsrobot_id: PropTypes.number.isRequired,
  tnsrobot_coauthor: PropTypes.shape({
    id: PropTypes.number,
    tnsrobot_group_id: PropTypes.number,
    user_id: PropTypes.number,
  }).isRequired,
  usersLookup: PropTypes.shape({}).isRequired,
};

const NewTNSRobotCoauthor = ({ tnsrobot, usersLookup }) => {
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  const userOptions = Object.values(usersLookup).filter(
    (user) => !tnsrobot.coauthors.some((c) => c.user_id === user.id), // eslint-disable-line no-shadow
  );

  const handleAdd = () => {
    setLoading(true);
    dispatch(tnsrobotsActions.addTNSRobotCoauthor(tnsrobot.id, user)).then(
      (response) => {
        if (response.status === "success") {
          dispatch(showNotification(`Successfully added user`));
        } else {
          dispatch(showNotification(`Failed to add user`, "error"));
        }
        setLoading(false);
        setOpen(false);
      },
    );
  };

  return (
    <div>
      <Chip
        size="small"
        label="+"
        onClick={() => {
          setOpen(true);
        }}
      />
      <Dialog
        open={open}
        onClose={() => {
          setOpen(false);
        }}
        aria-labelledby="form-dialog-title"
      >
        <DialogTitle id="form-dialog-title">Add Coauthor</DialogTitle>
        <DialogContent
          style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
        >
          <div>
            <InputLabel>Coauthor</InputLabel>
            <Select
              value={user}
              onChange={(e) => setUser(e.target.value)}
              style={{ minWidth: "20vw" }}
            >
              {userOptions
                .sort((a, b) => userLabel(a).localeCompare(userLabel(b)))
                .map(
                  (
                    user, // eslint-disable-line no-shadow
                  ) => (
                    <MenuItem key={user.id} value={user.id}>
                      {userLabel(user)}
                    </MenuItem>
                  ),
                )}
            </Select>
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              gap: "0.5rem",
              justifyContent: "space-between",
            }}
          >
            <Button primary onClick={handleAdd} disabled={loading}>
              Add
            </Button>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

NewTNSRobotCoauthor.propTypes = {
  tnsrobot: PropTypes.shape({
    id: PropTypes.number,
    coauthors: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        tnsrobot_id: PropTypes.number,
        user_id: PropTypes.number,
      }),
    ),
  }).isRequired,
  usersLookup: PropTypes.shape({}).isRequired,
};

const TNSRobotsPage = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [openNewTNSRobot, setOpenNewTNSRobot] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [tnsrobotToManage, setTnsrobotToManage] = useState(null);

  const groups = useSelector((state) => state.groups.userAccessible);
  const allGroups = useSelector((state) => state.groups.all);
  const { users: allUsers } = useSelector((state) => state.users);
  const { tnsrobotList } = useSelector((state) => state.tnsrobots);
  const { instrumentList } = useSelector((state) => state.instruments);
  const tnsAllowedInstruments = useSelector(
    (state) => state.config.tnsAllowedInstruments,
  );
  const streams = useSelector((state) => state.streams);

  const [selectedFormData, setSelectedFormData] = useState({
    bot_name: "",
    bot_id: "",
    source_group_id: "",
    acknowledgments: "",
    api_key: "",
    owner_group_ids: [],
    instrument_ids: [],
    stream_ids: [],
    report_exceptions: false,
    first_and_last_detections: true,
    autoreport_allow_archival: false,
  });

  const allowedInstruments = instrumentList.filter((instrument) =>
    (tnsAllowedInstruments || []).includes(instrument.name?.toLowerCase()),
  );

  useEffect(() => {
    const fetchData = async () => {
      // Wait for the TNS robots to update before setting
      // the new default form fields, so that the TNS robots list can
      // update
      dispatch(streamsActions.fetchStreams());
      dispatch(tnsrobotsActions.fetchTNSRobots());
    };
    fetchData();
  }, [dispatch]);

  const tnsrobotListLookup = {};
  if (tnsrobotList) {
    tnsrobotList.forEach((tnsrobot) => {
      tnsrobotListLookup[tnsrobot.id] = tnsrobot;
    });
  }

  const groupsLookup = {};
  if (groups?.length > 0) {
    groups.forEach((group) => {
      groupsLookup[group.id] = group;
    });
  }

  // there are groups that the current user does not have access to,
  // but we still need their names for display
  const allGroupsLookup = {};
  if (allGroups?.length > 0) {
    allGroups.forEach((group) => {
      allGroupsLookup[group.id] = group;
    });
  }

  const usersLookup = {};
  if (allUsers && allUsers?.length > 0) {
    allUsers.forEach((user) => {
      usersLookup[user.id] = user;
    });
  }

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setTnsrobotToManage(id);
  };

  const openEditDialog = (id) => {
    setSelectedFormData({
      bot_name: tnsrobotListLookup[id]?.bot_name || "",
      bot_id: tnsrobotListLookup[id]?.bot_id || "",
      source_group_id: tnsrobotListLookup[id]?.source_group_id || "",
      acknowledgments: tnsrobotListLookup[id]?.acknowledgments || "",
      api_key: "",
      owner_group_ids: (tnsrobotListLookup[id]?.owner_group_ids || []).map(
        (groupId) => groupsLookup[groupId].name,
      ),
      instrument_ids: (tnsrobotListLookup[id]?.instruments || []).map(
        (instrument) => instrument.id,
      ),
      stream_ids: (tnsrobotListLookup[id]?.streams || []).map(
        (stream) => stream.id,
      ),
      report_existing: tnsrobotListLookup[id]?.report_existing,
      first_and_last_detections:
        tnsrobotListLookup[id]?.photometry_options?.first_and_last_detections,
      autoreport_allow_archival:
        tnsrobotListLookup[id]?.photometry_options?.autoreport_allow_archival,
    });
    setEditDialogOpen(true);
    setTnsrobotToManage(id);
  };

  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setTnsrobotToManage(null);
  };

  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setTnsrobotToManage(null);
  };

  const addTNSRobot = (formData) => {
    const {
      bot_name,
      bot_id,
      source_group_id,
      acknowledgments,
      api_key,
      owner_group_ids,
      instrument_ids,
      stream_ids,
      testing,
      report_existing,
      first_and_last_detections,
      autoreport_allow_archival,
    } = formData.formData;

    if (api_key?.length === 0) {
      dispatch(
        showNotification(
          "Error adding TNS Robot: API Key is required when creating a new robot.",
          "error",
        ),
      );
      return;
    }

    const data = {
      bot_name,
      bot_id,
      source_group_id,
      acknowledgments,
      _altdata: {
        api_key,
      },
      owner_group_ids,
      instrument_ids,
      stream_ids,
      testing,
      report_existing,
      photometry_options: {
        first_and_last_detections,
        autoreport_allow_archival,
      },
    };

    dispatch(tnsrobotsActions.addTNSRobot(data)).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("TNS Robot added successfully."));
        setOpenNewTNSRobot(false);
      } else {
        dispatch(showNotification("Error adding TNS Robot.", "error"));
      }
    });
  };

  const deleteTNSRobot = () => {
    dispatch(tnsrobotsActions.deleteTNSRobot(tnsrobotToManage)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("TNS Robot deleted successfully."));
          closeDeleteDialog();
        } else {
          dispatch(showNotification("Error deleting TNS Robot.", "error"));
        }
      },
    );
  };

  const editTNSRobot = (formData) => {
    const {
      bot_name,
      bot_id,
      source_group_id,
      api_key,
      acknowledgments,
      instrument_ids,
      stream_ids,
      testing,
      report_existing,
      first_and_last_detections,
      autoreport_allow_archival,
    } = formData.formData;

    const data = {
      bot_name,
      bot_id,
      source_group_id,
      acknowledgments,
      instrument_ids,
      stream_ids,
      testing,
      report_existing,
      photometry_options: {
        first_and_last_detections,
        autoreport_allow_archival,
      },
    };

    if (api_key?.length > 0) {
      // eslint-disable-next-line no-underscore-dangle
      data._altdata = {
        api_key,
      };
    }

    dispatch(tnsrobotsActions.editTNSRobot(tnsrobotToManage, data)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("TNS Robot edited successfully."));
          closeEditDialog();
        } else {
          dispatch(showNotification("Error editing TNS Robot.", "error"));
        }
      },
    );
  };

  const renderDelete = (dataIndex) => {
    const tnsrobot = tnsrobotList[dataIndex];
    return (
      <div>
        <IconButton
          key={tnsrobot.id}
          id="delete_button"
          onClick={() => openDeleteDialog(tnsrobot.id)}
        >
          <DeleteIcon />
        </IconButton>
        <ConfirmDeletionDialog
          deleteFunction={deleteTNSRobot}
          dialogOpen={deleteDialogOpen}
          closeDialog={closeDeleteDialog}
          resourceName="TNS Robot"
        />
      </div>
    );
  };

  const editSchema = {
    type: "object",
    properties: {
      bot_name: {
        type: "string",
        title: "Bot name",
        default: tnsrobotListLookup[tnsrobotToManage]?.bot_name || "",
      },
      bot_id: {
        type: "number",
        title: "Bot ID",
        default: tnsrobotListLookup[tnsrobotToManage]?.bot_id || "",
      },
      source_group_id: {
        type: "integer",
        title: "Source group ID",
        default: tnsrobotListLookup[tnsrobotToManage]?.source_group_id || "",
      },
      api_key: {
        type: "string",
        title: "API Key",
      },
      acknowledgments: {
        type: "string",
        title: "Acknowledgments",
        default:
          tnsrobotListLookup[tnsrobotToManage]?.acknowledgments ||
          "on behalf of ...",
        description:
          "Added at the end of the author list, e.g. 'First Last (Affiliation(s)) <insert_acknowledgments_here>'",
      },
      instrument_ids: {
        type: "array",
        items: {
          type: "integer",
          anyOf: (allowedInstruments || []).map((instrument) => ({
            enum: [instrument.id],
            type: "integer",
            title: instrument.name,
          })),
        },
        uniqueItems: true,
        default: [],
        title: "Instruments to restrict photometry to",
      },
      stream_ids: {
        type: "array",
        items: {
          type: "integer",
          anyOf: (streams || []).map((stream) => ({
            enum: [stream.id],
            type: "integer",
            title: stream.name,
          })),
        },
        uniqueItems: true,
        default: [],
        title: "Streams to restrict photometry to (optional)",
      },
      testing: {
        type: "boolean",
        title: "Testing Mode",
        default: tnsrobotListLookup[tnsrobotToManage]?.testing,
        description:
          "If enabled, the bot will not submit to TNS but only store the payload in the DB (useful for debugging).",
      },
      report_existing: {
        type: "boolean",
        title: "Report existing",
        default: tnsrobotListLookup[tnsrobotToManage]?.report_existing || false,
        description:
          "If disabled, the bot will not send a report to TNS if an object within 2 arcsec is already in the TNS database. If enabled, a report is sent as long as there are no reports with the same internal name.",
      },
      first_and_last_detections: {
        type: "boolean",
        title: "Mandatory first and last detection",
        default:
          tnsrobotListLookup[tnsrobotToManage]?.photometry_options
            ?.first_and_last_detections || true,
        description:
          "If enabled, the bot will not send a report to TNS if there is not both first and last detection (at least 2 detections required).",
      },
      autoreport_allow_archival: {
        type: "boolean",
        title: "Allow archival auto-reports",
        default:
          tnsrobotListLookup[tnsrobotToManage]?.photometry_options
            ?.autoreport_allow_archival || false,
        description:
          "If enabled, the bot will submit auto-reports as archival if there is no non-detection prior to the first detection that can be reported.",
      },
    },
    required: [
      "bot_name",
      "bot_id",
      "source_group_id",
      "acknowledgments",
      "instrument_ids",
      "first_and_last_detections",
    ],
  };

  // the create schema is the same as the edit schema, but with the owner_group_ids field
  const createSchema = JSON.parse(JSON.stringify(editSchema));
  createSchema.properties.owner_group_ids = {
    type: "array",
    items: {
      type: "integer",
      anyOf: (groups || [])
        .sort((a, b) => a?.name?.localeCompare(b?.name))
        .map((group) => ({
          enum: [group.id],
          type: "integer",
          title: group.name,
        })),
    },
    uniqueItems: true,
    default: tnsrobotListLookup[tnsrobotToManage]?.owner_group_ids || [],
    title: "Owner Group(s)",
  };
  createSchema.required.push("owner_group_ids");
  // change the default of testing to be true
  createSchema.properties.testing.default = true;

  const validate = (formData, errors) => {
    const { source_group_id } = formData;
    if (source_group_id !== "" && Number.isNaN(source_group_id)) {
      errors.source_group_id.addError("Source group ID must be a number.");
    }
    return errors;
  };

  const renderEdit = (dataIndex) => {
    const tnsrobot = tnsrobotList[dataIndex];
    return (
      <div>
        <IconButton
          key={tnsrobot.id}
          id="edit_button"
          classes={{
            root: classes.tnsrobotEdit,
          }}
          onClick={() => openEditDialog(tnsrobot.id)}
        >
          <EditIcon />
        </IconButton>
        <Dialog
          open={editDialogOpen}
          onClose={closeEditDialog}
          aria-labelledby="form-dialog-title"
        >
          <DialogTitle id="form-dialog-title">Edit TNS Robot</DialogTitle>
          <DialogContent>
            <Form
              formData={selectedFormData}
              onChange={({ formData }) => setSelectedFormData(formData)}
              schema={editSchema}
              onSubmit={editTNSRobot}
              liveValidate
              validator={validator}
              customValidate={validate}
            />
          </DialogContent>
        </Dialog>
      </div>
    );
  };

  const renderSubmissions = (dataIndex) => {
    // this button simply sends the user to the submissions page for the selected TNS Robot
    // which url is /tns_robot/:id/submissions
    // link should open in a new tab
    const tnsrobot = tnsrobotList[dataIndex];
    return (
      <Link
        to={`/tns_robot/${tnsrobot.id}/submissions`}
        key={tnsrobot.id}
        id="submissions_button"
        target="_blank"
      >
        <IconButton
          classes={{
            root: classes.tnsrobotSubmissions,
          }}
        >
          <ChecklistIcon />
        </IconButton>
      </Link>
    );
  };

  const renderBotName = (dataIndex) => {
    const tnsrobot = tnsrobotList[dataIndex];

    return (
      <div style={{ display: "flex", alignItems: "center" }}>
        {tnsrobot.testing === true && (
          <Tooltip
            title={
              <h2>
                This bot is in testing mode and will not submit to TNS but only
                store the payload in the database (useful for debugging). Click
                on the edit button to change this.
              </h2>
            }
            placement="right"
          >
            <BugReportIcon style={{ color: "orange" }} />
          </Tooltip>
        )}
        <Typography variant="body1" style={{ marginLeft: "0.5rem" }}>
          {tnsrobot.bot_name}
        </Typography>
      </div>
    );
  };

  const renderCoauthors = (dataIndex) => {
    let tnsrobot_coauthors = tnsrobotList[dataIndex]?.coauthors || [];
    // sort them alphabetically
    tnsrobot_coauthors = tnsrobot_coauthors.sort((a, b) => {
      const a_fullname = userLabel(usersLookup[a.user_id]);
      const b_fullname = userLabel(usersLookup[b.user_id]);
      if (a_fullname < b_fullname) {
        return -1;
      }
      if (a_fullname > b_fullname) {
        return 1;
      }
      return 0;
    });

    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.2rem" }}>
        {tnsrobot_coauthors.map((tnsrobot_coauthor) => (
          <TNSRobotCoauthor // eslint-disable-line react/jsx-key
            tnsrobot_id={tnsrobotList[dataIndex]?.id}
            tnsrobot_coauthor={tnsrobot_coauthor}
            usersLookup={usersLookup}
          />
        ))}
        <NewTNSRobotCoauthor
          tnsrobot={tnsrobotList[dataIndex]}
          usersLookup={usersLookup}
        />
      </div>
    );
  };

  const renderAcknowledgments = (dataIndex) => {
    const tnsrobot = tnsrobotList[dataIndex];
    return (
      <Tooltip
        title={`Added at the end of the author list, e.g. 'First Last (Affiliation(s)) ${
          tnsrobot?.acknowledgments || "<insert_acknowledgments_here>"
        }`}
        placement="top"
      >
        <Typography variant="body1">{tnsrobot.acknowledgments}</Typography>
      </Tooltip>
    );
  };

  const renderGroups = (dataIndex) => {
    let tnsrobot_groups = tnsrobotList[dataIndex]?.groups || [];
    // order alphabetically by group name, then by owner status
    tnsrobot_groups = tnsrobot_groups.sort((a, b) => {
      if (
        allGroupsLookup[a.group_id]?.name < allGroupsLookup[b.group_id]?.name
      ) {
        return -1;
      }
      if (
        allGroupsLookup[a.group_id]?.name > allGroupsLookup[b.group_id]?.name
      ) {
        return 1;
      }
      return 0;
    });
    tnsrobot_groups = tnsrobot_groups.sort((a, b) => {
      if (a.owner && !b.owner) {
        return -1;
      }
      if (!a.owner && b.owner) {
        return 1;
      }
      return 0;
    });

    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.2rem" }}>
        {tnsrobot_groups.map((tnsrobot_group) => (
          <TNSRobotGroup // eslint-disable-line react/jsx-key
            tnsrobot_group={tnsrobot_group}
            groupsLookup={allGroupsLookup}
            usersLookup={usersLookup}
          />
        ))}
        <NewTNSRobotGroup
          tnsrobot={tnsrobotList[dataIndex]}
          groupsLookup={groupsLookup}
        />
      </div>
    );
  };

  const renderReportExisting = (dataIndex) => {
    const tnsrobot = tnsrobotList[dataIndex];
    return (
      <Tooltip
        title={
          tnsrobot.report_existing
            ? "This bot will send a report even if an object is already on TNS (within 2 arcsec of the reported position), as long as there are no reports with the same internal name."
            : "This bot will not send a report if an object is already on TNS (within 2 arcsec of the reported position)."
        }
        placement="left"
      >
        <Typography variant="body1">
          {tnsrobot.report_existing ? "Yes" : "No"}
        </Typography>
      </Tooltip>
    );
  };

  const renderManage = (dataIndex) => {
    const deleteButton = renderDelete(dataIndex);
    const editButton = renderEdit(dataIndex);
    const submissionsButton = renderSubmissions(dataIndex);
    return (
      <div className={classes.manageButtons}>
        {submissionsButton}
        {editButton}
        {deleteButton}
      </div>
    );
  };

  const columns = [
    {
      name: "id",
      label: "ID",
      options: {
        display: false,
        filter: false,
        sort: false,
      },
    },
    {
      name: "bot_name",
      label: "Bot name",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: renderBotName,
      },
    },
    {
      name: "bot_id",
      label: "Bot ID",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "source_group_id",
      label: "Source group ID",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "groups",
      label: "Groups",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderGroups,
      },
    },
    {
      name: "coauthors",
      label: "Coauthors",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderCoauthors,
      },
    },
    {
      name: "acknowledgments",
      label: "Acknowledgments",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderAcknowledgments,
      },
    },
    {
      name: "instruments",
      label: "Instruments",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { instruments } = tnsrobotList[dataIndex];
          if (instruments?.length > 0) {
            return (
              <span>
                {instruments.map((instrument) => instrument.name).join(", ")}
              </span>
            );
          }
          return <span />;
        },
      },
    },
    {
      name: "streams",
      label: "Streams (optional)",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { streams } = tnsrobotList[dataIndex]; // eslint-disable-line no-shadow
          if (streams?.length > 0) {
            return (
              <span>{streams.map((stream) => stream.name).join(", ")}</span>
            );
          }
          return <span />;
        },
      },
    },
    {
      name: "report_existing",
      label: "Report existing",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderReportExisting,
      },
    },
    {
      name: "delete",
      label: " ",
      options: {
        customBodyRenderLite: renderManage,
      },
    },
  ];

  return (
    <div>
      <MUIDataTable
        className={classes.tnsrobots}
        title="TNS Robots"
        data={tnsrobotList.sort((a, b) =>
          a?.bot_name?.localeCompare(b?.bot_name),
        )}
        columns={columns}
        options={{
          selectableRows: "none",
          filter: false,
          print: false,
          download: false,
          viewColumns: false,
          pagination: false,
          search: false,
          customToolbar: () => (
            <IconButton
              name="new_tnsrobot"
              onClick={() => {
                setSelectedFormData({
                  bot_name: "",
                  bot_id: "",
                  source_group_id: "",
                  api_key: "",
                  owner_group_ids: [],
                  instrument_ids: [],
                  stream_ids: [],
                  acknowledgments: "on behalf of ...",
                  report_existing: false,
                  first_and_last_detections: true,
                });
                setOpenNewTNSRobot(true);
              }}
            >
              <AddIcon />
            </IconButton>
          ),
        }}
      />
      <Dialog
        open={openNewTNSRobot}
        onClose={() => {
          setOpenNewTNSRobot(false);
        }}
        aria-labelledby="form-dialog-title"
      >
        <DialogTitle id="form-dialog-title">Add TNS Robot</DialogTitle>
        <DialogContent>
          <Form
            formData={selectedFormData}
            onChange={({ formData }) => setSelectedFormData(formData)}
            schema={createSchema}
            onSubmit={addTNSRobot}
            liveValidate
            validator={validator}
            customValidate={validate}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TNSRobotsPage;

export { userLabel };
