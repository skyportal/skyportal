import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";
import DeleteIcon from "@mui/icons-material/Delete";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DialogContent from "@mui/material/DialogContent";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";
import StyledDataGrid from "./StyledDataGrid";

import NewRecurringAPI from "./NewRecurringAPI";

import * as recurringAPIsActions from "../ducks/recurring_apis";

const useStyles = makeStyles()((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
  },
}));

const RecurringAPIPage = () => {
  const { recurringAPIList } = useSelector((state) => state.recurring_apis);
  const [openNewForm, setOpenNewForm] = useState(false);

  const currentUser = useSelector((state) => state.profile);
  const { classes } = useStyles();
  const dispatch = useDispatch();

  const [recurringAPIToDelete, setRecurringAPIToDelete] = useState(null);

  const [dialogOpen, setDialogOpen] = useState(false);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage Recurring APIs");

  useEffect(() => {
    const getRecurringAPIs = async () => {
      await dispatch(recurringAPIsActions.fetchRecurringAPIs());
    };

    getRecurringAPIs();
  }, [dispatch]);

  const openDialog = (id) => {
    setDialogOpen(true);
    setRecurringAPIToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setRecurringAPIToDelete(null);
  };

  const deleteRecurringAPI = () => {
    dispatch(
      recurringAPIsActions.deleteRecurringAPI(recurringAPIToDelete),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("RecurringAPI deleted"));
        closeDialog();
      }
    });
  };

  const renderDelete = (params) => {
    const recurringAPI = params.row;
    return (
      <div>
        <IconButton
          id="delete_button"
          onClick={() => openDialog(recurringAPI.id)}
        >
          <DeleteIcon />
        </IconButton>
        <ConfirmDeletionDialog
          deleteFunction={deleteRecurringAPI}
          dialogOpen={dialogOpen}
          closeDialog={closeDialog}
          resourceName="recurring API"
        />
      </div>
    );
  };

  if (!recurringAPIList) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const columns = [
    { field: "id", headerName: "ID", width: 80 },
    {
      field: "owner_username",
      headerName: "Owner",
      flex: 1,
      minWidth: 120,
      valueGetter: (value, row) => row.owner?.username || "Unknown",
    },
    { field: "method", headerName: "Method", flex: 1, minWidth: 100 },
    { field: "endpoint", headerName: "Endpoint", flex: 1, minWidth: 160 },
    { field: "next_call", headerName: "Next Call", flex: 1, minWidth: 160 },
    {
      field: "payload",
      headerName: "Payload",
      flex: 1,
      minWidth: 160,
      valueGetter: (value, row) => JSON.stringify(row.payload) || "Unknown",
    },
    { field: "call_delay", headerName: "Delay (days)", flex: 1, minWidth: 110 },
    { field: "created_at", headerName: "Created at", flex: 1, minWidth: 160 },
    {
      field: "number_of_retries",
      headerName: "Number of retries",
      flex: 1,
      minWidth: 140,
    },
    {
      field: "active",
      headerName: "Active",
      width: 90,
      valueGetter: (value, row) => (row.active ? "Yes" : "No"),
    },
  ];

  if (permission) {
    columns.push({
      field: "delete",
      headerName: " ",
      width: 70,
      sortable: false,
      filterable: false,
      renderCell: renderDelete,
    });
  }

  const CustomToolbar = () => (
    <GridToolbarContainer>
      <GridToolbarColumnsButton />
      <IconButton
        name="new_recurring_api_form"
        onClick={() => setOpenNewForm(true)}
      >
        <AddIcon />
      </IconButton>
    </GridToolbarContainer>
  );

  return (
    <div className={classes.paperContent}>
      <Typography variant="h6">Recurring APIs</Typography>
      <Box sx={{ width: "100%" }}>
        <StyledDataGrid
          autoHeight
          rows={recurringAPIList}
          columns={columns}
          getRowId={(row) => row.id}
          initialState={{
            columns: { columnVisibilityModel: { created_at: false } },
          }}
          slots={{ toolbar: CustomToolbar }}
          showToolbar
        />
      </Box>
      <Dialog
        open={openNewForm}
        onClose={() => setOpenNewForm(false)}
        aria-labelledby="form-dialog-title"
      >
        <DialogTitle id="form-dialog-title">
          Add a New Recurring API
        </DialogTitle>
        <DialogContent>
          <NewRecurringAPI />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RecurringAPIPage;
