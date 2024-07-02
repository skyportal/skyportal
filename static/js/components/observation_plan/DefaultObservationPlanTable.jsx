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
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import MUIDataTable from "mui-datatables";
import { JSONTree } from "react-json-tree";

import { showNotification } from "baselayer/components/Notifications";
import * as defaultObservationPlansActions from "../../ducks/default_observation_plans";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewDefaultObservationPlan from "./NewDefaultObservationPlan";

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
  sortingCallback,
  deletePermission,
  hideTitle = false,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  const dispatch = useDispatch();

  const [setRowsPerPage] = useState(100);

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [defaultObservationPlanToDelete, setDefaultObservationPlanToDelete] =
    useState(null);

  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setDefaultObservationPlanToDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
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
        closeDeleteDialog();
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

  const renderPayload = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];
    const cellStyle = {
      whiteSpace: "nowrap",
    };

    return (
      <div style={cellStyle}>
        {default_observation_plan ? (
          <JSONTree data={default_observation_plan.payload} hideRoot />
        ) : (
          ""
        )}
      </div>
    );
  };

  const renderAutoSend = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];
    return (
      <div>
        {default_observation_plan &&
        Object.keys(default_observation_plan).includes("auto_send")
          ? default_observation_plan?.auto_send?.toString()
          : "false"}
      </div>
    );
  };

  const renderDelete = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];
    if (!deletePermission) {
      return null;
    }
    return (
      <div>
        <Button
          key={default_observation_plan.id}
          id="delete_button"
          classes={{
            root: classes.defaultObservationPlanDelete,
            disabled: classes.defaultObservationPlanDeleteDisabled,
          }}
          onClick={() => openDeleteDialog(default_observation_plan.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
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
      name: "payload",
      label: "Payload",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderPayload,
      },
    },
    {
      name: "auto_send",
      label: "Automatically send to queue?",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderAutoSend,
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
    customToolbar: () => (
      <IconButton
        name="new_default_observation_plan"
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
              title={hideTitle === true ? "" : "Default Observation Plans"}
              data={default_observation_plans || []}
              options={options}
              columns={columns}
            />
          </ThemeProvider>
        </StyledEngineProvider>
      </Paper>
      {newDialogOpen && (
        <Dialog
          open={newDialogOpen}
          onClose={closeNewDialog}
          style={{ position: "fixed" }}
          maxWidth="md"
        >
          <DialogTitle>New Default Observation Plan</DialogTitle>
          <DialogContent dividers>
            <NewDefaultObservationPlan onClose={closeNewDialog} />
          </DialogContent>
        </Dialog>
      )}
      <ConfirmDeletionDialog
        deleteFunction={deleteDefaultObservationPlan}
        dialogOpen={deleteDialogOpen}
        closeDialog={closeDeleteDialog}
        resourceName="default observation plan"
      />
    </div>
  );
};

DefaultObservationPlanTable.propTypes = {
  instruments: PropTypes.arrayOf(PropTypes.any).isRequired,
  telescopes: PropTypes.arrayOf(PropTypes.any).isRequired,
  default_observation_plans: PropTypes.arrayOf(PropTypes.any).isRequired,
  paginateCallback: PropTypes.func.isRequired,
  sortingCallback: PropTypes.func,
  deletePermission: PropTypes.bool,
  totalMatches: PropTypes.number,
  hideTitle: PropTypes.bool,
};

DefaultObservationPlanTable.defaultProps = {
  totalMatches: 0,
  sortingCallback: null,
  deletePermission: false,
  hideTitle: false,
};

export default DefaultObservationPlanTable;
