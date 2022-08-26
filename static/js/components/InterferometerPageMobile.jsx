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
import NewInterferometer from "./NewInterferometer";

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

export function interferometerTitle(interferometer) {
  if (!interferometer?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${interferometer?.nickname}`;
  return result;
}

export function interferometerInfo(interferometer) {
  if (!interferometer?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const array = [
    ...(interferometer?.lat ? [`Latitude: ${interferometer.lat}`] : []),
    ...(interferometer?.lon ? [`Longitude: ${interferometer.lon}`] : []),
    ...(interferometer?.elevation
      ? [`Elevation: ${interferometer.elevation}`]
      : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

  return result;
}

const InterferometerList = ({ interferometers }) => {
  const classes = useStyles();
  const textClasses = textStyles();

  return (
    <div className={classes.root}>
      <List component="nav">
        {interferometers?.map((interferometer) => (
          <ListItem button key={interferometer.id}>
            <ListItemText
              primary={interferometerTitle(interferometer)}
              secondary={interferometerInfo(interferometer)}
              classes={textClasses}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const InterferometerPage = () => {
  const { interferometerList } = useSelector((state) => state.interferometers);
  const currentUser = useSelector((state) => state.profile);

  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Interferometers</Typography>
            <InterferometerList interferometers={interferometerList} />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("Manage allocations") && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New Interferometer</Typography>
              <NewInterferometer />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

InterferometerList.propTypes = {
  interferometers: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      nickname: PropTypes.string.isRequired,
      lat: PropTypes.number.isRequired,
      lon: PropTypes.number.isRequired,
      elevation: PropTypes.number.isRequired,
      is_night_astronomical: PropTypes.bool.isRequired,
    })
  ).isRequired,
};

export default InterferometerPage;
