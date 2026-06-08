import { useEffect } from "react";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";

import { showNotification } from "../../../../baselayer/static/js/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { Telescope as TelescopeType } from "../../types/domain";
import { useGetTelescopeQuery } from "../../ducks/telescopes";
import { useGetWeatherQuery } from "../../ducks/weather";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import AllocationTable from "../allocation/AllocationTable";
import InstrumentTable from "../instrument/InstrumentTable";
import SkyCam from "../SkyCam";
import { WeatherView } from "../widget/WeatherWidget";
import Spinner from "../Spinner";
import Paper from "../Paper";
import withRouter from "../withRouter";

const useStyles = makeStyles()(() => ({
  title: {
    fontSize: "0.875rem",
  },
  displayInlineBlock: {
    display: "inline-block",
  },
}));

interface TelescopeProps {
  route: {
    id: string;
  };
}

const Telescope = ({ route }: TelescopeProps) => {
  const dispatch = useAppDispatch();
  const { classes } = useStyles();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const groups = useGetGroupsQuery().data?.all ?? [];
  const { data: telescope, isError: telescopeError } = useGetTelescopeQuery(
    route.id,
  );
  const { data: weather } = useGetWeatherQuery(
    telescope?.["id"] ? parseInt(telescope["id"], 10) : null,
    { skip: !telescope?.["id"] },
  );

  useEffect(() => {
    if (telescopeError) {
      dispatch(showNotification("Error loading telescope data", "error"));
    }
  }, [telescopeError, dispatch]);

  if (!telescope) return <CircularProgress color="secondary" />;

  return (
    <div>
      <Grid container spacing={2}>
        <Grid size={12}>
          <Typography variant="h5">
            {telescope["name"]} ({telescope["nickname"]})
          </Typography>
        </Grid>
        <Grid
          size={{ xs: 12, sm: 12, md: 6, lg: 6, xl: 6 }}
          className={classes.displayInlineBlock}
        >
          <SkyCam telescope={telescope as unknown as TelescopeType} />
        </Grid>
        <Grid
          size={{ xs: 12, sm: 12, md: 6, lg: 6, xl: 6 }}
          className={classes.displayInlineBlock}
        >
          <Paper>
            <Typography className={classes.title} color="textSecondary">
              Weather
            </Typography>
            {weather &&
            weather["telescope_id"] === parseInt(telescope["id"], 10) ? (
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
            <Paper>
              <Typography className={classes.title} color="textSecondary">
                No instruments available
              </Typography>
            </Paper>
          )}
        </Grid>
        <Grid size={12}>
          {telescope["allocations"] ? (
            <AllocationTable
              instruments={instrumentList}
              allocations={telescope["allocations"]}
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

export default withRouter(Telescope);
