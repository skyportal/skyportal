import React, { Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Grid from "@material-ui/core/Grid";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import { makeStyles } from "@material-ui/core/styles";
import { Link } from "react-router-dom";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { AirMassPlotWithEphemURL } from "./AirmassPlot";

const useStyles = makeStyles({ inner: { margin: "1rem" } });

dayjs.extend(utc);

const ObservabilityPage = ({ route }) => {
  const { telescopeList } = useSelector((state) => state.telescopes);
  const classes = useStyles();

  return (
    <div>
      <Typography variant="h4">
        Observability of <Link to={`/source/${route.id}`}>{route.id}</Link>
      </Typography>
      <Grid container spacing={3}>
        {telescopeList
          .filter((telescope) => telescope.fixed_location)
          .map((telescope) => {
            return (
              <Grid item key={telescope.id}>
                <Paper>
                  <div className={classes.inner}>
                    <Typography variant="h6">{telescope.name}</Typography>
                    <Suspense fallback={<div>Loading plot...</div>}>
                      <AirMassPlotWithEphemURL
                        dataUrl={`/api/internal/plot/airmass/objtel/${route.id}/${telescope.id}`}
                        ephemerisUrl={`/api/internal/ephemeris/${telescope.id}`}
                      />
                    </Suspense>
                  </div>
                </Paper>
              </Grid>
            );
          })}
      </Grid>
    </div>
  );
};

ObservabilityPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default ObservabilityPage;
