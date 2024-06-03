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
import * as defaultObservationPlansActions from "../ducks/default_observation_plans";

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

const DefaultObservationPlanTable = ({
  instruments,
  telescopes,
  default_observation_plans,
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
  const [defaultObservationPlanToDelete, setDefaultObservationPlanToDelete] =
    useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setDefaultObservationPlanToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setDefaultObservationPlanToDelete(null);
  };

  const deleteDefaultObservationPlan = () => {
    dispatch(
      defaultObservationPlansActions.deleteDefaultObservationPlan(
        defaultObservationPlanToDelete,
      ),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Default observation plan deleted"));
        closeDialog();
      }
    });
  };

  const renderObservationPlanTitle = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];
    const { allocation } = default_observation_plan;
    const { instrument_id } = allocation;
    const instrument = instruments?.filter((i) => i.id === instrument_id)[0];

    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];

    return (
      <div>
        {instrument?.name && telescope?.name
          ? `${instrument.name}/${telescope.nickname} - ${default_observation_plan.default_plan_name}`
          : ""}
      </div>
    );
  };

  const renderGcnEventFilters = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan?.filters
          ? JSON.stringify(default_observation_plan.filters)
          : ""}
      </div>
    );
  };

  const renderFilters = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.filters
          : ""}
      </div>
    );
  };

  const renderProgram = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.program_id
          : ""}
      </div>
    );
  };

  const renderQueue = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.queue_name
          : ""}
      </div>
    );
  };

  const renderExposureTime = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.exposure_time
          : ""}
      </div>
    );
  };

  const renderScheduleType = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.schedule_type
          : ""}
      </div>
    );
  };

  const renderGalaxy = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.galaxy_catalog
          : ""}
      </div>
    );
  };

  const renderFilterStrategy = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.filter_strategy
          : ""}
      </div>
    );
  };

  const renderMaxAirmass = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.maximum_airmass
          : ""}
      </div>
    );
  };

  const renderSubprogram = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.subprogram_name
          : ""}
      </div>
    );
  };

  const renderScheduleStrategy = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.schedule_strategy
          : ""}
      </div>
    );
  };

  const renderProb = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.integrated_probability
          : ""}
      </div>
    );
  };

  const renderMinTimeDiff = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];

    return (
      <div>
        {default_observation_plan
          ? default_observation_plan.payload.minimum_time_difference
          : ""}
      </div>
    );
  };

  const renderDelete = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];
    return (
      <div>
        <Button
          key={default_observation_plan.id}
          id="delete_button"
          classes={{
            root: classes.defaultObservationPlanDelete,
            disabled: classes.defaultObservationPlanDeleteDisabled,
          }}
          onClick={() => openDialog(default_observation_plan.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
        <ConfirmDeletionDialog
          deleteFunction={deleteDefaultObservationPlan}
          dialogOpen={dialogOpen}
          closeDialog={closeDialog}
          resourceName="default observation plan"
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
      name: "defaultObservationPlan",
      label: "Default Observation Plan",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderObservationPlanTitle,
      },
    },
    {
      name: "Event Filters",
      label: "GCN Event Filters",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderGcnEventFilters,
      },
    },
    {
      name: "filters",
      label: "Filters",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderFilters,
      },
    },
    {
      name: "program",
      label: "Program",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderProgram,
      },
    },
    {
      name: "queue",
      label: "Queue",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderQueue,
      },
    },
    {
      name: "exposure_time",
      label: "Exposure Time",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderExposureTime,
      },
    },
    {
      name: "schedule_type",
      label: "Schedule Type",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderScheduleType,
      },
    },
    {
      name: "schedule_strategy",
      label: "Schedule Strategy",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderScheduleStrategy,
      },
    },
    {
      name: "galaxy_catalog",
      label: "Galaxy Catalog",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderGalaxy,
      },
    },
    {
      name: "filter_strategy",
      label: "Filter Strategy",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderFilterStrategy,
      },
    },
    {
      name: "max_airmass",
      label: "Maximum Airmass",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMaxAirmass,
      },
    },
    {
      name: "subprogram",
      label: "Subprogram",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderSubprogram,
      },
    },
    {
      name: "integrated_probability",
      label: "Integrated Probability",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderProb,
      },
    },
    {
      name: "min_time_diff",
      label: "Minimum Time Difference",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMinTimeDiff,
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
      {default_observation_plans ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title={!hideTitle ? "" : ""}
                data={default_observation_plans}
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

DefaultObservationPlanTable.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  instruments: PropTypes.arrayOf(PropTypes.any).isRequired,
  // eslint-disable-next-line react/forbid-prop-types
  telescopes: PropTypes.arrayOf(PropTypes.any).isRequired,
  // eslint-disable-next-line react/forbid-prop-types
  default_observation_plans: PropTypes.arrayOf(PropTypes.any).isRequired,
  paginateCallback: PropTypes.func.isRequired,
  sortingCallback: PropTypes.func,
  totalMatches: PropTypes.number,
  hideTitle: PropTypes.bool,
  deletePermission: PropTypes.bool.isRequired,
};

DefaultObservationPlanTable.defaultProps = {
  totalMatches: 0,
  sortingCallback: null,
  hideTitle: false,
};

export default DefaultObservationPlanTable;
