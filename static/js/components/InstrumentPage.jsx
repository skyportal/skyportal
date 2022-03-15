import React from "react";
import { useSelector } from "react-redux";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import PropTypes from "prop-types";
import CircularProgress from "@material-ui/core/CircularProgress";
import NewInstrument from "./NewInstrument";
// eslint-disable-next-line import/no-cycle
import ModifyInstrument from "./ModifyInstrument";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    padding: "1rem",
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
      result += `filters: ${instrument.filters}`;
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

const InstrumentList = ({ instruments, telescopes }) => {
  const classes = useStyles();
  const textClasses = textStyles();

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
            />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("System admin") && (
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
};

export default InstrumentPage;
