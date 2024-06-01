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
import NewMMADetector from "../NewMMADetector";

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

export function mmadetectorTitle(mmadetector) {
  if (!mmadetector?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${mmadetector?.nickname}`;
  return result;
}

export function mmadetectorInfo(mmadetector) {
  if (!mmadetector?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const array = [
    ...(mmadetector?.lat ? [`Latitude: ${mmadetector.lat}`] : []),
    ...(mmadetector?.lon ? [`Longitude: ${mmadetector.lon}`] : []),
    ...(mmadetector?.elevation ? [`Elevation: ${mmadetector.elevation}`] : []),
  ];

  // eslint-disable-next-line prefer-template
  const result = "( " + array.join(" / ") + " )";

  return result;
}

const MMADetectorList = ({ mmadetectors }) => {
  const classes = useStyles();
  const textClasses = textStyles();

  return (
    <div className={classes.root}>
      <List component="nav">
        {mmadetectors?.map((mmadetector) => (
          <ListItem button key={mmadetector.id}>
            <ListItemText
              primary={mmadetectorTitle(mmadetector)}
              secondary={mmadetectorInfo(mmadetector)}
              classes={textClasses}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const MMADetectorPageMobile = () => {
  const { mmadetectorList } = useSelector((state) => state.mmadetectors);
  const currentUser = useSelector((state) => state.profile);

  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of MMADetectors</Typography>
            <MMADetectorList mmadetectors={mmadetectorList} />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("Manage allocations") && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New MMADetector</Typography>
              <NewMMADetector />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

MMADetectorList.propTypes = {
  mmadetectors: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      nickname: PropTypes.string.isRequired,
      lat: PropTypes.number.isRequired,
      lon: PropTypes.number.isRequired,
      elevation: PropTypes.number.isRequired,
      is_night_astronomical: PropTypes.bool.isRequired,
    }),
  ).isRequired,
};

export default MMADetectorPageMobile;
