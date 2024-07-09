import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Paper from "@mui/material/Paper";
import MUIDataTable from "mui-datatables";
import { JSONTree } from "react-json-tree";

import { showNotification } from "baselayer/components/Notifications";
import NewDefaultFollowupRequest from "./NewDefaultFollowupRequest";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import Button from "../Button";

import * as defaultFollowupRequestsActions from "../../ducks/default_followup_requests";

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  defaultFollowupRequestManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTablePagination: {
        styleOverrides: {
          toolbar: {
            flexFlow: "row wrap",
            justifyContent: "flex-end",
            padding: "0.5rem 1rem 0",
            [theme.breakpoints.up("sm")]: {
              // Cancel out small screen styling and replace
              padding: "0px",
              paddingRight: "2px",
              flexFlow: "row nowrap",
            },
          },
          tableCellContainer: {
            padding: "1rem",
          },
          selectRoot: {
            marginRight: "0.5rem",
            [theme.breakpoints.up("sm")]: {
              marginLeft: "0",
              marginRight: "2rem",
            },
          },
        },
      },
    },
  });

const DefaultFollowupRequestList = ({
  default_followup_requests,
  deletePermission,
  hideTitle = false,
}) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const theme = useTheme();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setDefaultFollowupRequestToDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setDefaultFollowupRequestToDelete(null);
  };

  const [dialogOpen, setDialogOpen] = useState(false);
  const [defaultFollowupRequestToDelete, setDefaultFollowupRequestToDelete] =
    useState(null);

  const deleteDefaultFollowupRequest = () => {
    dispatch(
      defaultFollowupRequestsActions.deleteDefaultFollowupRequest(
        defaultFollowupRequestToDelete,
      ),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Default follow-up request deleted"));
        closeDeleteDialog();
      }
    });
  };

  const renderInstrumentName = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const { allocation, default_followup_name } = default_followup_request;
    const { instrument_id } = allocation;
    const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

    return (
      <div>
        <Link to={`/allocation/${allocation.id}`} role="link">
          {instrument ? instrument.name : ""}
        </Link>
      </div>
    );
  };

  const renderTelescopeName = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const { allocation, default_followup_name } = default_followup_request;
    const { instrument_id } = allocation;
    const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

    const telescope_id = instrument?.telescope_id;
    const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

    return (
      <div>
        <Link to={`/allocation/${allocation.id}`} role="link">
          {telescope ? telescope.nickname : ""}
        </Link>
      </div>
    );
  };

  const renderGroup = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const { allocation, default_followup_name } = default_followup_request;

    const group = groups?.filter((g) => g.id === allocation.group_id)[0];

    return <div>{group ? group.name : ""}</div>;
  };

  const renderPayload = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const cellStyle = {
      whiteSpace: "nowrap",
    };

    return (
      <div style={cellStyle}>
        {default_followup_request ? (
          <JSONTree data={default_followup_request.payload} hideRoot />
        ) : (
          ""
        )}
      </div>
    );
  };

  const renderSourceFilter = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const cellStyle = {
      whiteSpace: "nowrap",
    };

    return (
      <div style={cellStyle}>
        {default_followup_request ? (
          <JSONTree data={default_followup_request.source_filter} hideRoot />
        ) : (
          ""
        )}
      </div>
    );
  };

  const renderManage = (dataIndex) => {
    if (!deletePermission) {
      return null;
    }
    const default_followup_request = default_followup_requests[dataIndex];
    return (
      <div className={classes.defaultFollowupRequestManage}>
        <Button
          key={`delete_${default_followup_request.id}`}
          id={`delete_button_${default_followup_request.id}`}
          onClick={() => openDeleteDialog(default_followup_request.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const columns = [
    {
      name: "instrument_name",
      label: "Instrument Name",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderInstrumentName,
      },
    },
    {
      name: "telescope_name",
      label: "Telescope Name",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderTelescopeName,
      },
    },
    {
      name: "default_followup_name",
      label: "Name",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "group",
      label: "Group",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderGroup,
      },
    },
    {
      name: "Payload",
      label: "Payload",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderPayload,
      },
    },
    {
      name: "Source Filter",
      label: "Source Filter",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderSourceFilter,
      },
    },
    {
      name: "manage",
      label: " ",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderManage,
      },
    },
  ];

  const options = {
    search: false,
    draggableColumns: { enabled: true },
    selectableRows: "none",
    elevation: 0,
    jumpToPage: true,
    pagination: true,
    filter: true,
    sort: true,
    customToolbar: () => (
      <IconButton
        name="new_default_followup_request"
        onClick={() => {
          openNewDialog();
        }}
      >
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div>
      <Paper className={classes.container}>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              title={!hideTitle ? "Default Follow-up Requests" : ""}
              data={default_followup_requests || []}
              options={options}
              columns={columns}
            />
          </ThemeProvider>
        </StyledEngineProvider>
      </Paper>
      <Dialog
        open={newDialogOpen}
        onClose={closeNewDialog}
        style={{ position: "fixed" }}
        maxWidth="md"
      >
        <DialogTitle>New Default Follow-up Request</DialogTitle>
        <DialogContent dividers>
          <NewDefaultFollowupRequest onClose={closeNewDialog} />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteDefaultFollowupRequest}
        dialogOpen={deleteDialogOpen}
        closeDialog={closeDeleteDialog}
        resourceName="default follow-up request"
      />
    </div>
  );
};

DefaultFollowupRequestList.propTypes = {
  default_followup_requests: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
  hideTitle: PropTypes.bool,
};

DefaultFollowupRequestList.defaultProps = {
  hideTitle: false,
};

export default DefaultFollowupRequestList;
