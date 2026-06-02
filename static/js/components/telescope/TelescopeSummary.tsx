import { useEffect, useState } from "react";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import AllocationTable from "../allocation/AllocationTable";
import InstrumentTable from "../instrument/InstrumentTable";
import SkyCam from "../SkyCam";
import { WeatherView } from "../widget/WeatherWidget";
import Spinner from "../Spinner";

import withRouter from "../withRouter";

import * as telescopesAction from "../../ducks/telescopes";
import * as weatherActions from "../../ducks/weather";
import { showNotification } from "../../../../baselayer/static/js/components/Notifications";

const useStyles = makeStyles()((theme) => ({
  title: {
    fontSize: "0.875rem",
  },
  displayInlineBlock: {
    display: "inline-block",
  },
  paper: {
    padding: theme.spacing(2),
  },
}));

interface TelescopeSummaryProps {
  route: {
    id: string;
  };
}

const TelescopeSummary = ({ route }: TelescopeSummaryProps) => {
  const dispatch = useAppDispatch();
  const { classes } = useStyles();
  const instrumentsState = useAppSelector((state) => state.instruments);
  const groups = useAppSelector((state) => state.groups.all);
  const weather = useAppSelector((state) => state.weather);
  const [telescope, setTelescope] = useState<any>(null);

  // Load the instrument if needed
  useEffect(() => {
    dispatch(telescopesAction.fetchTelescope(route.id)).then((result: any) => {
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

  if (!telescope) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <div>
      <Grid container spacing={2} className={(classes as any).source}>
        <Grid size={12}>
          <Typography variant="h5">
            {telescope.name} ({telescope.nickname})
          </Typography>
        </Grid>
        <Grid
          size={{ xs: 12, sm: 12, md: 6, lg: 6, xl: 6 }}
          className={classes.displayInlineBlock}
        >
          <SkyCam telescope={telescope} />
        </Grid>
        <Grid
          size={{ xs: 12, sm: 12, md: 6, lg: 6, xl: 6 }}
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
        <Grid size={12}>
          {telescope.instruments ? (
            <InstrumentTable
              instruments={telescope.instruments}
              telescopeInfo={false}
            />
          ) : (
            <Paper className={classes.paper}>
              <Typography className={classes.title} color="textSecondary">
                No instruments available
              </Typography>
            </Paper>
          )}
        </Grid>
        <Grid size={12}>
          {telescope.allocations ? (
            <AllocationTable
              instruments={instrumentsState.instrumentList}
              allocations={telescope.allocations}
              groups={groups}
              telescopeInfo={false}
            />
          ) : (
            <Paper className={classes.paper}>
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

export default withRouter(TelescopeSummary);
