import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Grid from "@material-ui/core/Grid";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Button from "@material-ui/core/Button";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import { Link } from "react-router-dom";
import DownloadLink from "react-download-link";
import { makeStyles } from "@material-ui/core/styles";
import dayjs from "dayjs";
import Papa from "papaparse";

import { showNotification } from "baselayer/components/Notifications";
import Plot from "./Plot";
import { UserContactInfo } from "./UserProfileInfo";
import { fetchSourceSpectra, deleteSpectrum } from "../ducks/spectra";

const useStyles = makeStyles({
  plot: {
    width: "900px",
    overflow: "auto",
  },
  inner: { padding: "1rem" },
  margined: { margin: "1rem" },
  detailedSpecButton: {
    color: "primary",
    variant: "contained",
    cursor: "default",
  },
  specTitle: { margin: "0.5rem" },
});

function get_filename(spectrum, instrument) {
  return `${spectrum.obj_id}_${instrument.name}_${spectrum.observed_at}.csv`;
}

function to_csv(spectrum) {
  const formatted = [];
  spectrum.wavelengths.forEach((wave, i) => {
    const obj = {};
    obj.wavelength = wave;
    obj.flux = spectrum.fluxes[i];
    if (spectrum.fluxerr) {
      obj.fluxerr = spectrum.fluxerr[i];
    }
    formatted.push(obj);
  });
  return Papa.unparse(formatted);
}

const DetailedSpectrumView = ({ spectrum }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { id: currentUserId } = useSelector((state) => state.profile);
  const [open, setOpen] = React.useState(false);

  const instrument = instrumentList.find(
    (i) => i.id === spectrum.instrument_id
  );

  const data = spectrum.original_file_string
    ? spectrum.original_file_string
    : to_csv(spectrum);
  const filename = spectrum.original_file_filename
    ? spectrum.original_file_filename
    : get_filename(spectrum, instrument);

  return (
    <div>
      <Typography variant="h6">Uploaded by</Typography>
      <UserContactInfo user={spectrum.owner} />
      {spectrum.reducers?.length > 0 && (
        <div>
          <Typography variant="h6">Reduced by</Typography>
          {spectrum.reducers.map((reducer) => (
            <UserContactInfo user={reducer} key={reducer.id} />
          ))}
        </div>
      )}
      {spectrum.observers?.length > 0 && (
        <div>
          <Typography variant="h6">Observed by</Typography>
          {spectrum.observers.map((observer) => (
            <UserContactInfo user={observer} key={observer.id} />
          ))}
        </div>
      )}
      <Plot
        className={classes.plot}
        url={`/api/internal/plot/spectroscopy/${spectrum.obj_id}?spectrumID=${spectrum.id}`}
      />
      {spectrum.owner_id === currentUserId && (
        <Button
          onClick={() => {
            setOpen(true);
          }}
          data-testid="delete-spectrum-button"
        >
          Delete Spectrum
        </Button>
      )}
      <DownloadLink
        filename={filename}
        exportFile={() => data}
        style={{ color: "rgba(0, 0, 0, 0.87)", fontWeight: 500 }}
        label="Download ASCII Spectrum"
        tagName={Button}
      />
      <Dialog
        open={open}
        aria-labelledby="simple-modal-title"
        aria-describedby="simple-modal-description"
        onClose={() => {
          setOpen(false);
        }}
        className={classes.detailedSpecButton}
      >
        <DialogContent>
          <div>
            <Typography variant="h6">
              Are you sure you want to do this?
            </Typography>
            The following operation <em>permanently</em> deletes the spectrum
            from the database. This operation cannot be undone and your data
            cannot be recovered after the fact. You will have to upload the
            spectrum again from scratch.
          </div>
          <div>
            <Button
              onClick={() => {
                setOpen(false);
              }}
            >
              No, do not delete the spectrum.
            </Button>
            <Button
              onClick={async () => {
                const result = await dispatch(deleteSpectrum(spectrum.id));
                if (result.status === "success") {
                  dispatch(showNotification("Spectrum deleted."));
                }
              }}
              data-testid="yes-delete"
            >
              Yes, delete the spectrum.
            </Button>
          </div>
        </DialogContent>
      </Dialog>
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
    obj_id: PropTypes.string,
    owner_id: PropTypes.number,
    instrument_id: PropTypes.number,
    reducers: PropTypes.arrayOf(user),
    observers: PropTypes.arrayOf(user),
    owner: PropTypes.shape(user),
    original_file_string: PropTypes.string,
    original_file_filename: PropTypes.string,
  }).isRequired,
};

const SpectraPage = ({ route }) => {
  const dispatch = useDispatch();
  const spectra = useSelector((state) => state.spectra);
  const classes = useStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const profile = useSelector((state) => state.profile);

  useEffect(() => {
    dispatch(fetchSourceSpectra(route.id));
  }, [dispatch, route.id]);

  if (
    !Object.keys(spectra).includes(route.id) ||
    telescopeList.length === 0 ||
    instrumentList.length === 0 ||
    !profile.id
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
            <Grid item key={spectrum.id}>
              <Paper className={classes.margined}>
                <div className={classes.inner}>
                  <Typography variant="h5" className={classes.specTitle}>
                    {specname}
                  </Typography>
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

SpectraPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string.isRequired,
  }).isRequired,
};

export default SpectraPage;
