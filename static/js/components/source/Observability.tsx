import { useGetProfileQuery } from "../../ducks/profile";
import { Suspense, useState } from "react";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import { makeStyles } from "tss-react/mui";
import { Link } from "react-router-dom";
import CircularProgress from "@mui/material/CircularProgress";
import Pagination from "@mui/material/Pagination";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import HoursBelowAirmassPlot from "../templates/HoursBelowAirmassPlot";
import AcrossVisibility from "./AcrossVisibility";
import ObservabilityPreferences from "../user/preferences/ObservabilityPreferences";
import AirmassPlot, { Ephemeris } from "../plot/AirmassPlot";
import withRouter from "../withRouter";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useGetEphemeridesQuery } from "../../ducks/ephemeris";
import { useGetAcrossInstrumentsQuery } from "../../ducks/across";

const useStyles = makeStyles()({
  inner: {
    margin: "1rem",
    padding: "1rem",
  },
  preferences: {
    displaypadding: "1rem",
    marginTop: "1rem",
  },
  preferencesContent: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    margin: "1rem",
  },
});

dayjs.extend(utc);

interface ObservabilityPageProps {
  route: {
    id: string;
  };
}

const ObservabilityPage = ({ route }: ObservabilityPageProps) => {
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const preferences = useGetProfileQuery().data?.preferences?.[
    "observabilityTelescopes"
  ] as any;
  const { classes } = useStyles();
  const [page, setPage] = useState(1);

  const { data: acrossInstruments = [] } = useGetAcrossInstrumentsQuery();

  const selectedTelescopes = telescopeList?.filter(
    (telescope: any) =>
      preferences &&
      preferences.length > 0 &&
      preferences.indexOf(telescope.id) !== -1,
  );

  // Ground telescopes also get airmass plots below; the joint-visibility panel
  // covers all selected telescopes (ground via astroplan, space via ACROSS).
  const groundTelescopes = selectedTelescopes?.filter(
    (telescope: any) => telescope.fixed_location === true,
  );

  const acrossTelescopeIds = new Set(
    acrossInstruments.map((inst: any) => inst.telescope_id),
  );
  const panelTelescopes = (selectedTelescopes || [])
    .filter(
      (t: any) => t.fixed_location === true || acrossTelescopeIds.has(t.id),
    )
    .map((t: any) => ({ id: t.id, name: t.nickname || t.name }));

  const pagedTelescopeIds: number[] = groundTelescopes
    ? [...groundTelescopes]
        .splice((page - 1) * 16, page * 16)
        .map((telescope: any) => telescope.id)
    : [];

  const { data: ephemerides = {}, isFetching } = useGetEphemeridesQuery(
    pagedTelescopeIds,
    { skip: pagedTelescopeIds.length === 0 },
  );

  const loading = isFetching;

  // ephmerides is an object where each key is the telescope id and the value is the ephemeris

  return (
    <div>
      <Typography variant="h4">
        Observability of <Link to={`/source/${route.id}`}>{route.id}</Link>
      </Typography>
      {telescopeList?.length > 0 && (
        <Paper className={classes.preferences}>
          <div className={classes.preferencesContent}>
            <ObservabilityPreferences />
            <Pagination
              count={Math.ceil(groundTelescopes?.length / 16)}
              page={page}
              onChange={(_event, value) => setPage(value)}
            />
          </div>
        </Paper>
      )}
      <AcrossVisibility objId={route.id} telescopes={panelTelescopes} />

      <Grid container spacing={3}>
        {!loading && ephemerides
          ? groundTelescopes
              ?.filter(
                // check that the telescope id is a key in the ephemerides object
                (telescope: any) =>
                  Object.prototype.hasOwnProperty.call(
                    ephemerides,
                    telescope.id,
                  ),
              )
              ?.map((telescope: any) => (
                <Grid key={telescope.id}>
                  <Paper>
                    <div className={classes.inner}>
                      <Typography variant="h6">{telescope.name}</Typography>
                      <Suspense
                        fallback={
                          <div>
                            <CircularProgress color="secondary" />
                          </div>
                        }
                      >
                        <AirmassPlot
                          dataUrl={`/api/internal/plot/airmass/objtel/${route.id}/${telescope.id}`}
                          ephemeris={ephemerides[telescope.id] as Ephemeris}
                        />
                      </Suspense>
                      <Suspense
                        fallback={
                          <div>
                            <CircularProgress color="secondary" />
                          </div>
                        }
                      >
                        <HoursBelowAirmassPlot
                          dataUrl={`/api/internal/plot/airmass/hours_below/${route.id}/${telescope.id}`}
                        />
                      </Suspense>
                    </div>
                  </Paper>
                </Grid>
              ))
          : null}
        {(telescopeList?.length === 0 || !telescopeList) && (
          <Grid size={{ md: 12, sm: 12 }}>
            <Paper>
              <Typography variant="h6" style={{ margin: "1rem" }}>
                Fetching Telescopes...
              </Typography>
            </Paper>
          </Grid>
        )}
        {loading && telescopeList?.length > 0 && preferences?.length > 0 && (
          <Grid size={{ md: 12, sm: 12 }}>
            <Paper>
              <Typography variant="h6" style={{ margin: "1rem" }}>
                Loading Plots...
              </Typography>
            </Paper>
          </Grid>
        )}
        {telescopeList?.length > 0 &&
          Object?.keys(typeof ephemerides === "object" ? ephemerides : {})
            ?.length === 0 &&
          (selectedTelescopes?.length === 0 || !selectedTelescopes) && (
            <Grid size={{ md: 12, sm: 12 }}>
              <Paper>
                <Typography variant="h6" style={{ margin: "1rem" }}>
                  No telescopes selected
                </Typography>
              </Paper>
            </Grid>
          )}
      </Grid>
    </div>
  );
};

export default withRouter(ObservabilityPage);
