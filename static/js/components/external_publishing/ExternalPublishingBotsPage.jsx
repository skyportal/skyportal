import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";
import { withTheme } from "@rjsf/core";

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

import validator from "@rjsf/validator-ajv8";

import MUIDataTable from "mui-datatables";
import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import TransferList from "../TransferList";

import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import * as externalPublishingActions from "../../ducks/externalPublishing";
import * as streamsActions from "../../ducks/streams";
import { userLabelWithAffiliations } from "../../utils/user";
import { CustomCheckboxWidgetMuiTheme } from "../CustomCheckboxWidget";
import Box from "@mui/material/Box";
import InfoIcon from "@mui/icons-material/Info";

const Form = withTheme(CustomCheckboxWidgetMuiTheme);

const useStyles = makeStyles(() => ({
  publishingBotList: {
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

const ExternalPublishingBotGroup = ({
  botGroup,
  groupsLookup,
  usersLookup,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const [owner, setOwner] = useState(botGroup.owner || false);
  const [autoPublish, setAutoPublish] = useState(
    botGroup.auto_publish || false,
  );
  const [autoPublishAllowBots, setAutoPublishAllowBots] = useState(
    botGroup.auto_publish_allow_bots || false,
  );
  const [left, setLeft] = useState([]);
  const [right, setRight] = useState([]);
  const [updating, setUpdating] = useState(false);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (open) {
      // we have the groupsLookup and usersLookup, that we'll use to find the users of the selected group
      const group = groupsLookup[botGroup.group_id];
      // the users in usersLookup have a "groups" field that contain all the groups that the user is part of
      const group_users = Object.values(usersLookup || {}).filter((user) =>
        // groups is a list of group objects, so we check if it includes a group with that id
        user.groups.some((userGroup) => userGroup.id === group.id),
      );

      // on the left are the users that are not auto publishers of the botGroup
      // meaning there are no auto publishers with user_id equal to the user.id
      const newLeft = group_users.filter(
        (user) =>
          !botGroup.auto_publishers.some(
            (autoPublisher) => autoPublisher.user_id === user.id,
          ),
      );
      // on the right are the users that are auto publishers of the botGroup
      // meaning there are auto publishers with user_id equal to the user.id
      const newRight = group_users.filter((user) =>
        botGroup.auto_publishers.some(
          (autoPublisher) => autoPublisher.user_id === user.id,
        ),
      );
      // we create an entry with only the user id and the label
      setLeft(
        newLeft
          .map((user) => ({
            id: user.id,
            label: userLabelWithAffiliations(user),
          }))
          .sort((a, b) => a?.label?.localeCompare(b?.label)),
      );
      setRight(
        newRight
          .map((user) => ({
            id: user.id,
            label: userLabelWithAffiliations(user),
          }))
          .sort((a, b) => a?.label?.localeCompare(b?.label)),
      );

      if (!initialized) {
        setInitialized(true);
      }
    }
  }, [botGroup, groupsLookup, usersLookup, open, initialized]);

  const updateGroup = async () => {
    setUpdating(true);
    if (
      owner !== botGroup.owner ||
      autoPublish !== botGroup.auto_publish ||
      autoPublishAllowBots !== botGroup.auto_publish_allow_bots
    ) {
      await dispatch(
        externalPublishingActions.editExternalPublishingBotGroup(
          botGroup.external_publishing_bot_id,
          botGroup.group_id,
          {
            owner,
            auto_publish: autoPublish,
            auto_publish_allow_bots: autoPublishAllowBots,
          },
        ),
      ).then((response) => {
        if (response.status === "success") {
          dispatch(
            showNotification(`Successfully updated group ${botGroup.group_id}`),
          );
          setOpen(false);
        } else {
          dispatch(
            showNotification(
              `Failed to update group ${botGroup.group_id}`,
              "error",
            ),
          );
        }
      });
    }

    // next we need to update the auto publishers
    // for that we want to find the users that are in the right list but not in the existing auto publishers
    // and the users that are in the existing auto publishers but not in the right list
    const newAutoPublishers = right.map((user) => user.id);
    const oldAutoPublishers = botGroup.auto_publishers.map(
      (auto_publisher) => auto_publisher.user_id,
    );
    const toAdd = newAutoPublishers.filter(
      (user) => !oldAutoPublishers.includes(user),
    );
    const toRemove = oldAutoPublishers.filter(
      (user) => !newAutoPublishers.includes(user),
    );

    // ADD
    if (toAdd?.length > 0) {
      await dispatch(
        externalPublishingActions.addExternalPublishingBotGroupAutoPublishers(
          botGroup.external_publishing_bot_id,
          botGroup.group_id,
          toAdd,
        ),
      ).then((response) => {
        if (response.status === "success") {
          dispatch(showNotification(`Successfully added auto publishers`));
        } else {
          dispatch(showNotification(`Failed to add auto publishers`, "error"));
        }
      });
    }

    // REMOVE
    if (toRemove?.length > 0) {
      await dispatch(
        externalPublishingActions.deleteExternalPublishingBotGroupAutoPublishers(
          botGroup.external_publishing_bot_id,
          botGroup.group_id,
          toRemove,
        ),
      ).then((response) => {
        if (response.status === "success") {
          dispatch(showNotification(`Successfully removed auto publishers`));
        } else {
          dispatch(
            showNotification(`Failed to remove auto publishers`, "error"),
          );
        }
      });
    }

    setUpdating(false);
  };

  const deleteGroup = () => {
    dispatch(
      externalPublishingActions.deleteExternalPublishingBotGroup(
        botGroup.external_publishing_bot_id,
        botGroup.group_id,
      ),
    ).then((response) => {
      if (response.status === "success") {
        dispatch(
          showNotification(
            `Group access to publishing bot removed successfully`,
          ),
        );
        setOpen(false);
      } else {
        dispatch(
          showNotification(
            `Failed to remove group access to publishing bot`,
            "error",
          ),
        );
      }
    });
  };

  return (
    <div key={botGroup.id}>
      <Chip
        size="small"
        label={groupsLookup[botGroup.group_id]?.name || "loading..."}
        className={botGroup.owner ? classes.groupChipOwner : classes.groupChip}
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
          Set group parameters and auto publishers
        </DialogTitle>
        <DialogContent>
          <InputLabel>Owner</InputLabel>
          <Switch
            checked={owner}
            onChange={(e) => setOwner(e.target.checked)}
          />
          <InputLabel>Auto publish</InputLabel>
          <Switch
            checked={autoPublish}
            onChange={(e) => setAutoPublish(e.target.checked)}
          />
          {autoPublish && (
            <>
              <InputLabel>Allow bots to auto publish</InputLabel>
              <Switch
                checked={autoPublishAllowBots}
                onChange={(e) => setAutoPublishAllowBots(e.target.checked)}
              />
            </>
          )}
          {initialized && (
            <div>
              <Typography>Auto publishers</Typography>
              <div style={{ padding: "0.5rem 0 1rem 0", minWidth: "70vw" }}>
                <TransferList
                  left={left}
                  right={right}
                  setLeft={setLeft}
                  setRight={setRight}
                  leftLabel="Group Users"
                  rightLabel="AutoPublishers"
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
          resourceName="publishing bot group"
        />
      </Dialog>
    </div>
  );
};

ExternalPublishingBotGroup.propTypes = {
  botGroup: PropTypes.shape({
    id: PropTypes.number,
    external_publishing_bot_id: PropTypes.number,
    group_id: PropTypes.number,
    owner: PropTypes.bool,
    auto_publish: PropTypes.bool,
    auto_publish_allow_bots: PropTypes.bool,
    auto_publishers: PropTypes.arrayOf(
      PropTypes.shape({
        botGroup_id: PropTypes.number,
        group_user_id: PropTypes.number,
        user_id: PropTypes.number,
      }),
    ),
  }).isRequired,
  groupsLookup: PropTypes.shape({}).isRequired,
  usersLookup: PropTypes.shape({}).isRequired,
};

const NewExternalPublishingBotGroup = ({
  externalPublishingBot,
  groupsLookup,
}) => {
  // here we want to have a chip with a + sign that opens a dialog to create a new externalPublishingBot group
  // the dialog will show a dropdown with all the groups that the user has access to
  // a switch to set the owner
  // and that are not already in the externalPublishingBot group list
  // and ADD and CANCEL buttons
  const [open, setOpen] = useState(false);
  const [group, setGroup] = useState(null);
  const [owner, setOwner] = useState(false);
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);

  const groupOptions = Object.values(groupsLookup).filter(
    (g) =>
      !externalPublishingBot.groups.some(
        (botGroup) => botGroup.group_id === g.id,
      ),
  );

  const handleAdd = () => {
    setLoading(true);
    dispatch(
      externalPublishingActions.addExternalPublishingBotGroup(
        externalPublishingBot.id,
        {
          group_id: group,
          owner,
          auto_publish: false,
          auto_publish_allow_bots: false,
        },
      ),
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

NewExternalPublishingBotGroup.propTypes = {
  externalPublishingBot: PropTypes.shape({
    id: PropTypes.number,
    groups: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        external_publishing_bot_id: PropTypes.number,
        group_id: PropTypes.number,
        owner: PropTypes.bool,
        auto_publish: PropTypes.bool,
        auto_publish_allow_bots: PropTypes.bool,
      }),
    ),
  }).isRequired,
  groupsLookup: PropTypes.shape({}).isRequired,
};

const ExternalPublishingBotCoauthor = ({
  external_publishing_bot_id,
  external_publishing_bot_coauthor,
  usersLookup,
}) => {
  const dispatch = useDispatch();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const user = usersLookup[external_publishing_bot_coauthor.user_id];

  const deleteCoauthor = () => {
    dispatch(
      externalPublishingActions.deleteExternalPublishingBotCoauthor(
        external_publishing_bot_id,
        user.id,
      ),
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
      {userLabelWithAffiliations(user)}
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
        resourceName="coauthor"
      />
    </>
  );
};

ExternalPublishingBotCoauthor.propTypes = {
  external_publishing_bot_id: PropTypes.number.isRequired,
  external_publishing_bot_coauthor: PropTypes.shape({
    id: PropTypes.number,
    botGroup_id: PropTypes.number,
    user_id: PropTypes.number,
  }).isRequired,
  usersLookup: PropTypes.shape({}).isRequired,
};

const NewExternalPublishingBotCoauthor = ({
  externalPublishingBot,
  usersLookup,
}) => {
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  const userOptions = Object.values(usersLookup).filter(
    (u) =>
      !externalPublishingBot.coauthors.some(
        (coauthor) => coauthor.user_id === u.id,
      ),
  );

  const handleAdd = () => {
    setLoading(true);
    dispatch(
      externalPublishingActions.addExternalPublishingBotCoauthor(
        externalPublishingBot.id,
        user,
      ),
    ).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification(`Successfully added user`));
      } else {
        dispatch(showNotification(`Failed to add user`, "error"));
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
                .sort((a, b) =>
                  userLabelWithAffiliations(a).localeCompare(
                    userLabelWithAffiliations(b),
                  ),
                )
                .map(
                  (
                    user, // eslint-disable-line no-shadow
                  ) => (
                    <MenuItem key={user.id} value={user.id}>
                      {userLabelWithAffiliations(user)}
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

NewExternalPublishingBotCoauthor.propTypes = {
  externalPublishingBot: PropTypes.shape({
    id: PropTypes.number,
    coauthors: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        external_publishing_bot_id: PropTypes.number,
        user_id: PropTypes.number,
      }),
    ),
  }).isRequired,
  usersLookup: PropTypes.shape({}).isRequired,
};

const ExternalPublishingBotsPage = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [openNewExternalPublishingBot, setOpenNewExternalPublishingBot] =
    useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(null);
  const [editDialogOpen, setEditDialogOpen] = useState(null);
  const [externalPublishingBotToManage, setExternalPublishingBotToManage] =
    useState(null);
  const [autoSendToTNS, setAutoSendToTNS] = useState(true);
  const [autoSendToHermes, setAutoSendToHermes] = useState(false);

  const groups = useSelector((state) => state.groups.userAccessible);
  const allGroups = useSelector((state) => state.groups.all);
  const { users: allUsers } = useSelector((state) => state.users);
  const { externalPublishingBotList } = useSelector(
    (state) => state.externalPublishingBots,
  );
  const { instrumentList } = useSelector((state) => state.instruments);
  const allowedInstrumentsForPublishing = useSelector(
    (state) => state.config.allowedInstrumentsForPublishing,
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
    first_and_last_detections: true,
    auto_publish_allow_archival: false,
  });

  const allowedInstruments = instrumentList.filter((instrument) =>
    (allowedInstrumentsForPublishing || []).includes(
      instrument.name?.toLowerCase(),
    ),
  );

  useEffect(() => {
    const fetchData = async () => {
      dispatch(streamsActions.fetchStreams());
      dispatch(externalPublishingActions.fetchExternalPublishingBots());
    };
    fetchData();
  }, [dispatch]);

  const externalPublishingBotListLookup = {};
  if (externalPublishingBotList) {
    externalPublishingBotList.forEach((externalPublishingBot) => {
      externalPublishingBotListLookup[externalPublishingBot.id] =
        externalPublishingBot;
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
    setDeleteDialogOpen(id);
    setExternalPublishingBotToManage(id);
  };

  const openEditDialog = (publishingBot) => {
    setSelectedFormData({
      bot_name: publishingBot?.bot_name || "",
      bot_id: publishingBot?.bot_id || "",
      source_group_id: publishingBot?.source_group_id || "",
      acknowledgments: publishingBot?.acknowledgments || "",
      api_key: "",
      owner_group_ids: (publishingBot?.owner_group_ids || []).map(
        (groupId) => groupsLookup[groupId].name,
      ),
      instrument_ids: (publishingBot?.instruments || []).map(
        (instrument) => instrument.id,
      ),
      stream_ids: (publishingBot?.streams || []).map((stream) => stream.id),
      publish_existing_tns_objects: publishingBot?.publish_existing_tns_objects,
      first_and_last_detections:
        publishingBot?.photometry_options?.first_and_last_detections,
      auto_publish_allow_archival:
        publishingBot?.photometry_options?.auto_publish_allow_archival,
    });
    setAutoSendToTNS(publishingBot?.auto_publish_to_tns);
    setAutoSendToHermes(publishingBot?.auto_publish_to_hermes);
    setExternalPublishingBotToManage(publishingBot.id);
    setEditDialogOpen(publishingBot.id);
  };

  const closeDeleteDialog = () => {
    setDeleteDialogOpen(null);
    setExternalPublishingBotToManage(null);
  };

  const closeEditDialog = () => {
    setEditDialogOpen(null);
    setExternalPublishingBotToManage(null);
  };

  const addExternalPublishingBot = (formData) => {
    const {
      bot_name,
      bot_id,
      source_group_id,
      api_key,
      acknowledgments,
      owner_group_ids,
      instrument_ids,
      stream_ids,
      testing,
      publish_existing_tns_objects,
      first_and_last_detections,
      auto_publish_allow_archival,
    } = formData.formData;

    if (api_key?.length === 0) {
      dispatch(
        showNotification(
          "Error adding publishing bot: A TNS API key is required to create a new bot.",
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
      _tns_altdata: {
        api_key,
      },
      owner_group_ids,
      instrument_ids,
      stream_ids,
      testing,
      publish_existing_tns_objects,
      photometry_options: {
        first_and_last_detections,
        auto_publish_allow_archival,
      },
      auto_publish_to_tns: autoSendToTNS,
      auto_publish_to_hermes: autoSendToHermes,
    };

    dispatch(externalPublishingActions.addExternalPublishingBot(data)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Publishing Bot added successfully."));
          setOpenNewExternalPublishingBot(false);
        } else {
          dispatch(showNotification("Error adding publishing Bot.", "error"));
        }
      },
    );
  };

  const deleteExternalPublishingBot = () => {
    dispatch(
      externalPublishingActions.deleteExternalPublishingBot(
        externalPublishingBotToManage,
      ),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Publishing Bot deleted successfully."));
        closeDeleteDialog();
      } else {
        dispatch(showNotification("Error deleting publishing Bot.", "error"));
      }
    });
  };

  const editExternalPublishingBot = (formData) => {
    const {
      bot_name,
      bot_id,
      source_group_id,
      api_key,
      acknowledgments,
      instrument_ids,
      stream_ids,
      testing,
      publish_existing_tns_objects,
      first_and_last_detections,
      auto_publish_allow_archival,
    } = formData.formData;

    const data = {
      bot_name,
      bot_id,
      source_group_id,
      acknowledgments,
      instrument_ids,
      stream_ids,
      testing,
      publish_existing_tns_objects,
      photometry_options: {
        first_and_last_detections,
        auto_publish_allow_archival,
      },
      auto_publish_to_tns: autoSendToTNS,
      auto_publish_to_hermes: autoSendToHermes,
    };

    if (api_key?.length > 0) {
      data._tns_altdata = {
        api_key,
      };
    }

    dispatch(
      externalPublishingActions.editExternalPublishingBot(
        externalPublishingBotToManage,
        data,
      ),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Publishing Bot edited successfully."));
        closeEditDialog();
      } else {
        dispatch(showNotification("Error editing publishing Bot.", "error"));
      }
    });
  };

  const renderDelete = (dataIndex) => {
    const externalPublishingBot = externalPublishingBotList[dataIndex];
    return (
      <div>
        <IconButton
          key={externalPublishingBot.id}
          id="delete_button"
          onClick={() => openDeleteDialog(externalPublishingBot.id)}
        >
          <DeleteIcon />
        </IconButton>
        <ConfirmDeletionDialog
          deleteFunction={deleteExternalPublishingBot}
          dialogOpen={deleteDialogOpen === dataIndex}
          closeDialog={closeDeleteDialog}
          resourceName="Publishing Bot"
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
        default:
          externalPublishingBotListLookup[externalPublishingBotToManage]
            ?.bot_name || "",
      },
      bot_id: {
        type: "number",
        title: "Bot ID",
        default:
          externalPublishingBotListLookup[externalPublishingBotToManage]
            ?.bot_id || "",
      },
      source_group_id: {
        type: "integer",
        title: "Source group ID",
        default:
          externalPublishingBotListLookup[externalPublishingBotToManage]
            ?.source_group_id || "",
      },
      api_key: {
        type: "string",
        title: "TNS API Key",
      },
      acknowledgments: {
        type: "string",
        title: "Acknowledgments",
        default:
          externalPublishingBotListLookup[externalPublishingBotToManage]
            ?.acknowledgments || "on behalf of ...",
        description:
          "Added at the end of the author list, e.g. 'First Last (Affiliation(s)) ...'",
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
        default:
          externalPublishingBotListLookup[externalPublishingBotToManage]
            ?.testing,
        description:
          "If enabled, the bot will not publish the data but only store the payload in the DB (useful for debugging).",
      },
      publish_existing_tns_objects: {
        type: "boolean",
        title: "Publish existing TNS objects",
        default:
          externalPublishingBotListLookup[externalPublishingBotToManage]
            ?.publish_existing_tns_objects || false,
        description:
          "If disabled, skips objects within 2 arcsec already in TNS. If enabled, publish if not yet submitted under this internal name.",
      },
      first_and_last_detections: {
        type: "boolean",
        title: "Mandatory first and last detection",
        default:
          externalPublishingBotListLookup[externalPublishingBotToManage]
            ?.photometry_options?.first_and_last_detections || true,
        description:
          "If enabled, the bot will only publish objects with both a first and last detection (i.e., at least two detections).",
      },
      auto_publish_allow_archival: {
        type: "boolean",
        title: "Allow archival auto-publishing",
        default:
          externalPublishingBotListLookup[externalPublishingBotToManage]
            ?.photometry_options?.auto_publish_allow_archival || false,
        description:
          "If enabled, the bot will submit auto-publish as archival if there is no non-detection prior to the first detection that can be published.",
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
    default:
      externalPublishingBotListLookup[externalPublishingBotToManage]
        ?.owner_group_ids || [],
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
    const externalPublishingBot = externalPublishingBotList[dataIndex];
    return (
      <div>
        <IconButton
          key={externalPublishingBot.id}
          id="edit_button"
          classes={{
            root: classes.externalPublishingBotEdit,
          }}
          onClick={() => openEditDialog(externalPublishingBot)}
        >
          <EditIcon />
        </IconButton>
        <Dialog
          open={editDialogOpen === externalPublishingBot.id}
          onClose={closeEditDialog}
          aria-labelledby="form-dialog-title"
        >
          <DialogTitle id="form-dialog-title">
            <Box
              display="flex"
              gap={1}
              style={{ alignItems: "center", justifyContent: "space-between" }}
            >
              Edit publishing bot
              <div
                style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
              >
                <Tooltip title="Select which services to automatically publish to if auto-publishing is enabled.">
                  <InfoIcon
                    fontSize="small"
                    style={{ cursor: "help", color: "#888" }}
                  />
                </Tooltip>
                <div>
                  <Chip
                    label="Tns"
                    clickable
                    onClick={() => setAutoSendToTNS(!autoSendToTNS)}
                    color={autoSendToTNS ? "primary" : "default"}
                    variant={autoSendToTNS ? "filled" : "outlined"}
                  />
                </div>
                <Tooltip
                  title={
                    <h3>
                      HERMES is a Message Exchange Service for Multi-Messenger
                      Astronomy. Click{" "}
                      <a
                        href="https://hermes.lco.global/about"
                        target="_blank"
                        rel="noopener noreferrer"
                        className={classes.tooltipLink}
                      >
                        here
                      </a>{" "}
                      for more information.
                    </h3>
                  }
                >
                  <Chip
                    label="Hermes"
                    clickable
                    onClick={() => setAutoSendToHermes(!autoSendToHermes)}
                    color={autoSendToHermes ? "primary" : "default"}
                    variant={autoSendToHermes ? "filled" : "outlined"}
                  />
                </Tooltip>
              </div>
            </Box>
          </DialogTitle>
          <DialogContent>
            <Form
              formData={selectedFormData}
              onChange={({ formData }) => setSelectedFormData(formData)}
              schema={editSchema}
              onSubmit={editExternalPublishingBot}
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
    // this button simply sends the user to the submissions page for the selected external publishing bot,
    // which url is /external_publishing/:bot_id/submissions, link should open in a new tab
    const externalPublishingBot = externalPublishingBotList[dataIndex];
    return (
      <Link
        to={`/external_publishing/${externalPublishingBot.id}/submissions`}
        key={externalPublishingBot.id}
        id="submissions_button"
        target="_blank"
      >
        <Tooltip title="View submissions">
          <IconButton
            classes={{
              root: classes.externalPublishingBotSubmissions,
            }}
          >
            <ChecklistIcon />
          </IconButton>
        </Tooltip>
      </Link>
    );
  };

  const renderBotName = (dataIndex) => {
    const externalPublishingBot = externalPublishingBotList[dataIndex];

    return (
      <div style={{ display: "flex", alignItems: "center" }}>
        {externalPublishingBot.testing === true && (
          <Tooltip
            title={
              <h2>
                This bot is currently in testing mode. It will not publish any
                data but will store the payload in the database instead (useful
                for debugging purposes).
              </h2>
            }
            placement="right"
          >
            <BugReportIcon style={{ color: "orange" }} />
          </Tooltip>
        )}
        <Typography variant="body1" style={{ marginLeft: "0.5rem" }}>
          {externalPublishingBot.bot_name}
        </Typography>
      </div>
    );
  };

  const renderCoauthors = (dataIndex) => {
    let external_publishing_bot_coauthors =
      externalPublishingBotList[dataIndex]?.coauthors || [];
    // sort them alphabetically
    external_publishing_bot_coauthors = external_publishing_bot_coauthors.sort(
      (a, b) => {
        const a_fullname = userLabelWithAffiliations(usersLookup[a.user_id]);
        const b_fullname = userLabelWithAffiliations(usersLookup[b.user_id]);
        if (a_fullname < b_fullname) {
          return -1;
        }
        if (a_fullname > b_fullname) {
          return 1;
        }
        return 0;
      },
    );

    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.2rem" }}>
        {external_publishing_bot_coauthors.map(
          (external_publishing_bot_coauthor) => (
            <ExternalPublishingBotCoauthor // eslint-disable-line react/jsx-key
              external_publishing_bot_id={
                externalPublishingBotList[dataIndex]?.id
              }
              external_publishing_bot_coauthor={
                external_publishing_bot_coauthor
              }
              usersLookup={usersLookup}
            />
          ),
        )}
        <NewExternalPublishingBotCoauthor
          externalPublishingBot={externalPublishingBotList[dataIndex]}
          usersLookup={usersLookup}
        />
      </div>
    );
  };

  const renderAcknowledgments = (dataIndex) => {
    const externalPublishingBot = externalPublishingBotList[dataIndex];
    return (
      <Tooltip
        title={`Added at the end of the author list, e.g. 'First Last (Affiliation(s)) ${
          externalPublishingBot?.acknowledgments || "..."
        }`}
        placement="top"
      >
        <Typography variant="body1">
          {externalPublishingBot.acknowledgments}
        </Typography>
      </Tooltip>
    );
  };

  const renderGroups = (dataIndex) => {
    let botGroups = externalPublishingBotList[dataIndex]?.groups || [];
    // order alphabetically by group name, then by owner status
    botGroups = botGroups.sort((a, b) => {
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
    botGroups = botGroups.sort((a, b) => {
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
        {botGroups.map((botGroup) => (
          <ExternalPublishingBotGroup // eslint-disable-line react/jsx-key
            botGroup={botGroup}
            groupsLookup={allGroupsLookup}
            usersLookup={usersLookup}
          />
        ))}
        <NewExternalPublishingBotGroup
          externalPublishingBot={externalPublishingBotList[dataIndex]}
          groupsLookup={groupsLookup}
        />
      </div>
    );
  };

  const renderPublishExisting = (dataIndex) => {
    const externalPublishingBot = externalPublishingBotList[dataIndex];
    return (
      <Tooltip
        title={
          externalPublishingBot.publish_existing_tns_objects
            ? "This bot will publish to TNS even if a matching object (within 2 arcsec) already exists, as long as it hasn't been published under the same internal name."
            : "This bot will not publish to TNS if a matching object (within 2 arcsec) already exists."
        }
        placement="left"
      >
        <Typography variant="body1">
          {externalPublishingBot.publish_existing_tns_objects ? "Yes" : "No"}
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
          const { instruments } = externalPublishingBotList[dataIndex];
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
          const { streams } = externalPublishingBotList[dataIndex]; // eslint-disable-line no-shadow
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
      name: "publish_existing_tns_objects",
      label: "Publish existing",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderPublishExisting,
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
        className={classes.publishingBotList}
        title="Publishing Bots"
        data={externalPublishingBotList.sort((a, b) =>
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
              name="new_externalPublishingBot"
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
                  publish_existing_tns_objects: false,
                  first_and_last_detections: true,
                });
                setAutoSendToTNS(true);
                setAutoSendToHermes(false);
                setOpenNewExternalPublishingBot(true);
              }}
            >
              <AddIcon />
            </IconButton>
          ),
        }}
      />
      <Dialog
        open={openNewExternalPublishingBot}
        onClose={() => {
          setOpenNewExternalPublishingBot(false);
        }}
        aria-labelledby="form-dialog-title"
      >
        <DialogTitle id="form-dialog-title">
          <Box
            display="flex"
            gap={1}
            style={{ alignItems: "center", justifyContent: "space-between" }}
          >
            Add Publishing Bot
            <div
              style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
              <Tooltip title="Select which services to automatically publish to if auto-publishing is enabled.">
                <InfoIcon
                  fontSize="small"
                  style={{ cursor: "help", color: "#888" }}
                />
              </Tooltip>
              <div>
                <Chip
                  label="Tns"
                  clickable
                  onClick={() => setAutoSendToTNS(!autoSendToTNS)}
                  color={autoSendToTNS ? "primary" : "default"}
                  variant={autoSendToTNS ? "filled" : "outlined"}
                />
              </div>
              <Tooltip
                title={
                  <h3>
                    HERMES is a Message Exchange Service for Multi-Messenger
                    Astronomy. Click{" "}
                    <a
                      href="https://hermes.lco.global/about"
                      target="_blank"
                      rel="noopener noreferrer"
                      className={classes.tooltipLink}
                    >
                      here
                    </a>{" "}
                    for more information.
                  </h3>
                }
              >
                <Chip
                  label="Hermes"
                  clickable
                  onClick={() => setAutoSendToHermes(!autoSendToHermes)}
                  color={autoSendToHermes ? "primary" : "default"}
                  variant={autoSendToHermes ? "filled" : "outlined"}
                />
              </Tooltip>
            </div>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Form
            formData={selectedFormData}
            onChange={({ formData }) => setSelectedFormData(formData)}
            schema={createSchema}
            onSubmit={addExternalPublishingBot}
            validator={validator}
            customValidate={validate}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ExternalPublishingBotsPage;
