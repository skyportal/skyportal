import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";

import MUIDataTable from "mui-datatables";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";
import * as defaultSurveyEfficienciesActions from "../ducks/default_survey_efficiencies";

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
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

const DefaultSurveyEfficiencyTable = ({
  default_survey_efficiencies,
  paginateCallback,
  totalMatches,
  deletePermission,
  sortingCallback,
  hideTitle = false,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  const dispatch = useDispatch();

  const [setRowsPerPage] = useState(100);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [defaultSurveyEfficiencyToDelete, setDefaultSurveyEfficiencyToDelete] =
    useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setDefaultSurveyEfficiencyToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setDefaultSurveyEfficiencyToDelete(null);
  };

  const deleteDefaultSurveyEfficiency = () => {
    dispatch(
      defaultSurveyEfficienciesActions.deleteDefaultSurveyEfficiency(
        defaultSurveyEfficiencyToDelete,
      ),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Default survey efficiency deleted"));
        closeDialog();
      }
    });
  };

  const renderSurveyEfficiencyTitle = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];

    return (
      <div>
        {
          default_survey_efficiency.default_observationplan_request
            .default_plan_name
        }
      </div>
    );
  };

  const renderModelName = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];

    return (
      <div>
        {default_survey_efficiency
          ? default_survey_efficiency.payload.modelName
          : ""}
      </div>
    );
  };

  const renderMaxPhase = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];

    return (
      <div>
        {default_survey_efficiency
          ? default_survey_efficiency.payload.maximumPhase
          : ""}
      </div>
    );
  };

  const renderMinPhase = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];

    return (
      <div>
        {default_survey_efficiency
          ? default_survey_efficiency.payload.minimumPhase
          : ""}
      </div>
    );
  };

  const renderNumDetections = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];

    return (
      <div>
        {default_survey_efficiency
          ? default_survey_efficiency.payload.numberDetections
          : ""}
      </div>
    );
  };

  const renderNumInjections = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];

    return (
      <div>
        {default_survey_efficiency
          ? default_survey_efficiency.payload.numberInjections
          : ""}
      </div>
    );
  };

  const renderDetectionThreshold = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];

    return (
      <div>
        {default_survey_efficiency
          ? default_survey_efficiency.payload.detectionThreshold
          : ""}
      </div>
    );
  };

  const renderLocCumprob = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];

    return (
      <div>
        {default_survey_efficiency
          ? default_survey_efficiency.payload.localizationCumprob
          : ""}
      </div>
    );
  };

  const renderInjectionParameters = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];

    return (
      <div>
        {default_survey_efficiency
          ? default_survey_efficiency.payload.optionalInjectionParameters
          : ""}
      </div>
    );
  };

  const renderDelete = (dataIndex) => {
    const default_survey_efficiency = default_survey_efficiencies[dataIndex];
    return (
      <div>
        <Button
          key={default_survey_efficiency.id}
          id="delete_button"
          classes={{
            root: classes.defaultSurveyEfficiencyDelete,
            disabled: classes.defaultSurveyEfficiencyDeleteDisabled,
          }}
          onClick={() => openDialog(default_survey_efficiency.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
        <ConfirmDeletionDialog
          deleteFunction={deleteDefaultSurveyEfficiency}
          dialogOpen={dialogOpen}
          closeDialog={closeDialog}
          resourceName="default survey efficiency"
        />
      </div>
    );
  };

  const handleTableChange = (action, tableState) => {
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        setRowsPerPage(tableState.rowsPerPage);
        paginateCallback(
          tableState.page + 1,
          tableState.rowsPerPage,
          tableState.sortOrder,
        );
        break;
      case "sort":
        if (tableState.sortOrder.direction === "none") {
          paginateCallback(1, tableState.rowsPerPage, {});
        } else {
          sortingCallback(tableState.sortOrder);
        }
        break;
      default:
    }
  };

  const columns = [
    {
      name: "defaultSurveyEfficiency",
      label: "Default Plan",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderSurveyEfficiencyTitle,
      },
    },
    {
      name: "modelName",
      label: "Model Name",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderModelName,
      },
    },
    {
      name: "numInjections",
      label: "Number of Injections",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderNumInjections,
      },
    },
    {
      name: "maxPhase",
      label: "Maximum Phase (days)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMaxPhase,
      },
    },
    {
      name: "minPhase",
      label: "Minimum Phase (days)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMinPhase,
      },
    },
    {
      name: "numDetections",
      label: "Number of Detections",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderNumDetections,
      },
    },
    {
      name: "detectionThreshold",
      label: "Detection Threshold (sigma)",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderDetectionThreshold,
      },
    },
    {
      name: "cumProb",
      label: "Cumulative Probability",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderLocCumprob,
      },
    },
    {
      name: "injectionParameters",
      label: "Optional Injection Parameters",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderInjectionParameters,
      },
    },
    {
      name: "delete",
      label: " ",
      options: {
        customBodyRenderLite: renderDelete,
      },
    },
  ];

  const options = {
    search: false,
    selectableRows: "none",
    elevation: 0,
    onTableChange: handleTableChange,
    jumpToPage: true,
    serverSide: true,
    pagination: false,
    count: totalMatches,
    filter: true,
    sort: true,
  };

  return (
    <div>
      {default_survey_efficiencies ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title={!hideTitle ? "" : ""}
                data={default_survey_efficiencies}
                options={options}
                columns={columns}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </Paper>
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

DefaultSurveyEfficiencyTable.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  default_survey_efficiencies: PropTypes.arrayOf(PropTypes.any).isRequired,
  paginateCallback: PropTypes.func.isRequired,
  sortingCallback: PropTypes.func,
  totalMatches: PropTypes.number,
  hideTitle: PropTypes.bool,
  deletePermission: PropTypes.bool.isRequired,
};

DefaultSurveyEfficiencyTable.defaultProps = {
  totalMatches: 0,
  sortingCallback: null,
  hideTitle: false,
};

export default DefaultSurveyEfficiencyTable;
