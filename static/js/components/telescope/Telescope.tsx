import { useEffect } from "react";
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

interface TelescopeProps {
  route: {
    id: string;
  };
}

const Telescope = ({ route }: TelescopeProps) => {
  const dispatch = useAppDispatch();
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

  if (!telescope) return <Spinner />;

  return (
    <Grid container spacing={2}>
      <Grid size={12}>
        <Typography variant="h5">
          {telescope["name"]} ({telescope["nickname"]})
        </Typography>
      </Grid>
      <Grid size={{ xs: 12, sm: 12, md: 6, lg: 6, xl: 6 }}>
        <SkyCam telescope={telescope as unknown as TelescopeType} />
      </Grid>
      <Grid size={{ xs: 12, sm: 12, md: 6, lg: 6, xl: 6 }}>
        <Paper>
          <Typography variant="h6">Weather</Typography>
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
          <Paper>
            <Typography color="textSecondary">
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
          <Paper>
            <Typography color="textSecondary">
              No allocations available
            </Typography>
          </Paper>
        )}
      </Grid>
    </Grid>
  );
};

export default withRouter(Telescope);
