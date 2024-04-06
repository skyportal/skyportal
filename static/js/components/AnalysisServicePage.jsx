import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import DeleteIcon from "@mui/icons-material/Delete";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import { showNotification } from "baselayer/components/Notifications";
import CircularProgress from "@mui/material/CircularProgress";
import MUIDataTable from "mui-datatables";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";
import NewAnalysisService from "./NewAnalysisService";

import * as analysisServicesActions from "../ducks/analysis_services";

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
  analysisServiceDeleteDisabled: {
    opacity: 0,
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
  const textClasses = textStyles();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [analysisServiceToDelete, setAnalysisServiceToDelete] = useState(null);

  const openDialog = (id) => {
    setDialogOpen(true);
    setAnalysisServiceToDelete(id);
  };

  const closeDialog = () => {
    setDialogOpen(false);
    setAnalysisServiceToDelete(null);
  };

  const deleteAnalysisService = () => {
    dispatch(
      analysisServicesActions.deleteAnalysisService(analysisServiceToDelete),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Analysis Service deleted"));
        closeDialog();
      }
    });
  };

  const columns = [
    {
      name: "display_name",
      label: "Service Name",
      options: {
        customBodyRenderLite: (dataIndex) => {
          const service = analysisServices[dataIndex];
          return (
            <div className={textClasses.primary}>{service.display_name}</div>
          );
        },
      },
    },
    {
      name: "description",
      label: "Description",
    },
    {
      name: "id",
      label: "Actions",
      options: {
        customBodyRenderLite: (dataIndex) => {
          const service = analysisServices[dataIndex];
          return deletePermission ? (
            <Button
              key={service.id}
              id="delete_button"
              onClick={() => openDialog(service.id)}
              style={{ cursor: "pointer" }}
              disabled={!deletePermission}
            >
              <DeleteIcon />
            </Button>
          ) : null;
        },
        sort: false,
      },
    },
  ];

  const options = {
    filterType: "checkbox",
    responsive: "standard",
    selectableRows: "none",
  };

  return (
    <div className={classes.root}>
      <MUIDataTable
        title="Analysis Services"
        data={analysisServices}
        columns={columns}
        options={options}
      />
      <ConfirmDeletionDialog
        deleteFunction={deleteAnalysisService}
        dialogOpen={dialogOpen}
        closeDialog={closeDialog}
        resourceName="analysis service"
      />
    </div>
  );
};

const AnalysisServicePage = () => {
  const { analysisServiceList } = useSelector(
    (state) => state.analysis_services,
  );

  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();
  const dispatch = useDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage Analysis Services");

  useEffect(() => {
    const getAnalysisServices = async () => {
      // Wait for the analysis services to update before setting
      // the new default form fields, so that the instruments list can
      // update

      await dispatch(analysisServicesActions.fetchAnalysisServices());
    };

    getAnalysisServices();
  }, [dispatch]);

  if (!analysisServiceList) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Analysis Services</Typography>
            <AnalysisServiceList
              analysisServices={analysisServiceList}
              deletePermission={permission}
            />
          </div>
        </Paper>
      </Grid>
      {permission && (
        <>
          <Grid item md={6} sm={12}>
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">Add a New Analysis Service</Typography>
                <NewAnalysisService />
              </div>
            </Paper>
          </Grid>
        </>
      )}
    </Grid>
  );
};

AnalysisServiceList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  analysisServices: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

export default AnalysisServicePage;
