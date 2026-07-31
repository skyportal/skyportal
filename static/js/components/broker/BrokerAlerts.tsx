import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import {
  useGetBrokersQuery,
  useLazyGetBrokerAlertsQuery,
  useLazyTestBrokerFilterQuery,
} from "../../ducks/brokers";
import BrokerAlertDialog from "./BrokerAlertDialog";
import BrokerAlertTable, { AlertRow } from "./BrokerAlertTable";
import BrokerFilterManager from "./BrokerFilterManager";
import LasairFilterBuilder from "./LasairFilterBuilder";

const useStyles = makeStyles()((theme) => ({
  root: { padding: theme.spacing(2) },
  form: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    gap: theme.spacing(2),
    marginBottom: theme.spacing(2),
  },
  json: { padding: theme.spacing(2), maxHeight: "50vh", overflow: "auto" },
  pre: {
    margin: 0,
    fontFamily: "monospace",
    fontSize: "0.75rem",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
}));

const asArray = (result: unknown): unknown[] | null => {
  if (Array.isArray(result)) return result;
  if (
    result &&
    typeof result === "object" &&
    Array.isArray((result as { objects?: unknown[] }).objects)
  ) {
    return (result as { objects: unknown[] }).objects;
  }
  return null;
};

const FID_BAND: Record<number, string> = { 1: "g", 2: "r", 3: "i" };

const DEG = Math.PI / 180;

// Angular separation in arcsec, for the cone-search separation column.
const separation = (ra1: number, dec1: number, ra2: number, dec2: number) => {
  const d =
    Math.sin(dec1 * DEG) * Math.sin(dec2 * DEG) +
    Math.cos(dec1 * DEG) * Math.cos(dec2 * DEG) * Math.cos((ra1 - ra2) * DEG);
  return Math.acos(Math.min(1, Math.max(-1, d))) * (180 / Math.PI) * 3600;
};

// Pull the columns we render from a provider alert (candidate may be nested).
// `raw` keeps the whole record so the detail dialog can show every field.
const toRow = (a: any, index: number, center: [number, number] | null) => {
  const cand = a?.candidate ?? a ?? {};
  const cls = a?.classifications ?? {};
  // `object`/`diaObjectId` are the objectId in Lasair cone/LSST result rows.
  const objectId =
    a?.objectId ??
    a?.diaObjectId ??
    a?.object_id ??
    a?.object ??
    cand?.objectId;
  const candid = cand?.candid ?? a?.candid;
  const ra = cand?.ra ?? a?.ra;
  const dec = cand?.dec ?? a?.dec;
  return {
    id: String(candid ?? `${objectId}-${index}`),
    objectId,
    candid,
    ra,
    dec,
    jd: cand?.jd ?? a?.jd,
    band: cand?.band ?? FID_BAND[cand?.fid],
    magpsf: cand?.magpsf ?? a?.magpsf ?? cand?.mag,
    sigmapsf: cand?.sigmapsf,
    snr: cand?.snr_psf,
    isdiffpos: cand?.isdiffpos,
    // Real-bogus score: `drb` (ZTF), `reliability` (LSST), `rb` (older ZTF).
    drb: cand?.drb ?? cand?.reliability ?? cand?.rb,
    programid: cand?.programid,
    braai: cls?.braai,
    acai_h: cls?.acai_h,
    acai_n: cls?.acai_n,
    acai_o: cls?.acai_o,
    acai_v: cls?.acai_v,
    acai_b: cls?.acai_b,
    btsbot: cls?.btsbot,
    separation:
      center && typeof ra === "number" && typeof dec === "number"
        ? separation(center[0], center[1], ra, dec)
        : undefined,
    raw: a,
  } as AlertRow;
};

const BrokerAlerts = () => {
  const { classes } = useStyles();
  const { data: brokers, isLoading: brokersLoading } = useGetBrokersQuery();

  const [brokerId, setBrokerId] = useState<number | "">("");
  const [objectId, setObjectId] = useState("");
  const [ra, setRa] = useState("");
  const [dec, setDec] = useState("");
  const [radius, setRadius] = useState("");
  const [mode, setMode] = useState<"search" | "preview">("search");
  // The row whose detail dialog is open, if any.
  const [selected, setSelected] = useState<AlertRow | null>(null);
  // Position the results were searched at, for the separation column.
  const [center, setCenter] = useState<[number, number] | null>(null);
  // Bumped per search so the table re-applies its default sort.
  const [searchKey, setSearchKey] = useState(0);

  const [
    triggerAlerts,
    { data: alertData, error: alertError, isFetching: alertFetching },
  ] = useLazyGetBrokerAlertsQuery();
  const [
    triggerFilter,
    { data: filterData, error: filterError, isFetching: filterFetching },
  ] = useLazyTestBrokerFilterQuery();

  const data = mode === "preview" ? filterData : alertData;
  const error = mode === "preview" ? filterError : alertError;
  const isFetching = alertFetching || filterFetching;

  const activeBrokers = (brokers || []).filter((b) => b.active);
  const selectedBroker = activeBrokers.find((b) => b.id === brokerId);
  const survey = selectedBroker?.surveys?.[0] ?? "ZTF";
  const canPreview = Boolean(selectedBroker?.capabilities?.["test_filter"]);

  // Deep link (e.g. the source page's "Search alerts" button): prefill the
  // search from ?objectId=/ra/dec/radius, auto-select a broker for ?survey=, and
  // run the search once brokers have loaded. Uses the URL values directly so the
  // query isn't delayed by the state updates it also seeds.
  const [searchParams] = useSearchParams();
  const autoSearched = useRef(false);
  useEffect(() => {
    if (autoSearched.current || !activeBrokers.length) return;
    const oid = searchParams.get("objectId") || "";
    const uRa = searchParams.get("ra") || "";
    const uDec = searchParams.get("dec") || "";
    const uRadius = searchParams.get("radius") || "";
    if (!oid && !uRa) return;
    const uSurvey = searchParams.get("survey");
    const match =
      (uSurvey && activeBrokers.find((b) => b.surveys?.includes(uSurvey))) ||
      activeBrokers.find((b) => b.capabilities?.["query_alerts"]) ||
      activeBrokers[0];
    if (!match) return;

    autoSearched.current = true;
    setBrokerId(match.id);
    setObjectId(oid);
    setRa(uRa);
    setDec(uDec);
    setRadius(uRadius);
    setMode("search");
    setCenter(uRa && uDec ? [Number(uRa), Number(uDec)] : null);
    setSearchKey((k) => k + 1);
    triggerAlerts({
      brokerId: match.id,
      params: {
        objectId: oid || undefined,
        ra: uRa || undefined,
        dec: uDec || undefined,
        radius: uRadius || undefined,
        radius_units: uRadius ? "arcsec" : undefined,
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeBrokers.length]);

  const onSearch = () => {
    if (brokerId === "") return;
    setMode("search");
    setCenter(ra && dec ? [Number(ra), Number(dec)] : null);
    setSearchKey((k) => k + 1);
    triggerAlerts({
      brokerId,
      params: {
        objectId: objectId || undefined,
        ra: ra || undefined,
        dec: dec || undefined,
        radius: radius || undefined,
        radius_units: radius ? "arcsec" : undefined,
      },
    });
  };

  const onPreview = (params: Record<string, unknown>) => {
    if (brokerId === "") return;
    setMode("preview");
    setCenter(null);
    setSearchKey((k) => k + 1);
    triggerFilter({ brokerId, params });
  };

  // One row per alert. Rows without an objectId can't be acted on (saved, or
  // looked up for cutouts), so they fall through to the raw JSON view.
  const results = asArray(data);
  const alertRows = (results ?? [])
    .map((a, i) => toRow(a, i, center))
    .filter((r) => r.objectId);
  const objectCount = new Set(alertRows.map((r) => r.objectId)).size;

  return (
    <Box className={classes.root}>
      <Typography variant="h5" gutterBottom>
        Broker alerts
      </Typography>

      {brokersLoading ? (
        <CircularProgress />
      ) : activeBrokers.length === 0 ? (
        <Typography color="text.secondary">
          No active brokers configured. Add one via the API (POST /api/brokers).
        </Typography>
      ) : (
        <>
          <div className={classes.form}>
            <FormControl size="small" sx={{ minWidth: 220 }}>
              <InputLabel id="broker-select-label">Broker</InputLabel>
              <Select
                labelId="broker-select-label"
                label="Broker"
                value={brokerId}
                onChange={(e) => setBrokerId(e.target.value as number)}
              >
                {activeBrokers.map((b) => (
                  <MenuItem key={b.id} value={b.id}>
                    {b.name} ({b.broker_classname})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Object ID"
              value={objectId}
              onChange={(e) => setObjectId(e.target.value)}
            />
            <TextField
              size="small"
              label="RA (deg)"
              value={ra}
              onChange={(e) => setRa(e.target.value)}
            />
            <TextField
              size="small"
              label="Dec (deg)"
              value={dec}
              onChange={(e) => setDec(e.target.value)}
            />
            <TextField
              size="small"
              label="Radius (arcsec)"
              value={radius}
              onChange={(e) => setRadius(e.target.value)}
            />
            <Button
              variant="contained"
              onClick={onSearch}
              disabled={brokerId === "" || isFetching}
            >
              {isFetching ? "Searching…" : "Search"}
            </Button>
          </div>

          {selectedBroker &&
            selectedBroker.filter_kind !== "none" &&
            (selectedBroker.filter_kind === "pipeline" ? (
              <BrokerFilterManager brokerId={brokerId as number} />
            ) : selectedBroker.filter_kind === "query" && canPreview ? (
              <LasairFilterBuilder
                brokerId={brokerId as number}
                survey={survey}
                onPreview={onPreview}
              />
            ) : (
              <div className={classes.form}>
                <Typography variant="body2" color="text.secondary">
                  {`Filter kind: ${selectedBroker.filter_kind} — editor coming soon.`}
                </Typography>
              </div>
            ))}

          {error && (
            <Typography color="error" gutterBottom>
              {`Error: ${JSON.stringify(
                (error as { data?: unknown }).data ?? error,
              )}`}
            </Typography>
          )}

          {data !== undefined &&
            (alertRows.length > 0 ? (
              <>
                <Typography variant="subtitle2" gutterBottom>
                  {`${alertRows.length} alert${
                    alertRows.length === 1 ? "" : "s"
                  } across ${objectCount} object${
                    objectCount === 1 ? "" : "s"
                  } — click a row for cutouts and metadata`}
                </Typography>
                <BrokerAlertTable
                  rows={alertRows}
                  onRowClick={setSelected}
                  hasPosition={center !== null}
                  searchKey={searchKey}
                />
              </>
            ) : (
              <Paper className={classes.json} variant="outlined">
                {results ? (
                  <Typography variant="subtitle2" gutterBottom>
                    {`${results.length} result${
                      results.length === 1 ? "" : "s"
                    }`}
                  </Typography>
                ) : null}
                <pre className={classes.pre}>
                  {JSON.stringify(data, null, 2)}
                </pre>
              </Paper>
            ))}

          <BrokerAlertDialog
            brokerId={brokerId as number}
            survey={survey}
            alert={selected}
            onClose={() => setSelected(null)}
          />
        </>
      )}
    </Box>
  );
};

export default BrokerAlerts;
