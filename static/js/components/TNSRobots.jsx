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
import * as streamsActions from "../ducks/streams";

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
    api_key: "",
    auto_report: false,
    auto_reporter_ids: [],
    auto_report_instrument_ids: [],
    auto_report_stream_ids: [],
  });

  const allowedInstruments = instrumentList.filter((instrument) =>
    (tnsAllowedInstruments || []).includes(instrument.name?.toLowerCase()),
  );

  useEffect(() => {
    const fetchData = async () => {
      // Wait for the TNS robots to update before setting
      // the new default form fields, so that the TNS robots list can
      // update
      if (group_id) {
        await dispatch(streamsActions.fetchStreams());
        await dispatch(
          tnsrobotsActions.fetchTNSRobots({
            groupID: group_id,
          }),
        );
      }
    };
    fetchData();
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
    setSelectedFormData({
      bot_name: tnsrobotListLookup[id]?.bot_name || "",
      bot_id: tnsrobotListLookup[id]?.bot_id || "",
      source_group_id: tnsrobotListLookup[id]?.source_group_id || "",
      api_key: "",
      auto_report:
        tnsrobotListLookup[id]?.auto_report_group_ids?.includes(group_id),
      auto_reporter_ids: tnsrobotListLookup[id]?.auto_reporters || [],
      auto_report_instrument_ids:
        tnsrobotListLookup[id]?.auto_report_instruments.map(
          (instrument) => instrument.id,
        ) || [],
      auto_report_stream_ids:
        tnsrobotListLookup[id]?.auto_report_streams.map(
          (stream) => stream.id,
        ) || [],
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
      api_key,
      auto_report,
      auto_reporter_ids,
      auto_report_instrument_ids,
      auto_report_stream_ids,
    } = formData.formData;

    const auto_report_group_ids = [];
    if (auto_report) {
      auto_report_group_ids.push(group_id);
    }

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
      _altdata: {
        api_key,
      },
      group_id,
      auto_report_group_ids,
      auto_reporter_ids,
      auto_report_instrument_ids,
      auto_report_stream_ids,
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
      auto_report,
      auto_reporter_ids,
      auto_report_instrument_ids,
      auto_report_stream_ids,
    } = formData.formData;

    const auto_report_group_ids = [];
    if (auto_report) {
      auto_report_group_ids.push(group_id);
    }

    const data = {
      bot_name,
      bot_id,
      source_group_id,
      auto_report_group_ids,
      auto_reporter_ids,
      auto_report_instrument_ids,
      auto_report_stream_ids,
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
        type: "integer",
        title: "Source group ID",
        default: tnsrobotListLookup[tnsrobotToManage]?.source_group_id || "",
      },
      api_key: {
        type: "string",
        title: "API Key",
      },
      auto_report: {
        type: "boolean",
        title: "Auto report",
        default: false,
      },
    },
    required: ["bot_name", "bot_id", "source_group_id"],
    dependencies: {
      auto_report: {
        oneOf: [
          {
            properties: {
              auto_report: {
                enum: [true],
              },
              auto_reporter_ids: {
                type: "array",
                items: {
                  type: "integer",
                  anyOf: (users || []).map((user) => ({
                    enum: [user.id],
                    type: "integer",
                    title: `${user.first_name} ${user.last_name}`,
                  })),
                },
                uniqueItems: true,
                default: [],
                title: "Auto reporters",
              },
              auto_report_instrument_ids: {
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
                title: "Instruments to restrict photometry to (optional)",
              },
              auto_report_stream_ids: {
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
            },
            required: ["auto_reporter_ids"],
          },
        ],
      },
    },
  };

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
              formData={selectedFormData}
              onChange={({ formData }) => setSelectedFormData(formData)}
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
      name: "auto_report_instruments",
      label: "Auto Instrument",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { auto_report_instruments } = tnsrobotList[dataIndex];
          if (auto_report_instruments?.length > 0) {
            return (
              <span>
                {auto_report_instruments
                  .map((instrument) => instrument.name)
                  .join(", ")}
              </span>
            );
          }
          return <span />;
        },
      },
    },
    {
      name: "auto_report_streams",
      label: "Auto Streams",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { auto_report_streams } = tnsrobotList[dataIndex];
          if (auto_report_streams?.length > 0) {
            return (
              <span>
                {auto_report_streams.map((stream) => stream.name).join(", ")}
              </span>
            );
          }
          return <span />;
        },
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
                setSelectedFormData({
                  bot_name: "",
                  bot_id: "",
                  source_group_id: "",
                  api_key: "",
                  auto_report: false,
                  auto_reporter_ids: [],
                  auto_report_instrument_ids: [],
                  auto_report_stream_ids: [],
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
