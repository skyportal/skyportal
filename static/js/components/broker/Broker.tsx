import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Pagination from "@mui/material/Pagination";
import Paper from "@mui/material/Paper";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  useGetBrokersQuery,
  useLazyGetBrokerAlertsQuery,
  useLazyTestBrokerFilterQuery,
} from "../../ducks/brokers";
import BrokerAlertCard, { AlertOption } from "./BrokerAlertCard";
import BrokerAlertFilters from "./BrokerAlertFilters";
import BrokerCredentialsForm from "./BrokerCredentialsForm";
import FilterCatalog from "./FilterCatalog";
import { AlertFilter, fieldsOf, flatten, matchesFilters } from "./alertFields";
import NewBrokerFilterDialog from "./NewBrokerFilterDialog";
import LasairFilterBuilder from "./lasair/LasairFilterBuilder";
import Spinner from "../Spinner";
import { dec_to_deg, ra_to_deg } from "../../units";

const PAGE_SIZE = 12;

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
    candid: cand?.candid ?? a?.candid ?? a?._id ?? cand?.diaSourceId,
    ra: cand?.ra ?? a?.ra,
    dec: cand?.dec ?? a?.dec,
    magpsf: cand?.magpsf ?? a?.magpsf ?? cand?.mag,
    jd: cand?.jd ?? a?.jd,
    raw: a,
  };
};

// Mirrors the backend's survey_from_object_id.
const surveyFromObjectId = (
  objectId: string,
  surveys: string[],
): string | undefined => {
  const id = objectId.trim();
  let survey;
  if (/^ZTF\d{2}[a-z]{7}$/.test(id)) survey = "ZTF";
  else if (/^\d+$/.test(id)) survey = "LSST";
  return survey && surveys.includes(survey) ? survey : undefined;
};

const TooltipTab = ({ tooltip, ...tabProps }: any) => (
  <Tooltip title={tooltip} placement="top">
    <Box component="span" sx={{ display: "inline-flex" }}>
      <Tab {...tabProps} />
    </Box>
  </Tooltip>
);

const Broker = () => {
  const { brokerId: brokerIdParam } = useParams();
  const brokerId = Number(brokerIdParam);
  const { data: brokers, isLoading: brokersLoading } = useGetBrokersQuery();

  const [objectId, setObjectId] = useState("");
  const [ra, setRa] = useState("");
  const [dec, setDec] = useState("");
  const [radius, setRadius] = useState("");
  const [survey, setSurvey] = useState("");
  const [queriedSurvey, setQueriedSurvey] = useState("");
  const [mode, setMode] = useState<"search" | "preview">("search");
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState(0);
  const [newFilterOpen, setNewFilterOpen] = useState(false);
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
  const surveys = broker?.surveys ?? [];
  const searchSurvey =
    survey || surveyFromObjectId(objectId, surveys) || surveys[0] || "ZTF";
  const canQuery = Boolean(broker?.capabilities?.["query_alerts"]);
  const canPreview = Boolean(broker?.capabilities?.["test_filter"]);
  const hasFilters = Boolean(broker && broker.filter_kind !== "none");
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
    { label: "Credentials", enabled: true, reason: "" },
  ];
  const activeTab = TABS[tab]?.enabled ? tab : TABS.findIndex((t) => t.enabled);

  const search = (params: {
    objectId: string;
    survey: string;
    ra?: string;
    dec?: string;
    radius?: string;
  }) => {
    setMode("search");
    setPage(1);
    setFilters([]);
    setQueriedSurvey(params.survey);
    triggerAlerts({
      brokerId,
      params: {
        objectId: params.objectId || undefined,
        ra: params.ra ? ra_to_deg(params.ra) : undefined,
        dec: params.dec ? dec_to_deg(params.dec) : undefined,
        radius: params.radius || undefined,
        radius_units: params.radius ? "arcsec" : undefined,
        survey: params.survey,
      },
    });
  };

  const [searchParams] = useSearchParams();
  const autoSearched = useRef(false);
  useEffect(() => {
    if (autoSearched.current || !broker) return;
    autoSearched.current = true;
    const oid = searchParams.get("objectId") || "";
    const uRa = searchParams.get("ra") || "";
    const uDec = searchParams.get("dec") || "";
    const uRadius = searchParams.get("radius") || "";
    if (!oid && !uRa) return;

    const uSurvey =
      searchParams.get("survey") ||
      surveyFromObjectId(oid, broker.surveys ?? []) ||
      broker.surveys?.[0] ||
      "ZTF";
    setObjectId(oid);
    setRa(uRa);
    setDec(uDec);
    setRadius(uRadius);
    setSurvey(uSurvey);
    search({
      objectId: oid,
      ra: uRa,
      dec: uDec,
      radius: uRadius,
      survey: uSurvey,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [broker]);

  const coneDisabled = objectId.trim() !== "";
  const coneReason =
    "Disabled while an Object ID is set: the search is done by object, not by position.";
  const coneFields = [
    {
      label: "RA (deg)",
      placeholder: "deg or HH:MM:SS",
      value: ra,
      set: setRa,
    },
    {
      label: "Dec (deg)",
      placeholder: "deg or ±DD:MM:SS",
      value: dec,
      set: setDec,
    },
    { label: "Radius (arcsec)", value: radius, set: setRadius },
  ];

  const onPreview = (params: Record<string, unknown>) => {
    setMode("preview");
    setPage(1);
    setFilters([]);
    triggerFilter({ brokerId, params });
  };

  const rows = asArray(data);
  const flatRows = useMemo(() => (rows ?? []).map((r) => flatten(r)), [rows]);
  const fields = useMemo(() => fieldsOf(flatRows), [flatRows]);
  const kept = rows?.filter((_r, i) =>
    matchesFilters(flatRows[i] ?? {}, filters),
  );

  const byObject = new Map<string, NormalizedAlert[]>();
  // candid is optional: Lasair cone rows have none.
  (kept ?? []).map(normalizeAlert).forEach((a) => {
    if (a.objectId)
      byObject.set(a.objectId, [...(byObject.get(a.objectId) ?? []), a]);
  });
  const objectGroups = [...byObject].map(([oid, alerts]) => ({
    objectId: oid,
    alerts,
  }));
  const pageCount = Math.ceil(objectGroups.length / PAGE_SIZE);
  const current = Math.min(page, pageCount);
  const start = (current - 1) * PAGE_SIZE;
  const pageGroups = objectGroups.slice(start, start + PAGE_SIZE);

  if (brokersLoading) return <Spinner />;

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <IconButton component={Link} to="/brokers" aria-label="back to brokers">
          <ArrowBackIcon />
        </IconButton>
        <Box>
          <Typography variant="h5">{broker?.name ?? "Broker"}</Typography>
          {broker && (
            <Typography variant="body2" color="text.secondary">
              {broker.broker_classname}
            </Typography>
          )}
        </Box>
        {hasFilters && (
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => setNewFilterOpen(true)}
            sx={{ ml: "auto" }}
          >
            Filter
          </Button>
        )}
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
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: 2,
                mb: 2,
              }}
            >
              <TextField
                size="small"
                label="Object ID"
                value={objectId}
                onChange={(e) => setObjectId(e.target.value)}
              />
              {surveys.length > 1 && (
                <Tooltip
                  placement="top"
                  title="Selected automatically from the object ID format, override it if needed"
                >
                  <TextField
                    select
                    size="small"
                    label="Survey"
                    value={searchSurvey}
                    onChange={(e) => setSurvey(e.target.value)}
                    sx={{ minWidth: 120 }}
                  >
                    {surveys.map((s) => (
                      <MenuItem key={s} value={s}>
                        {s}
                      </MenuItem>
                    ))}
                  </TextField>
                </Tooltip>
              )}
              {coneFields.map(({ label, placeholder, value, set }) => (
                <Tooltip key={label} title={coneDisabled ? coneReason : ""}>
                  <span>
                    <TextField
                      size="small"
                      label={label}
                      placeholder={placeholder}
                      value={value}
                      disabled={coneDisabled}
                      onChange={(e) => set(e.target.value)}
                    />
                  </span>
                </Tooltip>
              ))}
              <Button
                variant="contained"
                onClick={() =>
                  search({
                    objectId,
                    survey: searchSurvey,
                    ...(!coneDisabled && { ra, dec, radius }),
                  })
                }
                disabled={isFetching}
              >
                {isFetching ? "Searching…" : "Search"}
              </Button>
            </Box>
          )}

          {activeTab === 1 &&
            (broker.broker_classname === "LASAIRBROKER" && canPreview ? (
              <LasairFilterBuilder
                brokerId={brokerId}
                survey={searchSurvey}
                onPreview={onPreview}
              />
            ) : broker.broker_classname === "BOOMBROKER" ? (
              <FilterCatalog brokerId={brokerId} />
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {`${broker.name} — filter editor coming soon.`}
              </Typography>
            ))}

          <NewBrokerFilterDialog
            open={newFilterOpen}
            onClose={() => setNewFilterOpen(false)}
            brokerId={brokerId}
          />
          {activeTab === 2 && (
            <BrokerCredentialsForm
              brokerId={brokerId}
              brokerClassname={broker.broker_classname}
            />
          )}

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
                    <Typography variant="subtitle2" gutterBottom>
                      {`${objectGroups.length} object${
                        objectGroups.length === 1 ? "" : "s"
                      } — showing ${start + 1}–${start + pageGroups.length}`}
                    </Typography>
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns:
                          pageGroups.length === 1
                            ? "1fr"
                            : "repeat(auto-fill, minmax(520px, 1fr))",
                        gap: 2,
                      }}
                    >
                      {pageGroups.map((g) => (
                        <BrokerAlertCard
                          key={g.objectId}
                          brokerId={brokerId}
                          brokerClassname={broker.broker_classname}
                          objectId={g.objectId}
                          survey={queriedSurvey || searchSurvey}
                          alerts={g.alerts}
                          expanded={pageGroups.length === 1}
                        />
                      ))}
                    </Box>
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
                ) : (
                  <Paper
                    variant="outlined"
                    sx={{ p: 2, maxHeight: "50vh", overflow: "auto" }}
                  >
                    {kept && (
                      <Typography variant="subtitle2" gutterBottom>
                        {`${kept.length} result${kept.length === 1 ? "" : "s"}`}
                      </Typography>
                    )}
                    <Box
                      component="pre"
                      sx={{
                        m: 0,
                        fontFamily: "monospace",
                        fontSize: "0.75rem",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                      }}
                    >
                      {JSON.stringify(kept ?? data, null, 2)}
                    </Box>
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
