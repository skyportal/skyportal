import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import makeStyles from "@mui/styles/makeStyles";
import { Link } from "react-router-dom";
import CircularProgress from "@mui/material/CircularProgress";
import Pagination from "@mui/material/Pagination";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
// eslint-disable-next-line
import HoursBelowAirmassPlot from "../templates/HoursBelowAirmassPlot";
import ObservabilityPreferences from "../user/preferences/ObservabilityPreferences";
import AirmassPlot from "../plot/AirmassPlot";
import withRouter from "../withRouter";
import * as ephemerisActions from "../../ducks/ephemeris";

const useStyles = makeStyles({
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

const ObservabilityPage = ({ route }) => {
  const { telescopeList } = useSelector((state) => state.telescopes);
  const preferences = useSelector(
    (state) => state.profile.preferences.observabilityTelescopes,
  );
  const [ephemerides, setEphemerides] = useState({});
  const classes = useStyles();
  const dispatch = useDispatch();
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const selectedTelescopes = telescopeList
    ?.filter(
      (telescope) =>
        preferences &&
        preferences.length > 0 &&
        preferences.indexOf(telescope.id) !== -1,
    )
    .filter((telescope) => telescope.fixed_location === true);

  useEffect(() => {
    const getEphem = async (selected_telescopes) => {
      const result = await dispatch(
        ephemerisActions.fetchEphemerides(
          [...selected_telescopes]
            .splice((page - 1) * 16, page * 16)
            .map((telescope) => telescope.id),
        ),
      );
      if (result.status === "success") {
        setEphemerides(result.data);
        setLoading(false);
      }
    };
    if (selectedTelescopes?.length > 0) {
      setLoading(true);
      getEphem(selectedTelescopes);
    } else if (selectedTelescopes?.length === 0) {
      setEphemerides({});
    }
  }, [telescopeList, preferences, page, dispatch]);

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
              count={Math.ceil(selectedTelescopes?.length / 16)}
              page={page}
              onChange={(event, value) => setPage(value)}
            />
          </div>
        </Paper>
      )}
      <Grid container spacing={3}>
        {!loading && ephemerides
          ? selectedTelescopes
              ?.filter(
                // check that the telescope id is a key in the ephemerides object
                (telescope) =>
                  Object.prototype.hasOwnProperty.call(
                    ephemerides,
                    telescope.id,
                  ),
              )
              ?.map((telescope) => (
                <Grid item key={telescope.id}>
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
                          ephemeris={ephemerides[telescope.id]}
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
          <Grid item md={12} sm={12}>
            <Paper>
              <Typography variant="h6" style={{ margin: "1rem" }}>
                Fetching Telescopes...
              </Typography>
            </Paper>
          </Grid>
        )}
        {loading && telescopeList?.length > 0 && preferences?.length && (
          <Grid item md={12} sm={12}>
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
            <Grid item md={12} sm={12}>
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

ObservabilityPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(ObservabilityPage);
