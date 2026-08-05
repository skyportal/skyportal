import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Pagination from "@mui/material/Pagination";
import Paper from "@mui/material/Paper";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import {
  useGetBrokersQuery,
  useLazyGetBrokerAlertsQuery,
  useLazyTestBrokerFilterQuery,
} from "../../ducks/brokers";
import BrokerAlertCard, { AlertOption } from "./BrokerAlertCard";
import BrokerAlertFilters from "./BrokerAlertFilters";
import FilterCatalog from "./FilterCatalog";
import { AlertFilter, fieldsOf, flatten, matchesFilters } from "./alertFields";
import NewBrokerFilterForm from "./NewBrokerFilterForm";
import LasairFilterBuilder from "./lasair/LasairFilterBuilder";
import Spinner from "../Spinner";

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
  gridSingle: { gridTemplateColumns: "1fr" },
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
    raw: a,
  };
};

const TooltipTab = ({ tooltip, ...tabProps }: any) => (
  <Tooltip title={tooltip} placement="top">
    <span style={{ display: "inline-flex" }}>
      <Tab {...tabProps} />
    </span>
  </Tooltip>
);

const Broker = () => {
  const { classes, cx } = useStyles();
  const { brokerId: brokerIdParam } = useParams();
  const brokerId = Number(brokerIdParam);
  const { data: brokers, isLoading: brokersLoading } = useGetBrokersQuery();

  const [objectId, setObjectId] = useState("");
  const [ra, setRa] = useState("");
  const [dec, setDec] = useState("");
  const [radius, setRadius] = useState("");
  const [mode, setMode] = useState<"search" | "preview">("search");
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState(0);
  const [filters, setFilters] = useState<AlertFilter[]>([]);

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

  const broker = (brokers || []).find((b) => b.id === brokerId);
  const survey = broker?.surveys?.[0] ?? "ZTF";
  const canQuery = Boolean(broker?.capabilities?.["query_alerts"]);
  const canPreview = Boolean(broker?.capabilities?.["test_filter"]);
  const hasFilters = Boolean(broker && broker.filter_kind !== "none");
  // A broker may expose only some of the tabs (ingestion-only, filters-only...)
  const TABS = [
    {
      label: "Alerts",
      enabled: canQuery,
      reason: `${broker?.name} does not support alerts query.`,
    },
    {
      label: "Filters",
      enabled: hasFilters,
      reason: `${broker?.name} does not support filters.`,
    },
    {
      label: "New filter",
      enabled: broker?.filter_kind === "pipeline",
      reason: `${broker?.name} does not support filters creation.`,
    },
  ];
  const activeTab = TABS[tab]?.enabled ? tab : TABS.findIndex((t) => t.enabled);

  const [searchParams] = useSearchParams();
  const autoSearched = useRef(false);
  // Run the search straight away when the URL carries a target
  useEffect(() => {
    if (autoSearched.current || !broker) return;
    autoSearched.current = true;
    const oid = searchParams.get("objectId") || "";
    const uRa = searchParams.get("ra") || "";
    const uDec = searchParams.get("dec") || "";
    const uRadius = searchParams.get("radius") || "";
    if (!oid && !uRa) return;

    setObjectId(oid);
    setRa(uRa);
    setDec(uDec);
    setRadius(uRadius);
    setMode("search");
    setPage(1);
    triggerAlerts({
      brokerId,
      params: {
        objectId: oid || undefined,
        ra: uRa || undefined,
        dec: uDec || undefined,
        radius: uRadius || undefined,
        radius_units: uRadius ? "arcsec" : undefined,
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [broker]);

  // Object ID and cone search are mutually exclusive
  const coneDisabled = objectId.trim() !== "";
  const coneReason =
    "Disabled while an Object ID is set: the search is done by object, not by position.";

  const onSearch = () => {
    if (!broker) return;
    setMode("search");
    setPage(1);
    setFilters([]);
    triggerAlerts({
      brokerId,
      params: {
        objectId: objectId || undefined,
        ra: coneDisabled ? undefined : ra || undefined,
        dec: coneDisabled ? undefined : dec || undefined,
        radius: coneDisabled ? undefined : radius || undefined,
        radius_units: !coneDisabled && radius ? "arcsec" : undefined,
      },
    });
  };

  const onPreview = (params: Record<string, unknown>) => {
    if (!broker) return;
    setMode("preview");
    setPage(1);
    setFilters([]);
    triggerFilter({ brokerId, params });
  };

  const rows = asArray(data);
  // Flat view of the response: the filter fields and the CSV columns.
  const flatRows = useMemo(() => (rows ?? []).map((r) => flatten(r)), [rows]);
  const fields = useMemo(() => fieldsOf(flatRows), [flatRows]);
  const kept = rows?.filter((_r, i) =>
    matchesFilters(flatRows[i] ?? {}, filters),
  );

  // Group alerts by object so each card is one object with a per-alert selector.
  const objectGroups: { objectId: string; alerts: NormalizedAlert[] }[] = [];
  if (kept) {
    const byObject = new Map<string, NormalizedAlert[]>();
    kept.map(normalizeAlert).forEach((a) => {
      // Require an objectId; candid is optional (Lasair cone rows have none).
      if (!a.objectId) return;
      if (!byObject.has(a.objectId)) byObject.set(a.objectId, []);
      byObject.get(a.objectId)!.push(a);
    });
    byObject.forEach((alerts, oid) =>
      objectGroups.push({ objectId: oid, alerts }),
    );
  }

  if (brokersLoading) return <Spinner />;

  return (
    <Box className={classes.root}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <IconButton component={Link} to="/brokers" aria-label="back to brokers">
          <ArrowBackIcon />
        </IconButton>
        <Box>
          <Typography variant="h5">
            {broker ? broker.name : "Broker"}
          </Typography>
          {broker && (
            <Typography variant="body2" color="text.secondary">
              {broker.broker_classname}
            </Typography>
          )}
        </Box>
      </Box>

      {!broker ? (
        <Typography color="text.secondary">
          {`No broker with id ${brokerIdParam}.`}
        </Typography>
      ) : (
        <>
          <Tabs
            sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}
            value={activeTab === -1 ? false : activeTab}
            onChange={(_event, value) => setTab(value)}
          >
            {TABS.map((t) => (
              <TooltipTab
                key={t.label}
                label={t.label}
                disabled={!t.enabled}
                tooltip={t.enabled ? "" : t.reason}
              />
            ))}
          </Tabs>

          {activeTab === 0 && (
            <div className={classes.form}>
              <TextField
                size="small"
                label="Object ID"
                value={objectId}
                onChange={(e) => setObjectId(e.target.value)}
              />
              <Tooltip title={coneDisabled ? coneReason : ""}>
                <span>
                  <TextField
                    size="small"
                    label="RA (deg)"
                    value={ra}
                    disabled={coneDisabled}
                    onChange={(e) => setRa(e.target.value)}
                  />
                </span>
              </Tooltip>
              <Tooltip title={coneDisabled ? coneReason : ""}>
                <span>
                  <TextField
                    size="small"
                    label="Dec (deg)"
                    value={dec}
                    disabled={coneDisabled}
                    onChange={(e) => setDec(e.target.value)}
                  />
                </span>
              </Tooltip>
              <Tooltip title={coneDisabled ? coneReason : ""}>
                <span>
                  <TextField
                    size="small"
                    label="Radius (arcsec)"
                    value={radius}
                    disabled={coneDisabled}
                    onChange={(e) => setRadius(e.target.value)}
                  />
                </span>
              </Tooltip>
              <Button
                variant="contained"
                onClick={onSearch}
                disabled={isFetching}
              >
                {isFetching ? "Searching…" : "Search"}
              </Button>
            </div>
          )}

          {activeTab === 1 &&
            (broker.filter_kind === "pipeline" ? (
              <FilterCatalog brokerId={brokerId} />
            ) : broker.filter_kind === "query" && canPreview ? (
              <LasairFilterBuilder
                brokerId={brokerId}
                survey={survey}
                onPreview={onPreview}
              />
            ) : (
              <div className={classes.form}>
                <Typography variant="body2" color="text.secondary">
                  {`Filter kind: ${broker.filter_kind} — editor coming soon.`}
                </Typography>
              </div>
            ))}

          {activeTab === 2 && <NewBrokerFilterForm brokerId={brokerId} />}

          {activeTab === (mode === "preview" ? 1 : 0) && (
            <>
              {error && (
                <Typography color="error" gutterBottom>
                  {(error as any)?.data?.message || "Failed to query broker."}
                </Typography>
              )}

              {rows && rows.length > 0 && (
                <BrokerAlertFilters
                  fields={fields}
                  filters={filters}
                  onChange={setFilters}
                />
              )}

              {data !== undefined &&
                (objectGroups.length > 0 ? (
                  <>
                    {(() => {
                      const pageCount = Math.ceil(
                        objectGroups.length / PAGE_SIZE,
                      );
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
                          <div
                            className={cx(classes.grid, {
                              [classes.gridSingle]: pageGroups.length === 1,
                            })}
                          >
                            {pageGroups.map((g) => (
                              <BrokerAlertCard
                                key={g.objectId}
                                brokerId={brokerId}
                                brokerClassname={broker.broker_classname}
                                objectId={g.objectId}
                                survey={survey}
                                alerts={g.alerts}
                                expanded={pageGroups.length === 1}
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
                    {kept ? (
                      <Typography variant="subtitle2" gutterBottom>
                        {`${kept.length} result${kept.length === 1 ? "" : "s"}`}
                      </Typography>
                    ) : null}
                    <pre className={classes.pre}>
                      {JSON.stringify(kept ?? data, null, 2)}
                    </pre>
                  </Paper>
                ))}
            </>
          )}
        </>
      )}
    </Box>
  );
};

export default Broker;
