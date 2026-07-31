import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";
import { makeStyles } from "tss-react/mui";

import {
  useGetBrokerAlertQuery,
  useGetSourceIfSavedQuery,
} from "../../ducks/brokers";
import { AlertRow } from "./BrokerAlertTable";
import BrokerAlertLightCurve from "./BrokerAlertLightCurve";
import BrokerAlertMetadata from "./BrokerAlertMetadata";
import BrokerSaveButton from "./BrokerSaveButton";
import CutoutTriplet from "./CutoutTriplet";

const useStyles = makeStyles()((theme) => ({
  title: {
    display: "flex",
    alignItems: "center",
    gap: theme.spacing(1),
    flexWrap: "wrap",
  },
  candid: { fontFamily: "monospace", fontSize: "0.85rem" },
  body: {
    display: "flex",
    flexWrap: "wrap",
    gap: theme.spacing(2),
    alignItems: "flex-start",
  },
  cutouts: { flex: "1 1 260px", minWidth: 240 },
  lc: { flex: "1 1 320px", minWidth: 280 },
  actions: { gap: theme.spacing(1), flexWrap: "wrap" },
}));

interface BrokerAlertDialogProps {
  brokerId: number;
  survey: string;
  alert: AlertRow | null;
  onClose: () => void;
}

/**
 * Detail view for one alert picked out of the table: cutout triplet, light
 * curve, full metadata, and the save/view-source action.
 */
const BrokerAlertDialog = ({
  brokerId,
  survey,
  alert,
  onClose,
}: BrokerAlertDialogProps) => {
  const { classes } = useStyles();
  const objectId = alert?.objectId;

  // Full object, also used by the light curve (RTK dedupes the request). Rows
  // from providers that omit ra/dec (e.g. Lasair cone results) fall back to it.
  const { data: alertData } = useGetBrokerAlertQuery(
    { brokerId, alertId: objectId as string },
    { skip: !objectId },
  );
  const { data: source } = useGetSourceIfSavedQuery(objectId as string, {
    skip: !objectId,
  });

  if (!alert || !objectId) return null;

  const cand = alertData?.candidate ?? {};
  const ra = alert.ra ?? cand.ra;
  const dec = alert.dec ?? cand.dec;
  // babamul/BOOM key cutouts by candid; Lasair rows have none, so fall back to
  // the objectId its cutouts are keyed by.
  const cutoutKey = alert.candid ?? objectId;
  const savedGroups = (source as any)?.groups ?? [];

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle className={classes.title}>
        <span>{objectId}</span>
        {alert.candid != null && (
          <span className={classes.candid}>{`candid ${alert.candid}`}</span>
        )}
        {source && <Chip size="small" color="primary" label="Saved" />}
        {savedGroups.map((g: any) => (
          <Chip key={g.id} size="small" variant="outlined" label={g.name} />
        ))}
      </DialogTitle>
      <DialogContent dividers>
        <div className={classes.body}>
          {ra != null && dec != null ? (
            <div className={classes.cutouts}>
              <CutoutTriplet
                brokerId={brokerId}
                candid={cutoutKey}
                survey={survey}
                ra={ra}
                dec={dec}
              />
            </div>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No position on this alert, so no cutouts.
            </Typography>
          )}
          <div className={classes.lc}>
            <BrokerAlertLightCurve brokerId={brokerId} objectId={objectId} />
          </div>
        </div>
        <BrokerAlertMetadata alert={alert.raw ?? alertData} />
      </DialogContent>
      <DialogActions className={classes.actions}>
        {source ? (
          <Button component={Link} to={`/source/${objectId}`} size="small">
            View source
          </Button>
        ) : (
          <BrokerSaveButton brokerId={brokerId} objectId={objectId} />
        )}
        <Button onClick={onClose} size="small">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BrokerAlertDialog;
