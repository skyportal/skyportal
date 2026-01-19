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
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Chip from "@mui/material/Chip";
import MUIDataTable from "mui-datatables";
import { JSONTree } from "react-json-tree";

import { showNotification } from "baselayer/components/Notifications";
import * as defaultObservationPlansActions from "../../ducks/default_observation_plans";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewDefaultObservationPlan from "./NewDefaultObservationPlan";

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
}) => {
  const theme = useTheme();
  const dispatch = useDispatch();
  const [setRowsPerPage] = useState(100);
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [defaultObservationPlanToDelete, setDefaultObservationPlanToDelete] =
    useState(null);

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
    if (!instrument?.name || !telescope?.name) return null;

    return `${instrument.name}/${telescope.nickname} - ${default_observation_plan.default_plan_name}`;
  };

  const renderGcnEventFilters = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];
    if (!default_observation_plan?.filters) return null;

    return (
      <div style={{ whiteSpace: "nowrap" }}>
        <JSONTree data={default_observation_plan.filters} hideRoot />
      </div>
    );
  };

  const renderPayload = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];
    if (!default_observation_plan?.payload) return null;

    return (
      <div style={{ whiteSpace: "nowrap" }}>
        <JSONTree data={default_observation_plan.payload} hideRoot />
      </div>
    );
  };

  const renderAutoSend = (dataIndex) => {
    const default_observation_plan = default_observation_plans[dataIndex];
    if (!default_observation_plan?.auto_send) return <Chip label="No" />;

    return <Chip label="Yes" color="success" />;
  };

  const renderDelete = (dataIndex) => {
    if (!deletePermission) return null;
    return (
      <Button
        id="delete_button"
        onClick={() =>
          openDeleteDialog(default_observation_plans[dataIndex].id)
        }
      >
        <DeleteIcon />
      </Button>
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
      <IconButton onClick={() => setNewDialogOpen(true)}>
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div>
      <Paper>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              title="Default Observation Plans"
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
          onClose={() => setNewDialogOpen(false)}
          maxWidth="md"
        >
          <DialogTitle>New Default Observation Plan</DialogTitle>
          <DialogContent dividers>
            <NewDefaultObservationPlan
              onClose={() => setNewDialogOpen(false)}
            />
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
};

DefaultObservationPlanTable.defaultProps = {
  totalMatches: 0,
  sortingCallback: null,
  deletePermission: false,
};

export default DefaultObservationPlanTable;
