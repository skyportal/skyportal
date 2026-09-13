import { ChangeEvent, useState } from "react";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import Button from "../Button";
import {
  PhotometryAvailability,
  SpectrumAvailability,
  useGetDataAvailabilityQuery,
  useRequestDataAccessMutation,
} from "../../ducks/dataAccessRequests";

const useStyles = makeStyles()((theme) => ({
  list: {
    "& > * + *": {
      borderTop: `1px solid ${theme.palette.divider}`,
    },
  },
  row: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "0.5rem",
    padding: "0.25rem 0",
  },
  divider: {
    margin: `${theme.spacing(2)} 0 ${theme.spacing(1)}`,
  },
  form: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: "0.5rem",
    marginTop: "0.5rem",
  },
}));

const ownerName = (owner: { username: string } | null) =>
  owner?.username ?? "someone";

const mjdRange = (dataset: PhotometryAvailability) => {
  if (dataset.first_mjd == null) return "";
  const first = dataset.first_mjd.toFixed(2);
  const last = dataset.last_mjd?.toFixed(2);
  return first === last ? `MJD ${first}` : `MJD ${first}–${last}`;
};

const photometryKey = (dataset: PhotometryAvailability) =>
  `${dataset.owner?.id}:${dataset.instrument?.id}:${dataset.filter}`;

const statusLabel = (status: string) =>
  status === "pending"
    ? "Requested"
    : status === "accepted"
      ? "Granted"
      : "Declined";

interface RequestDataAccessProps {
  sourceID: string;
}

/** What exists on this source that the viewer cannot see, and a way to ask. */
const RequestDataAccess = ({ sourceID }: RequestDataAccessProps) => {
  const { classes } = useStyles();
  const [open, setOpen] = useState(false);
  const [selectedPhotometry, setSelectedPhotometry] = useState<string[]>([]);
  const [selectedSpectra, setSelectedSpectra] = useState<number[]>([]);
  const [message, setMessage] = useState("");
  const { data: availability } = useGetDataAvailabilityQuery(sourceID);
  const [requestAccess, { isLoading }] = useRequestDataAccessMutation();

  const photometry = availability?.photometry ?? [];
  const spectra = availability?.spectra ?? [];
  const count = photometry.length + spectra.length;
  if (count === 0) return null;

  const togglePhotometry = (dataset: PhotometryAvailability) => {
    const key = photometryKey(dataset);
    setSelectedPhotometry((keys) =>
      keys.includes(key) ? keys.filter((k) => k !== key) : [...keys, key],
    );
  };

  const toggleSpectrum = (spectrum: SpectrumAvailability) => {
    setSelectedSpectra((ids) =>
      ids.includes(spectrum.id)
        ? ids.filter((id) => id !== spectrum.id)
        : [...ids, spectrum.id],
    );
  };

  const submit = async () => {
    const datasets = photometry
      .filter((dataset) => selectedPhotometry.includes(photometryKey(dataset)))
      .map((dataset) => ({
        ownerID: dataset.owner?.id as number,
        instrumentID: dataset.instrument?.id as number,
        filter: dataset.filter,
      }));
    const result = await requestAccess({
      objId: sourceID,
      photometry: datasets,
      spectrumIDs: selectedSpectra,
      message: message || null,
    });
    if (!("error" in result)) {
      setSelectedPhotometry([]);
      setSelectedSpectra([]);
      setMessage("");
      setOpen(false);
    }
  };

  const nothingSelected =
    selectedPhotometry.length === 0 && selectedSpectra.length === 0;

  return (
    <>
      <Tooltip title="Data on this source that you cannot see">
        <span>
          <Button
            secondary
            color="grey"
            size="small"
            onClick={() => setOpen(true)}
            data-testid="request-data-access-button"
          >
            {`Unshared data (${count})`}
          </Button>
        </span>
      </Tooltip>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="sm"
        fullWidth
        data-testid="data-availability-dialog"
      >
        <DialogTitle>Unshared data on {sourceID}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary">
            These datasets exist on this source but have not been shared with
            you. Pick the ones you would like, and their owners will be asked.
          </Typography>

          {photometry.length > 0 && (
            <>
              <Divider className={classes.divider} />
              <Typography variant="subtitle1">Photometry</Typography>
              <div className={classes.list}>
                {photometry.map((dataset) => (
                  <div className={classes.row} key={photometryKey(dataset)}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          size="small"
                          disabled={dataset.request?.status === "pending"}
                          checked={selectedPhotometry.includes(
                            photometryKey(dataset),
                          )}
                          onChange={() => togglePhotometry(dataset)}
                        />
                      }
                      label={
                        <Typography variant="body2">
                          {`${dataset.num_points} point(s) in ${dataset.filter} `}
                          {`on ${dataset.instrument?.name ?? "an instrument"}, `}
                          {`${mjdRange(dataset)}, from ${ownerName(dataset.owner)}`}
                        </Typography>
                      }
                    />
                    {dataset.request && (
                      <Typography variant="caption" color="textSecondary">
                        {statusLabel(dataset.request.status)}
                      </Typography>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          {spectra.length > 0 && (
            <>
              <Divider className={classes.divider} />
              <Typography variant="subtitle1">Spectra</Typography>
              <div className={classes.list}>
                {spectra.map((spectrum) => (
                  <div className={classes.row} key={spectrum.id}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          size="small"
                          disabled={spectrum.request?.status === "pending"}
                          checked={selectedSpectra.includes(spectrum.id)}
                          onChange={() => toggleSpectrum(spectrum)}
                        />
                      }
                      label={
                        <Typography variant="body2">
                          {`${spectrum.instrument?.name ?? "Spectrum"} `}
                          {spectrum.observed_at
                            ? `taken ${spectrum.observed_at.slice(0, 10)}, `
                            : ""}
                          {`from ${ownerName(spectrum.owner)}`}
                          {spectrum.type ? ` (${spectrum.type})` : ""}
                        </Typography>
                      }
                    />
                    {spectrum.request && (
                      <Typography variant="caption" color="textSecondary">
                        {statusLabel(spectrum.request.status)}
                      </Typography>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          <Divider className={classes.divider} />
          <div className={classes.form}>
            <TextField
              label="Note to the owner (optional)"
              size="small"
              fullWidth
              multiline
              value={message}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setMessage(event.target.value)
              }
            />
            <Button
              primary
              size="small"
              disabled={nothingSelected || isLoading}
              onClick={submit}
              data-testid="submit-data-request-button"
            >
              Ask for selected data
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default RequestDataAccess;
