import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import makeStyles from "@mui/styles/makeStyles";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import MUIDataTable from "mui-datatables";
import CircularProgress from "@mui/material/CircularProgress";
import ReactJson from "react-json-view";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewAnalysisService from "./NewAnalysisService";

import * as analysisServicesActions from "../../ducks/analysis_services";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
  },
  analysisServiceDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  analysisServiceManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

export function analysisServiceTitle(analysisService) {
  if (!analysisService?.display_name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${analysisService?.display_name}`;

  return result;
}

export function analysisServiceInfo(analysisService) {
  if (!analysisService?.url) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const share_groups = [];
  analysisService.groups.forEach((share_group) => {
    share_groups.push(share_group.name);
  });

  let result = `Description: ${analysisService.description} / URL: ${analysisService.url}`;

  if (share_groups.length > 0) {
    result += "\r\n(";
    result += `Default Share Groups: ${share_groups.join(", ")}`;
    result += ")";
  }

  return result;
}

const AnalysisServiceList = ({ analysisServices, deletePermission }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [analysisServiceToViewDelete, setAnalysisServiceToViewDelete] =
    useState(null);
  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openDetailsDialog = (id) => {
    setDetailsDialogOpen(true);
    setAnalysisServiceToViewDelete(id);
  };
  const closeDetailsDialog = () => {
    setDetailsDialogOpen(false);
    setAnalysisServiceToViewDelete(null);
  };

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setAnalysisServiceToViewDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setAnalysisServiceToViewDelete(null);
  };

  const deleteAnalysisService = () => {
    dispatch(
      analysisServicesActions.deleteAnalysisService(
        analysisServiceToViewDelete,
      ),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("AnalysisService deleted"));
        closeDeleteDialog();
      }
    });
  };

  const renderContact = (dataIndex) => {
    const analysis_service = analysisServices[dataIndex];
    if (!analysis_service.contact_name) {
      return null;
    }
    let contactText = analysis_service.contact_name;
    if (analysis_service.contact_email) {
      contactText += ` (${analysis_service.contact_email})`;
    }
    return (
      <div>
        <Typography variant="body2">{contactText}</Typography>
      </div>
    );
  };

  const renderShareGroups = (dataIndex) => {
    const analysis_service = analysisServices[dataIndex];

    const group_names = (analysis_service?.groups || []).map(
      (group) => group.name,
    );

    return <div>{group_names.length > 0 ? group_names.join(", ") : ""}</div>;
  };

  const renderDetails = (dataIndex) => {
    const analysis_service = analysisServices[dataIndex];
    return (
      <IconButton
        key={`details_${analysis_service.id}`}
        id={`details_button_${analysis_service.id}`}
        onClick={() => openDetailsDialog(analysis_service.id)}
      >
        <HistoryEduIcon />
      </IconButton>
    );
  };

  const renderManage = (dataIndex) => {
    const analysis_service = analysisServices[dataIndex];
    if (!deletePermission) {
      return null;
    }
    return (
      <div className={classes.analysisServiceManage}>
        <Button
          key={`delete_${analysis_service.id}`}
          id={`delete_button_${analysis_service.id}`}
          onClick={() => openDeleteDialog(analysis_service.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const columns = [
    {
      name: "display_name",
      label: "Name",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "description",
      label: "Description",
      options: {
        filter: false,
        sort: false,
      },
    },
    {
      name: "version",
      label: "Version",
      options: {
        filter: false,
        sort: false,
      },
    },
    {
      name: "url",
      label: "URL",
      options: {
        filter: false,
        sort: false,
      },
    },
    {
      name: "contact",
      label: "Contact",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderContact,
      },
    },
    {
      name: "default_share_group",
      label: "Default Share Groups",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderShareGroups,
      },
    },
    {
      name: "details",
      label: "Details",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderDetails,
      },
    },
  ];

  if (deletePermission) {
    columns.push({
      name: "manage",
      label: " ",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderManage,
      },
    });
  }

  const options = {
    search: false,
    draggableColumns: { enabled: true },
    selectableRows: "none",
    elevation: 0,
    jumpToPage: true,
    serverSide: false,
    pagination: true,
    filter: true,
    sort: true,
  };

  if (deletePermission) {
    options.customToolbar = () => (
      <IconButton
        name="new_analysis_service"
        onClick={() => {
          openNewDialog();
        }}
      >
        <AddIcon />
      </IconButton>
    );
  }

  return (
    <div className={classes.root}>
      <Paper className={classes.container}>
        <MUIDataTable
          title={"Analysis Services"}
          data={analysisServices || []}
          options={options}
          columns={columns}
        />
        <Dialog
          open={newDialogOpen}
          onClose={closeNewDialog}
          style={{ position: "fixed" }}
          maxWidth="md"
        >
          <DialogTitle>New Analysis Service</DialogTitle>
          <DialogContent dividers>
            <NewAnalysisService onClose={closeNewDialog} />
          </DialogContent>
        </Dialog>
        <Dialog
          open={detailsDialogOpen && analysisServiceToViewDelete}
          onClose={closeDetailsDialog}
          style={{ position: "fixed" }}
          maxWidth="lg"
        >
          <DialogTitle>Analysis Service Details</DialogTitle>
          <DialogContent dividers>
            <ReactJson
              src={analysisServices[analysisServiceToViewDelete] || {}}
              name={false}
              displayDataTypes={false}
              displayObjectSize={false}
              enableClipboard={false}
              collapsed={false}
            />
          </DialogContent>
        </Dialog>
        <ConfirmDeletionDialog
          deleteFunction={deleteAnalysisService}
          dialogOpen={deleteDialogOpen && analysisServiceToViewDelete}
          closeDialog={closeDeleteDialog}
          resourceName="analysis service"
        />
      </Paper>
    </div>
  );
};

const AnalysisServicePage = () => {
  const { analysisServiceList } = useSelector(
    (state) => state.analysis_services,
  );

  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage Analysis Services");

  useEffect(() => {
    const getAnalysisServices = async () => {
      await dispatch(analysisServicesActions.fetchAnalysisServices());
    };

    getAnalysisServices();
  }, []);

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <AnalysisServiceList
          analysisServices={analysisServiceList || []}
          deletePermission={permission}
        />
      </Grid>
    </Grid>
  );
};

AnalysisServiceList.propTypes = {
  analysisServices: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

export default AnalysisServicePage;
