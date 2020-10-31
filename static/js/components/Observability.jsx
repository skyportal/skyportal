import React, { Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Grid from "@material-ui/core/Grid";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";

const AirmassPlot = React.lazy(() =>
  import(/* webpackChunkName: "AirmassPlot" */ "./AirmassPlot")
);

const ObservabilityPage = ({ route }) => {
  const { telescopeList } = useSelector((state) => state.telescopes);

  return (
    <Grid container spacing={3}>
      {telescopeList.map((telescope) => (
        <Grid item md={3} sm={6} xs={12} key={telescope.id}>
          <Paper>
            <Typography variant="h6">{telescope.name}</Typography>
            <Suspense fallback={<div>Loading plot...</div>}>
              <AirmassPlot
                dataUrl={`/api/internal/plot/airmass/objtel/${route.id}/${telescope.id}`}
              />
            </Suspense>
          </Paper>
        </Grid>
      ))}
    </Grid>
  );
};

ObservabilityPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default ObservabilityPage;
