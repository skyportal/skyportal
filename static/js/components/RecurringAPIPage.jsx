import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
import { showNotification } from "baselayer/components/Notifications";
import DeleteIcon from "@mui/icons-material/Delete";
import CircularProgress from "@mui/material/CircularProgress";
import MUIDataTable from "mui-datatables";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DialogContent from "@mui/material/DialogContent";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";

import NewRecurringAPI from "./NewRecurringAPI";

import * as recurringAPIsActions from "../ducks/recurring_apis";

const useStyles = makeStyles((theme) => ({
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
  const classes = useStyles();
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

  const renderDelete = (dataIndex) => {
    const recurringAPI = recurringAPIList[dataIndex];
    return (
      <div>
        <IconButton
          key={recurringAPI.id}
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
    {
      name: "id",
      label: "ID",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "owner.username",
      label: "Owner",
      options: {
        filter: true,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const api = recurringAPIList[dataIndex];
          return api.owner.username || "Unknown";
        },
      },
    },
    {
      name: "method",
      label: "Method",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "endpoint",
      label: "Endpoint",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "next_call",
      label: "Next Call",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "payload",
      label: "Payload",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: (dataIndex) => {
          const api = recurringAPIList[dataIndex];
          return JSON.stringify(api.payload) || "Unknown";
        },
      },
    },
    {
      name: "call_delay",
      label: "Delay (days)",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "created_at",
      label: "Created at",
      options: {
        filter: true,
        sort: true,
        display: false,
        sortThirdClickReset: true,
      },
    },
    {
      name: "number_of_retries",
      label: "Number of retries",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "active",
      label: "Active",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRender: (value) => (value ? "Yes" : "No"),
      },
    },
  ];

  if (permission) {
    columns.push({
      name: "delete",
      label: " ",
      options: {
        customBodyRenderLite: renderDelete,
      },
    });
  }

  const options = {
    filterType: "dropdown",
    responsive: "standard",
    selectableRows: "none",
    customToolbar: () => (
      <IconButton
        name="new_recurring_api_form"
        onClick={() => {
          setOpenNewForm(true);
        }}
      >
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div className={classes.paperContent}>
      <MUIDataTable
        title="Recurring APIs"
        data={recurringAPIList}
        columns={columns}
        options={options}
      />
      <Dialog
        open={openNewForm}
        onClose={() => {
          setOpenNewForm(false);
        }}
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
