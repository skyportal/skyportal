import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";

import withRouter from "../withRouter";
import * as telescopesAction from "../../ducks/telescopes";
import * as weatherActions from "../../ducks/weather";
import { showNotification } from "../../../../baselayer/static/js/components/Notifications";
import AllocationTable from "../allocation/AllocationTable";
import InstrumentTable from "../instrument/InstrumentTable";
import SkyCam from "../SkyCam";
import { WeatherView } from "../widget/WeatherWidget";
import Spinner from "../Spinner";
import Paper from "../Paper";

const useStyles = makeStyles((theme) => ({
  title: {
    fontSize: "0.875rem",
  },
  displayInlineBlock: {
    display: "inline-block",
  },
}));

const Telescope = ({ route }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const instrumentsState = useSelector((state) => state.instruments);
  const groups = useSelector((state) => state.groups.all);
  const weather = useSelector((state) => state.weather);
  const [telescope, setTelescope] = useState(null);

  // Load the instrument if needed
  useEffect(() => {
    dispatch(telescopesAction.fetchTelescope(route.id)).then((result) => {
      if (result.status === "success") {
        setTelescope(result.data);
      } else {
        dispatch(showNotification("Error loading telescope data", "error"));
      }
    });
  }, [route.id, dispatch]);

  useEffect(() => {
    if (
      telescope?.id &&
      weather?.telescope_id !== parseInt(telescope?.id, 10)
    ) {
      dispatch(weatherActions.fetchWeather(parseInt(telescope.id, 10)));
    }
  }, [weather, telescope, dispatch]);

  if (!telescope) return <CircularProgress color="secondary" />;

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
          <Paper>
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
          {telescope.instruments ? (
            <InstrumentTable
              instruments={telescope.instruments}
              telescopeInfo={false}
            />
          ) : (
            <Paper>
              <Typography className={classes.title} color="textSecondary">
                No instruments available
              </Typography>
            </Paper>
          )}
        </Grid>
        <Grid item xs={12}>
          {telescope.allocations ? (
            <AllocationTable
              instruments={instrumentsState.instrumentList}
              allocations={telescope.allocations}
              groups={groups}
              telescopeInfo={false}
            />
          ) : (
            <Paper>
              <Typography className={classes.title} color="textSecondary">
                No allocations available
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </div>
  );
};

Telescope.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(Telescope);
