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
import NewGWDetector from "./NewGWDetector";

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

export function gwdetectorTitle(gwdetector) {
  if (!gwdetector?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${gwdetector?.nickname}`;
  return result;
}

export function gwdetectorInfo(gwdetector) {
  if (!gwdetector?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const array = [
    ...(gwdetector?.lat ? [`Latitude: ${gwdetector.lat}`] : []),
    ...(gwdetector?.lon ? [`Longitude: ${gwdetector.lon}`] : []),
    ...(gwdetector?.elevation ? [`Elevation: ${gwdetector.elevation}`] : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

  return result;
}

const GWDetectorList = ({ gwdetectors }) => {
  const classes = useStyles();
  const textClasses = textStyles();

  return (
    <div className={classes.root}>
      <List component="nav">
        {gwdetectors?.map((gwdetector) => (
          <ListItem button key={gwdetector.id}>
            <ListItemText
              primary={gwdetectorTitle(gwdetector)}
              secondary={gwdetectorInfo(gwdetector)}
              classes={textClasses}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const GWDetectorPage = () => {
  const { gwdetectorList } = useSelector((state) => state.gwdetectors);
  const currentUser = useSelector((state) => state.profile);

  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of GWDetectors</Typography>
            <GWDetectorList gwdetectors={gwdetectorList} />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("Manage allocations") && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New GWDetector</Typography>
              <NewGWDetector />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

GWDetectorList.propTypes = {
  gwdetectors: PropTypes.arrayOf(
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

export default GWDetectorPage;
