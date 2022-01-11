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

  if (instrument?.filters || instrument?.api_classname) {
    result += "( ";
    if (instrument?.filters) {
      result += `filters: ${instrument.filters}`;
    }
    if (instrument?.api_classname) {
      result += ` / API Classname: ${instrument?.api_classname}`;
    }
    result += " )";
  }

  return result;
}

const InstrumentList = ({ instruments }) => {
  const classes = useStyles();
  const textClasses = textStyles();
  const { telescopeList } = useSelector((state) => state.telescopes);

  return (
    <div className={classes.root}>
      <List component="nav">
        {instruments?.map((instrument) => (
          <ListItem button key={instrument.id}>
            <ListItemText
              primary={instrumentTitle(instrument, telescopeList)}
              secondary={instrumentInfo(instrument, telescopeList)}
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
  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Instruments</Typography>
            <InstrumentList instruments={instrumentList} />
          </div>
        </Paper>
      </Grid>
      <Grid item md={6} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Add a New Instrument</Typography>
            <NewInstrument />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

InstrumentList.propTypes = {
  instruments: PropTypes.arrayOf(PropTypes.any).isRequired,
};

export default InstrumentPage;
