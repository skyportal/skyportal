import { useState } from "react";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import Button from "../Button";
import { RequestSpectrumDialog } from "../plot/UnsharedSpectrumMarkers";
import {
  SpectrumAvailability,
  useGetDataAvailabilityQuery,
} from "../../ducks/dataAccessRequests";

const useStyles = makeStyles()((theme) => ({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
    padding: "0.5rem 1rem",
  },
  row: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "0.5rem",
    "& + &": {
      borderTop: `1px solid ${theme.palette.divider}`,
    },
  },
}));

const describe = (spectrum: SpectrumAvailability) =>
  [
    spectrum.instrument?.name ?? "Spectrum",
    spectrum.observed_at ? spectrum.observed_at.slice(0, 10) : null,
    spectrum.owner?.username ? `from ${spectrum.owner.username}` : null,
  ]
    .filter(Boolean)
    .join(", ");

interface UnsharedSpectraProps {
  sourceID: string;
}

/** Spectra taken of this source that the viewer cannot open, and a way to ask. */
const UnsharedSpectra = ({ sourceID }: UnsharedSpectraProps) => {
  const { classes } = useStyles();
  const [selected, setSelected] = useState<SpectrumAvailability | null>(null);
  const { data: availability } = useGetDataAvailabilityQuery(sourceID, {
    skip: !sourceID,
  });
  const spectra = availability?.spectra ?? [];

  if (spectra.length === 0) return null;

  return (
    <div className={classes.container} data-testid="unshared-spectra">
      <Typography variant="body2" color="textSecondary">
        {spectra.length === 1
          ? "One more spectrum exists but is not shared with you:"
          : `${spectra.length} more spectra exist but are not shared with you:`}
      </Typography>
      {spectra.map((spectrum) => (
        <div className={classes.row} key={spectrum.id}>
          <Typography variant="body2">{describe(spectrum)}</Typography>
          {spectrum.request?.status === "pending" ? (
            <Typography variant="caption" color="textSecondary">
              Requested
            </Typography>
          ) : (
            <Button
              secondary
              size="small"
              onClick={() => setSelected(spectrum)}
              data-testid={`ask-for-spectrum-${spectrum.id}`}
            >
              Ask for it
            </Button>
          )}
        </div>
      ))}
      <RequestSpectrumDialog
        objId={sourceID}
        spectrum={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
};

export default UnsharedSpectra;
