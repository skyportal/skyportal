import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Pagination from "@mui/material/Pagination";
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
import BrokerAlertCard, { AlertOption } from "./BrokerAlertCard";
import BrokerFilterManager from "./BrokerFilterManager";
import LasairFilterBuilder from "./LasairFilterBuilder";

const PAGE_SIZE = 12;

const useStyles = makeStyles()((theme) => ({
  root: { padding: theme.spacing(2) },
  form: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    gap: theme.spacing(2),
    marginBottom: theme.spacing(2),
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(520px, 1fr))",
    gap: theme.spacing(2),
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

interface NormalizedAlert extends AlertOption {
  objectId?: string;
}

// Pull the fields we render from a provider alert (candidate may be nested).
const normalizeAlert = (a: any): NormalizedAlert => {
  const cand = a?.candidate ?? a ?? {};
  return {
    // `object`/`diaObjectId` are the objectId in Lasair cone/LSST result rows.
    objectId:
      a?.objectId ??
      a?.diaObjectId ??
      a?.object_id ??
      a?.object ??
      cand?.objectId,
    candid: cand?.candid ?? a?.candid,
    ra: cand?.ra ?? a?.ra,
    dec: cand?.dec ?? a?.dec,
    magpsf: cand?.magpsf ?? a?.magpsf ?? cand?.mag,
    jd: cand?.jd ?? a?.jd,
  };
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
  const [page, setPage] = useState(1);

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
    setPage(1);
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
    setPage(1);
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
    setPage(1);
    triggerFilter({ brokerId, params });
  };

  // Group alerts by object so each card is one object with a per-alert selector.
  const rows = asArray(data);
  const objectGroups: { objectId: string; alerts: NormalizedAlert[] }[] = [];
  if (rows) {
    const byObject = new Map<string, NormalizedAlert[]>();
    rows.map(normalizeAlert).forEach((a) => {
      // Require an objectId; candid is optional (Lasair cone rows have none).
      if (!a.objectId) return;
      if (!byObject.has(a.objectId)) byObject.set(a.objectId, []);
      byObject.get(a.objectId)!.push(a);
    });
    byObject.forEach((alerts, oid) =>
      objectGroups.push({ objectId: oid, alerts }),
    );
  }

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
            (objectGroups.length > 0 ? (
              <>
                {(() => {
                  const pageCount = Math.ceil(objectGroups.length / PAGE_SIZE);
                  const current = Math.min(page, pageCount);
                  const start = (current - 1) * PAGE_SIZE;
                  const pageGroups = objectGroups.slice(
                    start,
                    start + PAGE_SIZE,
                  );
                  return (
                    <>
                      <Typography variant="subtitle2" gutterBottom>
                        {`${objectGroups.length} object${
                          objectGroups.length === 1 ? "" : "s"
                        } — showing ${start + 1}–${start + pageGroups.length}`}
                      </Typography>
                      <div className={classes.grid}>
                        {pageGroups.map((g) => (
                          <BrokerAlertCard
                            key={g.objectId}
                            brokerId={brokerId as number}
                            objectId={g.objectId}
                            survey={survey}
                            alerts={g.alerts}
                          />
                        ))}
                      </div>
                      {pageCount > 1 && (
                        <Pagination
                          count={pageCount}
                          page={current}
                          onChange={(_e, p) => setPage(p)}
                          sx={{
                            mt: 2,
                            display: "flex",
                            justifyContent: "center",
                          }}
                        />
                      )}
                    </>
                  );
                })()}
              </>
            ) : (
              <Paper className={classes.json} variant="outlined">
                {rows ? (
                  <Typography variant="subtitle2" gutterBottom>
                    {`${rows.length} result${rows.length === 1 ? "" : "s"}`}
                  </Typography>
                ) : null}
                <pre className={classes.pre}>
                  {JSON.stringify(data, null, 2)}
                </pre>
              </Paper>
            ))}
        </>
      )}
    </Box>
  );
};

export default BrokerAlerts;
