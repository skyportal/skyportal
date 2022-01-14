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
import NewTelescope from "./NewTelescope";

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

export function telescopeTitle(telescope) {
  if (!telescope?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${telescope?.nickname}`;

  return result;
}

export function telescopeInfo(telescope) {
  if (!telescope?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  let result = "";

  if (telescope?.lat) {
    result += "( ";
    if (telescope?.lat) {
      result += `/ Latitude: ${telescope.lat}`;
    }
    if (telescope?.lon) {
      result += `/ Latitude: ${telescope.lon}`;
    }
    if (telescope?.elevation) {
      result += `/ Elevation: ${telescope.elevation}`;
    }
    result += " )";
  }

  return result;
}

const TelescopeList = ({ telescopes }) => {
  const classes = useStyles();
  const textClasses = textStyles();

  return (
    <div className={classes.root}>
      <List component="nav">
        {telescopes?.map((telescope) => (
          <ListItem button key={telescope.id}>
            <ListItemText
              primary={telescopeTitle(telescope)}
              secondary={telescopeInfo(telescope)}
              classes={textClasses}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const TelescopePage = () => {
  const { telescopeList } = useSelector((state) => state.telescopes);

  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Telescopes</Typography>
            <TelescopeList telescopes={telescopeList} />
          </div>
        </Paper>
      </Grid>
      <Grid item md={6} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Add a New Telescope</Typography>
            <NewTelescope />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

TelescopeList.propTypes = {
  telescopes: PropTypes.arrayOf(PropTypes.any).isRequired,
};

export default TelescopePage;
