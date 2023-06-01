import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";

import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";

import * as tnsrobotsActions from "../ducks/tnsrobots";

const useStyles = makeStyles(() => ({
  tnsrobots: {
    width: "100%",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
  manageButtons: {
    display: "flex",
    flexDirection: "row",
  },
}));

const TNSRobots = ({ group_id }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [openNewTNSRobot, setOpenNewTNSRobot] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [tnsrobotToManage, setTnsrobotToManage] = useState(null);

  const { tnsrobotList } = useSelector((state) => state.tnsrobots);

  useEffect(() => {
    const getTNSRobots = async () => {
      // Wait for the TNS robots to update before setting
      // the new default form fields, so that the TNS robots list can
      // update
      if (group_id) {
        await dispatch(
          tnsrobotsActions.fetchTNSRobots({
            groupID: group_id,
          })
        );
      }
    };
    getTNSRobots();
  }, [dispatch, group_id]);

  const tnsrobotListLookup = {};
  if (tnsrobotList) {
    tnsrobotList.forEach((tnsrobot) => {
      tnsrobotListLookup[tnsrobot.id] = tnsrobot;
    });
  }

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setTnsrobotToManage(id);
  };

  const openEditDialog = (id) => {
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
    const { bot_name, bot_id, source_group_id, auto_report, auto_reporters } =
      formData.formData;

    const auto_report_group_ids = [];
    if (auto_report) {
      auto_report_group_ids.push(group_id);
    }

    const data = {
      bot_name,
      bot_id,
      source_group_id,
      group_id,
      auto_report_group_ids,
      auto_reporters,
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
      }
    );
  };

  const editTNSRobot = (formData) => {
    const { bot_name, bot_id, source_group_id, auto_report, auto_reporters } =
      formData.formData;

    const auto_report_group_ids = [];
    if (auto_report) {
      auto_report_group_ids.push(group_id);
    }

    const data = {
      bot_name,
      bot_id,
      source_group_id,
      auto_report_group_ids,
      auto_reporters,
    };

    dispatch(tnsrobotsActions.editTNSRobot(tnsrobotToManage, data)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("TNS Robot edited successfully."));
          closeEditDialog();
        } else {
          dispatch(showNotification("Error editing TNS Robot.", "error"));
        }
      }
    );
  };

  const renderDelete = (dataIndex) => {
    const tnsrobot = tnsrobotList[dataIndex];
    return (
      <div>
        <Button
          key={tnsrobot.id}
          id="delete_button"
          classes={{
            root: classes.tnsrobotDelete,
          }}
          onClick={() => openDeleteDialog(tnsrobot.id)}
        >
          <DeleteIcon />
        </Button>
        <ConfirmDeletionDialog
          deleteFunction={deleteTNSRobot}
          dialogOpen={deleteDialogOpen}
          closeDialog={closeDeleteDialog}
          resourceName="TNS Robot"
        />
      </div>
    );
  };

  const schema = {
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
        type: "number",
        title: "Source group ID",
        default: tnsrobotListLookup[tnsrobotToManage]?.source_group_id || "",
      },
      auto_report: {
        type: "boolean",
        title: "Auto report",
        default:
          tnsrobotListLookup[tnsrobotToManage]?.auto_report_group_ids?.includes(
            group_id
          ) || false,
      },
      auto_reporters: {
        type: "string",
        title: "Auto reporters",
        default: tnsrobotListLookup[tnsrobotToManage]?.auto_reporters || "",
      },
    },
  };

  const validate = (formData, errors) => {
    const { bot_name, bot_id, source_group_id, auto_report, auto_reporters } =
      formData;

    if (bot_name === "" || bot_name === undefined || bot_name === null) {
      errors.bot_name.addError("Bot name is required.");
    }

    if (Number.isNaN(bot_id)) {
      errors.bot_id.addError("Bot ID must be a number.");
    } else if (bot_id === "" || bot_id === undefined || bot_id === null) {
      errors.bot_id.addError("Bot ID is required.");
    }

    if (Number.isNaN(source_group_id)) {
      errors.source_group_id.addError("Source group ID must be a number.");
    } else if (
      source_group_id === "" ||
      source_group_id === undefined ||
      source_group_id === null
    ) {
      errors.source_group_id.addError("Source group ID is required.");
    }

    if (
      auto_report &&
      (auto_reporters === "" ||
        auto_reporters === undefined ||
        auto_reporters === null)
    ) {
      errors.auto_reporters.addError(
        "Auto reporters is required if auto report is enabled."
      );
    }
    return errors;
  };

  const renderEdit = (dataIndex) => {
    const tnsrobot = tnsrobotList[dataIndex];
    return (
      <div>
        <Button
          key={tnsrobot.id}
          id="edit_button"
          classes={{
            root: classes.tnsrobotEdit,
          }}
          onClick={() => openEditDialog(tnsrobot.id)}
        >
          <EditIcon />
        </Button>
        <Dialog
          open={editDialogOpen}
          onClose={closeEditDialog}
          aria-labelledby="form-dialog-title"
        >
          <DialogTitle id="form-dialog-title">Edit TNS Robot</DialogTitle>
          <DialogContent>
            <Form
              schema={schema}
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

  const renderManage = (dataIndex) => {
    const deleteButton = renderDelete(dataIndex);
    const editButton = renderEdit(dataIndex);
    return (
      <div className={classes.manageButtons}>
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
      name: "auto_report_group_ids",
      label: "Auto Report",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const auto_report = "False";
          if (tnsrobotList[dataIndex].auto_report_group_ids?.length > 0) {
            // if the group_id is in the list of auto_report_group_ids, then it is True
            if (
              tnsrobotList[dataIndex].auto_report_group_ids.includes(group_id)
            ) {
              return "True";
            }
          }
          return <span>{auto_report}</span>;
        },
      },
    },
    {
      name: "auto_reporters",
      label: "Auto Reporters",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "delete",
      label: "Manage",
      options: {
        customBodyRenderLite: renderManage,
      },
    },
  ];

  return (
    <div className={classes.container}>
      <InputLabel id="tnsrobot-select-label">TNS Robots</InputLabel>
      <MUIDataTable
        className={classes.tnsrobots}
        title="TNS Robots"
        data={tnsrobotList}
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
            schema={schema}
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

TNSRobots.propTypes = {
  group_id: PropTypes.number.isRequired,
};

export default TNSRobots;
