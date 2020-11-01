import React, { Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Grid from "@material-ui/core/Grid";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { AirMassPlotWithEphemURL } from "./AirmassPlot";

dayjs.extend(utc);

const ObservabilityPage = ({ route }) => {
  const { telescopeList } = useSelector((state) => state.telescopes);

  return (
    <Grid container spacing={3}>
      {telescopeList.map((telescope) => {
        return (
          <Grid item md={3} sm={6} xs={12} key={telescope.id}>
            <Paper>
              <Typography variant="h6">{telescope.name}</Typography>
              <Suspense fallback={<div>Loading plot...</div>}>
                <AirMassPlotWithEphemURL
                  dataUrl={`/api/internal/plot/airmass/objtel/${route.id}/${telescope.id}`}
                  ephemerisUrl={`/api/internal/ephemeris/${telescope.id}`}
                />
              </Suspense>
            </Paper>
          </Grid>
        );
      })}
    </Grid>
  );
};

ObservabilityPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default ObservabilityPage;
