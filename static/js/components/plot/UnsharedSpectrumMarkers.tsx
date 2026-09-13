/**
 * Spectra that exist on a source but have not been shared with the viewer.
 *
 * The photometry plot marks every spectrum's epoch with an "S". These are the
 * ones whose data the viewer cannot open: same marker, different colour, and
 * clicking one asks its owner for it.
 */
import { ChangeEvent, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import Button from "../Button";
import {
  SpectrumAvailability,
  useRequestDataAccessMutation,
} from "../../ducks/dataAccessRequests";

/** Trace name, also how a click on one of these markers is recognised. */
export const UNSHARED_SPECTRUM = "Unshared spectrum";

/**
 * Plotly traces for the unshared spectra, to concat onto the plot's other
 * event markers. `yMarkers` is the same y position the shared "S" markers use.
 */
export const unsharedSpectrumTraces = (
  spectra: SpectrumAvailability[],
  yMarkers: any[],
  colors: { available: string; requested: string },
  hoverBackground: string,
) =>
  spectra
    .filter((spectrum) => spectrum.observed_at_mjd != null)
    .map((spectrum) => {
      const pending = spectrum.request?.status === "pending";
      const hovertext = `<br>Observed at (UTC): ${spectrum.observed_at}
    <br>Instrument: ${spectrum.instrument?.name ?? "unknown"}
    <br>Owner: ${spectrum.owner?.username ?? "unknown"}
    <br>Origin: ${spectrum.origin || ""}
    <br><b>${pending ? "Access already requested" : "Not shared with you — click to ask for it"}</b>
    <extra></extra>
    `;
      return {
        x: [spectrum.observed_at_mjd],
        y: yMarkers,
        customdata: [spectrum.id],
        mode: "text",
        type: "scatter",
        name: UNSHARED_SPECTRUM,
        legendgroup: UNSHARED_SPECTRUM,
        text: ["S"],
        textposition: "bottom center",
        textfont: {
          color: pending ? colors.requested : colors.available,
          size: 16,
        },
        marker: { line: { width: 1 }, opacity: 1 },
        visible: true,
        showlegend: false,
        hoverlabel: {
          bgcolor: hoverBackground,
          font: { size: 14 },
          align: "left",
        },
        hovertemplate: hovertext,
      };
    });

interface RequestSpectrumDialogProps {
  objId: string;
  spectrum: SpectrumAvailability | null;
  onClose: () => void;
}

/** Confirmation for asking an owner for one spectrum. */
export const RequestSpectrumDialog = ({
  objId,
  spectrum,
  onClose,
}: RequestSpectrumDialogProps) => {
  const [message, setMessage] = useState("");
  const [requestAccess, { isLoading }] = useRequestDataAccessMutation();

  if (spectrum == null) return null;
  const pending = spectrum.request?.status === "pending";

  const submit = async () => {
    const result = await requestAccess({
      objId,
      spectrumIDs: [spectrum.id],
      message: message || null,
    });
    if (!("error" in result)) {
      setMessage("");
      onClose();
    }
  };

  return (
    <Dialog open onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>
        {pending ? "Access already requested" : "Ask for this spectrum"}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          {`${spectrum.instrument?.name ?? "Spectrum"}`}
          {spectrum.observed_at
            ? `, taken ${spectrum.observed_at.slice(0, 10)}`
            : ""}
          {`, owned by ${spectrum.owner?.username ?? "another user"}.`}
        </Typography>
        {pending ? (
          <Typography variant="body2">
            The owner has not answered yet. You will be notified when they do.
          </Typography>
        ) : (
          <>
            <TextField
              label="Note to the owner (optional)"
              size="small"
              fullWidth
              multiline
              value={message}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                setMessage(event.target.value)
              }
              style={{ marginTop: "0.5rem" }}
            />
            <Button
              primary
              size="small"
              disabled={isLoading}
              onClick={submit}
              style={{ marginTop: "0.75rem" }}
              data-testid="request-spectrum-button"
            >
              Ask for it
            </Button>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
