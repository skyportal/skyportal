import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import DeleteIcon from "@mui/icons-material/Delete";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import { showNotification } from "baselayer/components/Notifications";
import CircularProgress from "@mui/material/CircularProgress";
import Button from "./Button";
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
  recurringAPIDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  recurringAPIDeleteDisabled: {
    opacity: 0,
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

export function recurringAPITitle(recurringAPI) {
  if (!recurringAPI?.endpoint) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${recurringAPI?.endpoint} / ${recurringAPI?.method}`;

  return result;
}

export function recurringAPIInfo(recurringAPI) {
  if (!recurringAPI?.next_call) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `Next call: ${recurringAPI.next_call} / Delay [days]: ${recurringAPI.call_delay} / Active: ${recurringAPI.active}`;

  return result;
}

const RecurringAPIList = ({ recurringAPIs, deletePermission }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();
  const groups = useSelector((state) => state.groups.all);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [recurringAPIToDelete, setRecurringAPIToDelete] = useState(null);
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

  return (
    <div className={classes.root}>
      <List component="nav">
        {recurringAPIs?.map((recurringAPI) => (
          <ListItem button key={recurringAPI.id}>
            <ListItemText
              primary={recurringAPITitle(recurringAPI)}
              secondary={recurringAPIInfo(recurringAPI, groups)}
              classes={textClasses}
            />
            <Button
              key={recurringAPI.id}
              id="delete_button"
              classes={{
                root: classes.recurringAPIDelete,
                disabled: classes.recurringAPIDeleteDisabled,
              }}
              onClick={() => openDialog(recurringAPI.id)}
              disabled={!deletePermission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteRecurringAPI}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="recurring API"
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const RecurringAPIPage = () => {
  const { recurringAPIList } = useSelector((state) => state.recurring_apis);

  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();
  const dispatch = useDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage Recurring APIs");

  useEffect(() => {
    const getRecurringAPIs = async () => {
      await dispatch(recurringAPIsActions.fetchRecurringAPIs());
    };

    getRecurringAPIs();
  }, [dispatch]);

  if (!recurringAPIList) {
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
            <Typography variant="h6">List of Recurring APIs</Typography>
            <RecurringAPIList
              recurringAPIs={recurringAPIList}
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
                <Typography variant="h6">Add a New Recurring API</Typography>
                <NewRecurringAPI />
              </div>
            </Paper>
          </Grid>
        </>
      )}
    </Grid>
  );
};

RecurringAPIList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  recurringAPIs: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

export default RecurringAPIPage;
