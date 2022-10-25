import React, { useState } from "react";
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
import NewInstrument from "./NewInstrument";
// eslint-disable-next-line import/no-cycle
import ModifyInstrument from "./ModifyInstrument";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";

import * as instrumentActions from "../ducks/instrument";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    padding: "1rem",
  },
  instrumentDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  instrumentDeleteDisabled: {
    opacity: 0,
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

export function instrumentTitle(instrument, telescopeList) {
  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${instrument?.name}/${telescope?.nickname}`;

  return result;
}

export function instrumentInfo(instrument, telescopeList) {
  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  let result = "";

  if (
    instrument?.filters ||
    instrument?.api_classname ||
    instrument?.api_classname_obsplan ||
    instrument?.fields
  ) {
    result += "( ";
    if (instrument?.filters) {
      const filters_str = instrument.filters.join(", ");
      result += `filters: ${filters_str}`;
    }
    if (instrument?.api_classname) {
      result += ` / API Classname: ${instrument?.api_classname}`;
    }
    if (instrument?.api_classname_obsplan) {
      result += ` / API Observation Plan Classname: ${instrument?.api_classname_obsplan}`;
    }
    if (instrument?.fields && instrument?.fields.length > 0) {
      result += ` / # of Fields: ${instrument?.fields.length}`;
    }
    result += " )";
  }

  return result;
}

const InstrumentList = ({ instruments, telescopes, deletePermission }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [instrumentToDelete, setInstrumentToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setInstrumentToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setInstrumentToDelete(null);
  };

  const deleteInstrument = () => {
    dispatch(instrumentActions.deleteInstrument(instrumentToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Instrument deleted"));
          closeDialog();
        }
      }
    );
  };

  return (
    <div className={classes.root}>
      <List component="nav">
        {instruments?.map((instrument) => (
          <ListItem button key={instrument.id}>
            <ListItemText
              primary={instrumentTitle(instrument, telescopes)}
              secondary={instrumentInfo(instrument, telescopes)}
              classes={textClasses}
            />
            <Button
              key={instrument.id}
              id="delete_button"
              classes={{
                root: classes.instrumentDelete,
                disabled: classes.instrumentDeleteDisabled,
              }}
              onClick={() => openDialog(instrument.id)}
              disabled={!deletePermission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteInstrument}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="instrument"
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const InstrumentPage = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const currentUser = useSelector((state) => state.profile);

  const permission =
    currentUser.permissions?.includes("Manage allocations") ||
    currentUser.permissions?.includes("System admin");

  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Instruments</Typography>
            <InstrumentList
              instruments={instrumentList}
              telescopes={telescopeList}
              deletePermission={permission}
            />
          </div>
        </Paper>
      </Grid>
      {permission && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New Instrument</Typography>
              <NewInstrument />
            </div>
          </Paper>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Modify an Instrument</Typography>
              <ModifyInstrument />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

InstrumentList.propTypes = {
  instruments: PropTypes.arrayOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types
  telescopes: PropTypes.arrayOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types
  deletePermission: PropTypes.bool.isRequired,
};

export default InstrumentPage;
