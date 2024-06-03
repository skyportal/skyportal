import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

import CircularProgress from "@mui/material/CircularProgress";
import { Paper } from "@mui/material";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";

import AllocationTable from "../allocation/AllocationTable";
import InstrumentTable from "../InstrumentTable";
import SkyCam from "../SkyCam";
import { WeatherView } from "../WeatherWidget";
import Spinner from "../Spinner";

import withRouter from "../withRouter";

import * as Action from "../../ducks/telescope";
import * as weatherActions from "../../ducks/weather";

const useStyles = makeStyles((theme) => ({
  title: {
    fontSize: "0.875rem",
  },
  chip: {
    margin: theme.spacing(0.5),
  },
  displayInlineBlock: {
    display: "inline-block",
  },
  center: {
    margin: "auto",
    padding: "0.625rem",
  },
  columnItem: {
    marginBottom: theme.spacing(1),
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  paper: {
    padding: theme.spacing(2),
  },
}));

const TelescopeSummary = ({ route }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const telescope = useSelector((state) => state.telescope);
  const instrumentsState = useSelector((state) => state.instruments);
  const groups = useSelector((state) => state.groups.all);
  const weather = useSelector((state) => state.weather);

  // Load the instrument if needed
  useEffect(() => {
    dispatch(Action.fetchTelescope(route.id));
  }, [route.id, dispatch]);

  useEffect(() => {
    const fetchWeatherData = () => {
      dispatch(weatherActions.fetchWeather(parseInt(telescope.id, 10)));
    };
    if (
      telescope?.id &&
      (weather?.telescope_id !== parseInt(telescope?.id, 10) ||
        weather === undefined)
    ) {
      fetchWeatherData();
    }
  }, [weather, telescope, dispatch]);

  if (!("id" in telescope && telescope.id === parseInt(telescope.id, 10))) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <div>
      <Grid container spacing={2} className={classes.source}>
        <Grid item xs={12}>
          <Typography variant="h5">
            {telescope.name} ({telescope.nickname})
          </Typography>
        </Grid>
        <Grid
          item
          xs={12}
          sm={12}
          md={6}
          lg={6}
          xl={6}
          className={classes.displayInlineBlock}
        >
          <SkyCam telescope={telescope} />
        </Grid>
        <Grid
          item
          xs={12}
          sm={12}
          md={6}
          lg={6}
          xl={6}
          className={classes.displayInlineBlock}
        >
          <Paper elevation={1} className={classes.paper}>
            <Typography className={classes.title} color="textSecondary">
              Weather
            </Typography>
            {weather && weather?.telescope_id === parseInt(telescope.id, 10) ? (
              <WeatherView weather={weather} />
            ) : (
              <Spinner />
            )}
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <div>
            <Typography className={classes.title} color="textSecondary">
              Instruments
            </Typography>
            {telescope.instruments && (
              <InstrumentTable
                instruments={telescope.instruments}
                telescopeInfo={false}
              />
            )}
          </div>
          <div>
            <Typography className={classes.title} color="textSecondary">
              Allocations
            </Typography>
            {telescope.allocations && (
              <AllocationTable
                instruments={instrumentsState.instrumentList}
                allocations={telescope.allocations}
                groups={groups}
                hideTitle
                telescopeInfo={false}
              />
            )}
          </div>
        </Grid>
      </Grid>
    </div>
  );
};

TelescopeSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.number,
  }).isRequired,
};

export default withRouter(TelescopeSummary);
