import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Grid from "@material-ui/core/Grid";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import { Link } from "react-router-dom";

import { makeStyles } from "@material-ui/core/styles";
import dayjs from "dayjs";

import Plot from "./Plot";
import { UserContactCard } from "./UserProfileInfo";
import { fetchSourceSpectra } from "../ducks/spectra";

const useStyles = makeStyles({
  plot: {
    width: "900px",
    overflow: "auto",
  },
  inner: { padding: "1rem" },
  margined: { margin: "1rem" },
});

const DetailedSpectrumView = ({ spectrum }) => {
  const classes = useStyles();
  return (
    <div>
      <Typography variant="h6">Uploaded by</Typography>
      <UserContactCard user={spectrum.owner} />
      <Typography variant="h6">Reduced by</Typography>
      {spectrum.reducers.map((reducer) => (
        <UserContactCard user={reducer} key={reducer.id} />
      ))}
      <Typography variant="h6">Observed by</Typography>
      {spectrum.observers.map((observer) => (
        <UserContactCard user={observer} key={observer.id} />
      ))}
      <Plot
        className={classes.plot}
        url={`/api/internal/plot/spectroscopy/${spectrum.obj_id}?spectrumID=${spectrum.id}`}
      />
    </div>
  );
};

const user = {
  id: PropTypes.number.isRequired,
  contact_email: PropTypes.string.isRequired,
  first_name: PropTypes.string,
  last_name: PropTypes.string,
  username: PropTypes.string.isRequired,
};

DetailedSpectrumView.propTypes = {
  spectrum: PropTypes.shape({
    id: PropTypes.number,
    obj_id: PropTypes.number,
    reducers: PropTypes.arrayOf(user),
    observers: PropTypes.arrayOf(user),
    owner: PropTypes.shape(user),
  }).isRequired,
};

const SpectrumPage = ({ route }) => {
  const dispatch = useDispatch();
  const spectra = useSelector((state) => state.spectra);
  const classes = useStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);

  useEffect(() => {
    dispatch(fetchSourceSpectra(route.id));
  }, [dispatch, route.id]);

  if (
    !Object.keys(spectra).includes(route.id) ||
    telescopeList.length === 0 ||
    instrumentList.length === 0
  ) {
    return <p>Loading...</p>;
  }

  const sortedSpectra = spectra[route.id].sort(
    (a, b) => dayjs(a).unix() - dayjs(b).unix()
  );
  return (
    <div>
      <Typography variant="h4">
        Spectra of <Link to={`/source/${route.id}`}>{route.id}</Link>
      </Typography>
      <Grid container spacing={3}>
        {sortedSpectra.map((spectrum) => {
          const instrument = instrumentList.find(
            (i) => i.id === spectrum.instrument_id
          );
          const telescope = telescopeList.find(
            (t) => t.id === instrument?.telescope_id
          );
          const specname = `${telescope?.nickname}/${instrument?.name}: ${spectrum.observed_at}`;

          return (
            <Grid item md={12} lg={6} xl={4} key={spectrum.id}>
              <Paper className={classes.margined}>
                <div className={classes.inner}>
                  <Typography variant="h6">{specname}</Typography>
                  <DetailedSpectrumView spectrum={spectrum} />
                </div>
              </Paper>
            </Grid>
          );
        })}
      </Grid>
    </div>
  );
};

SpectrumPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.number.isRequired,
  }).isRequired,
};

export default SpectrumPage;
