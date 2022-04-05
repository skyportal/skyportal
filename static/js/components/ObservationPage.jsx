import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import PropTypes from "prop-types";

import ExecutedObservationsTable from "./ExecutedObservationsTable";
import NewObservation from "./NewObservation";
import NewAPIObservation from "./NewAPIObservation";

import * as observationsActions from "../ducks/observations";

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

const ObservationList = ({ observations }) => {
  if (!observations?.observations || observations.observations.length === 0) {
    return <p>No observations available...</p>;
  }

  return <ExecutedObservationsTable observations={observations.observations} />;
};

const ObservationPage = () => {
  const observations = useSelector((state) => state.observations);
  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();
  const classes = useStyles();

  useEffect(() => {
    dispatch(observationsActions.fetchObservations());
  }, [dispatch]);

  if (!observations) {
    return <p>No observations available...</p>;
  }

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Observations</Typography>
            <ObservationList observations={observations.observations} />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("System admin") && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add New Observations</Typography>
              <NewObservation />
            </div>
          </Paper>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add API Observations</Typography>
              <NewAPIObservation />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

ObservationList.propTypes = {
  observations: PropTypes.shape({
    observations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.string,
        obstime: PropTypes.instanceOf(Date),
        filt: PropTypes.string,
        exposure_time: PropTypes.number,
        airmass: PropTypes.number,
        limmag: PropTypes.number,
        seeing: PropTypes.number,
        processed_fraction: PropTypes.number,
      })
    ),
  }),
};

ObservationList.defaultProps = {
  observations: null,
};

export default ObservationPage;
