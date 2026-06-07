import { useGetGroupsQuery } from "../../ducks/groups";
import { useEffect } from "react";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";

import { useAppDispatch } from "../../types/hooks";
import AllocationTable from "../allocation/AllocationTable";
import InstrumentTable from "../instrument/InstrumentTable";
import SkyCam from "../SkyCam";
import { WeatherView } from "../widget/WeatherWidget";
import Spinner from "../Spinner";

import withRouter from "../withRouter";

import { useGetTelescopeQuery } from "../../ducks/telescopes";
import { useGetWeatherQuery } from "../../ducks/weather";
import { showNotification } from "../../../../baselayer/static/js/components/Notifications";
import { Telescope } from "../../types/domain";
import { useGetInstrumentsQuery } from "../../ducks/instruments";

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
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const groups = useGetGroupsQuery().data?.all ?? [];
  const { data: telescope, isError: telescopeError } = useGetTelescopeQuery(
    route.id,
  );
  const telescopeAny = telescope as any;
  const { data: weather } = useGetWeatherQuery(telescope?.["id"] ?? null, {
    skip: !telescope?.["id"],
  });

  useEffect(() => {
    if (telescopeError) {
      dispatch(showNotification("Error loading telescope data", "error"));
    }
  }, [telescopeError, dispatch]);

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
            {telescope["name"]} ({telescope["nickname"]})
          </Typography>
        </Grid>
        <Grid
          size={{ xs: 12, sm: 12, md: 6, lg: 6, xl: 6 }}
          className={classes.displayInlineBlock}
        >
          <SkyCam telescope={telescope as unknown as Telescope} />
        </Grid>
        <Grid
          size={{ xs: 12, sm: 12, md: 6, lg: 6, xl: 6 }}
          className={classes.displayInlineBlock}
        >
          <Paper elevation={1} className={classes.paper}>
            <Typography className={classes.title} color="textSecondary">
              Weather
            </Typography>
            {weather && weather["telescope_id"] === telescope["id"] ? (
              <WeatherView weather={weather} />
            ) : (
              <Spinner />
            )}
          </Paper>
        </Grid>
        <Grid size={12}>
          {telescope["instruments"] ? (
            <InstrumentTable
              instruments={telescope["instruments"]}
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
          {telescopeAny["allocations"] ? (
            <AllocationTable
              instruments={instrumentList}
              allocations={telescopeAny["allocations"]}
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
