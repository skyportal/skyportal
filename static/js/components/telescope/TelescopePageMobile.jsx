import React from "react";
import { useSelector } from "react-redux";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import NewTelescope from "../NewTelescope";

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

  const array = [
    ...(telescope?.lat ? [`Latitude: ${telescope.lat}`] : []),
    ...(telescope?.lon ? [`Longitude: ${telescope.lon}`] : []),
    ...(telescope?.elevation ? [`Elevation: ${telescope.elevation}`] : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

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

TelescopeList.propTypes = {
  telescopes: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      nickname: PropTypes.string.isRequired,
      lat: PropTypes.number,
      lon: PropTypes.number,
      elevation: PropTypes.number,
      is_night_astronomical: PropTypes.bool.isRequired,
    }),
  ).isRequired,
};

const TelescopePage = () => {
  const { telescopeList } = useSelector((state) => state.telescopes);
  const currentUser = useSelector((state) => state.profile);

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
      {currentUser.permissions?.includes("Manage telescopes") && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New Telescope</Typography>
              <NewTelescope />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

export default TelescopePage;
