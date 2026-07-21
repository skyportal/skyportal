import { useState } from "react";

import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import { Link } from "react-router-dom";
import { makeStyles } from "tss-react/mui";

import {
  useGetBrokerAlertQuery,
  useGetSourceIfSavedQuery,
} from "../../ducks/brokers";
import CutoutTriplet from "./CutoutTriplet";
import BrokerAlertLightCurve from "./BrokerAlertLightCurve";
import BrokerSaveButton from "./BrokerSaveButton";

const useStyles = makeStyles()((theme) => ({
  card: { height: "100%" },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: theme.spacing(1),
    marginBottom: theme.spacing(1),
  },
  objectId: { fontWeight: 600, fontSize: "1rem" },
  meta: {
    fontFamily: "monospace",
    fontSize: "0.8rem",
    color: theme.palette.text.secondary,
  },
  body: {
    display: "flex",
    flexWrap: "wrap",
    gap: theme.spacing(1),
    alignItems: "flex-start",
  },
  cutouts: { flex: "1 1 240px", minWidth: 220 },
  lc: { flex: "1 1 260px", minWidth: 240 },
  footer: {
    marginTop: theme.spacing(1),
    display: "flex",
    alignItems: "center",
    gap: theme.spacing(1),
    flexWrap: "wrap",
  },
  chips: { display: "flex", gap: theme.spacing(0.5), flexWrap: "wrap" },
}));

export interface AlertOption {
  candid: string | number;
  ra?: number;
  dec?: number;
  magpsf?: number;
  jd?: number;
}

interface BrokerAlertCardProps {
  brokerId: number;
  objectId: string;
  survey: string;
  alerts: AlertOption[];
}

const num = (v: number | undefined, d = 4) =>
  typeof v === "number" ? v.toFixed(d) : "—";

const BrokerAlertCard = ({
  brokerId,
  objectId,
  survey,
  alerts,
}: BrokerAlertCardProps) => {
  const { classes } = useStyles();
  // Newest alert first (highest jd), so the default selection is the latest.
  const sorted = [...alerts].sort((a, b) => (b.jd ?? 0) - (a.jd ?? 0));
  const [candid, setCandid] = useState<string | number | undefined>(
    sorted[0]?.candid,
  );
  const selected = sorted.find((a) => a.candid === candid) ?? sorted[0];

  // Full object (also used by the light curve; RTK dedupes the request). For
  // brokers whose alert rows omit ra/dec/candid (e.g. Lasair cone results), we
  // fall back to the fetched object's candidate.
  const { data: alertData } = useGetBrokerAlertQuery(
    { brokerId, alertId: objectId },
    { skip: !objectId },
  );
  const cand = alertData?.candidate ?? {};
  const ra = selected?.ra ?? cand.ra;
  const dec = selected?.dec ?? cand.dec;
  const magpsf = selected?.magpsf ?? cand.magpsf;
  // babamul/BOOM key cutouts by candid (present on the alert row); Lasair rows
  // have no candid, so its cutouts are keyed by objectId.
  const cutoutKey = selected?.candid ?? objectId;

  // Is this object already saved as a source? (drives the saved-groups chips.)
  const { data: source } = useGetSourceIfSavedQuery(objectId, {
    skip: !objectId,
  });
  const savedGroups = (source as any)?.groups ?? [];

  return (
    <Card variant="outlined" className={classes.card}>
      <CardContent>
        <div className={classes.header}>
          <span className={classes.objectId}>{objectId}</span>
          {sorted.length > 1 && (
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel id={`alert-${objectId}`}>Alert</InputLabel>
              <Select
                labelId={`alert-${objectId}`}
                label="Alert"
                value={candid}
                onChange={(e) => setCandid(e.target.value as string | number)}
              >
                {sorted.map((a) => (
                  <MenuItem key={String(a.candid)} value={a.candid}>
                    {`MJD ${
                      a.jd != null ? (a.jd - 2400000.5).toFixed(4) : "—"
                    } · mag ${num(a.magpsf, 2)} · ${a.candid}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </div>

        <div className={classes.meta}>
          {`ra ${num(ra)}  dec ${num(dec)}  mag ${num(magpsf, 2)}  ·  ${
            sorted.length
          } alert${sorted.length === 1 ? "" : "s"}`}
        </div>

        <div className={classes.body}>
          {ra != null && dec != null && (
            <div className={classes.cutouts}>
              <CutoutTriplet
                brokerId={brokerId}
                candid={cutoutKey}
                survey={survey}
                ra={ra}
                dec={dec}
              />
            </div>
          )}
          <div className={classes.lc}>
            <BrokerAlertLightCurve brokerId={brokerId} objectId={objectId} />
          </div>
        </div>

        <div className={classes.footer}>
          {source ? (
            <>
              <Chip size="small" color="primary" label="Saved" />
              <div className={classes.chips}>
                {savedGroups.map((g: any) => (
                  <Chip
                    key={g.id}
                    size="small"
                    variant="outlined"
                    label={g.name}
                  />
                ))}
              </div>
              <Link to={`/source/${objectId}`}>View source</Link>
            </>
          ) : (
            <BrokerSaveButton brokerId={brokerId} objectId={objectId} />
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default BrokerAlertCard;
