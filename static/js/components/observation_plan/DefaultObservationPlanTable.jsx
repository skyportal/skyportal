import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import { JSONTree } from "react-json-tree";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarQuickFilter,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";
import * as defaultObservationPlansActions from "../../ducks/default_observation_plans";
import StyledDataGrid from "../StyledDataGrid";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewDefaultObservationPlan from "./NewDefaultObservationPlan";

// Map each DataGrid column `field` to the field name the server expects for
// sorting. Columns absent from this map fall through to the field itself.
const SERVER_SORT_FIELD = {
  defaultObservationPlan: "defaultObservationPlan",
  payload: "payload",
  auto_send: "auto_send",
};

const DefaultObservationPlanTable = ({
  instruments,
  telescopes,
  default_observation_plans,
  paginateCallback,
  totalMatches,
  sortingCallback,
  deletePermission,
}) => {
  const dispatch = useDispatch();
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [defaultObservationPlanToDelete, setDefaultObservationPlanToDelete] =
    useState(null);
  const [sortModel, setSortModel] = useState([]);

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

  const getObservationPlanTitle = (default_observation_plan) => {
    const { allocation } = default_observation_plan;
    const { instrument_id } = allocation;
    const instrument = instruments?.filter((i) => i.id === instrument_id)[0];
    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];
    if (!instrument?.name || !telescope?.name) return "";

    return `${instrument.name}/${telescope.nickname} - ${default_observation_plan.default_plan_name}`;
  };

  const renderObservationPlanTitle = (params) =>
    getObservationPlanTitle(params.row) || null;

  const renderGcnEventFilters = (params) => {
    const default_observation_plan = params.row;
    if (!default_observation_plan?.filters) return null;

    return (
      <div style={{ whiteSpace: "nowrap" }}>
        <JSONTree data={default_observation_plan.filters} hideRoot />
      </div>
    );
  };

  const renderPayload = (params) => {
    const default_observation_plan = params.row;
    if (!default_observation_plan?.payload) return null;

    return (
      <div style={{ whiteSpace: "nowrap" }}>
        <JSONTree data={default_observation_plan.payload} hideRoot />
      </div>
    );
  };

  const renderAutoSend = (params) => {
    const default_observation_plan = params.row;
    if (!default_observation_plan?.auto_send) return <Chip label="No" />;

    return <Chip label="Yes" color="success" />;
  };

  const renderDelete = (params) => {
    if (!deletePermission) return null;
    return (
      <Button
        id="delete_button"
        onClick={() => openDeleteDialog(params.row.id)}
      >
        <DeleteIcon />
      </Button>
    );
  };

  const handleSortModelChange = (model) => {
    setSortModel(model);
    if (!model.length) {
      paginateCallback(1, 100, {});
      return;
    }
    const { field, sort } = model[0];
    sortingCallback({
      name: SERVER_SORT_FIELD[field] || field,
      direction: sort,
    });
  };

  const columns = [
    {
      field: "defaultObservationPlan",
      headerName: "Default Observation Plan",
      flex: 1,
      minWidth: 220,
      filterable: false,
      valueGetter: (value, row) => getObservationPlanTitle(row),
      renderCell: renderObservationPlanTitle,
    },
    {
      field: "Event Filters",
      headerName: "GCN Event Filters",
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      renderCell: renderGcnEventFilters,
    },
    {
      field: "payload",
      headerName: "Payload",
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      renderCell: renderPayload,
    },
    {
      field: "auto_send",
      headerName: "Automatically send to queue?",
      flex: 1,
      minWidth: 200,
      filterable: false,
      valueGetter: (value, row) => (row.auto_send ? "Yes" : "No"),
      renderCell: renderAutoSend,
    },
    {
      field: "delete",
      headerName: " ",
      width: 90,
      sortable: false,
      filterable: false,
      renderCell: renderDelete,
    },
  ];

  const CustomToolbar = () => (
    <GridToolbarContainer>
      <GridToolbarColumnsButton />
      <IconButton size="small" onClick={() => setNewDialogOpen(true)}>
        <AddIcon />
      </IconButton>
      <GridToolbarQuickFilter />
    </GridToolbarContainer>
  );

  return (
    <div>
      <Paper>
        <Typography variant="h6" style={{ padding: "0.5rem" }}>
          Default Observation Plans
        </Typography>
        <Box sx={{ width: "100%" }}>
          <StyledDataGrid
            autoHeight
            rows={default_observation_plans || []}
            columns={columns}
            getRowId={(row) => row.id}
            rowCount={totalMatches}
            sortingMode="server"
            sortModel={sortModel}
            onSortModelChange={handleSortModelChange}
            hideFooter
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
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
