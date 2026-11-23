import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import useTabParam from "../../hooks/useTabParam";

import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Pagination from "@mui/material/Pagination";
import Paper from "@mui/material/Paper";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import {
  useGetBrokersQuery,
  useLazyGetBrokerAlertsQuery,
} from "../../ducks/brokers";
import BrokerAlertCard, { AlertOption, toAlertOption } from "./BrokerAlertCard";
import BrokerAlertFilters from "./BrokerAlertFilters";
import BrokerAlertSearch, {
  AlertSearch,
  DEFAULT_SEARCH,
  SearchMode,
  searchSurvey,
} from "./BrokerAlertSearch";
import BrokerCredentialsForm from "./BrokerCredentialsForm";
import BrokerSchema from "./BrokerSchema";
import FilterCatalog from "./FilterCatalog";
import { AlertFilter, fieldsOf, flatten, matchesFilters } from "./alertFields";
import NewFilterDialog from "../filter/NewFilterDialog";
import Spinner from "../Spinner";
import { dec_to_deg, ra_to_deg } from "../../units";

const PAGE_SIZE = 12;

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

  const [form, setForm] = useState<AlertSearch>(DEFAULT_SEARCH);
  const [queriedDesignation, setQueriedDesignation] = useState("");
  const [queriedSurvey, setQueriedSurvey] = useState("");
  const [page, setPage] = useState(1);
  const [tab, setTab] = useTabParam([
    "alerts",
    "filters",
    "schema",
    "credentials",
  ]);
  const [newFilterOpen, setNewFilterOpen] = useState(false);
  const [filters, setFilters] = useState<AlertFilter[]>([]);

  const [triggerAlerts, { data, error, isFetching }] =
    useLazyGetBrokerAlertsQuery();

  const broker = brokers?.find((b) => b.id === brokerId);
  const surveys = broker?.surveys ?? [];
  const designationSearch =
    broker?.broker_classname === "BOOMBROKER" && surveys.includes("ZTF");
  const hasFilters = Boolean(broker && broker.filter_kind !== "none");
  const tabs = [
    {
      label: "Alerts",
      disabledReason: broker?.capabilities?.["query_alerts"]
        ? ""
        : `${broker?.name} does not support alerts query.`,
    },
    {
      label: "Filters",
      disabledReason: hasFilters
        ? ""
        : `${broker?.name} does not support filters.`,
    },
    {
      label: "Schema",
      disabledReason: broker?.capabilities?.["filter_modules"]
        ? ""
        : `${broker?.name} does not publish an alert schema.`,
    },
    { label: "Credentials", disabledReason: "" },
  ];
  const activeTab = tabs[tab]?.disabledReason
    ? tabs.findIndex((t) => !t.disabledReason)
    : tab;

  const search = (query: AlertSearch) => {
    const survey = searchSurvey(query, surveys);
    const designation =
      query.mode === "designation" ? query.designation.trim() : "";
    const cone = query.mode === "position";
    setPage(1);
    setFilters([]);
    setQueriedSurvey(survey);
    setQueriedDesignation(designation);
    triggerAlerts({
      brokerId,
      params: {
        objectId: query.mode === "object" ? query.objectId.trim() : undefined,
        designation: designation || undefined,
        ra: cone ? ra_to_deg(query.ra.trim()) : undefined,
        dec: cone ? dec_to_deg(query.dec.trim()) : undefined,
        radius: cone ? query.radius.trim() : undefined,
        radius_units: cone ? "arcsec" : undefined,
        survey,
      },
    });
  };

  const [searchParams] = useSearchParams();
  const autoSearched = useRef(false);
  useEffect(() => {
    if (autoSearched.current || !broker) return;
    autoSearched.current = true;
    const objectId = searchParams.get("objectId") || "";
    const designation = searchParams.get("designation") || "";
    const ra = searchParams.get("ra") || "";
    let mode: SearchMode | undefined;
    if (objectId) mode = "object";
    else if (designation) mode = "designation";
    else if (ra) mode = "position";
    if (!mode) return;

    const query: AlertSearch = {
      mode,
      objectId,
      designation,
      ra,
      dec: searchParams.get("dec") || "",
      radius: searchParams.get("radius") || DEFAULT_SEARCH.radius,
      survey: searchParams.get("survey") || "",
    };
    setForm(query);
    search(query);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [broker]);

  const rows: unknown[] | null = Array.isArray(data)
    ? data
    : Array.isArray((data as any)?.objects)
      ? (data as any).objects
      : null;
  const flatRows = useMemo(() => (rows ?? []).map((r) => flatten(r)), [rows]);
  const fields = useMemo(() => fieldsOf(flatRows), [flatRows]);
  const kept = useMemo(
    () => rows?.filter((_r, i) => matchesFilters(flatRows[i] ?? {}, filters)),
    [rows, flatRows, filters],
  );

  const byObject = useMemo(() => {
    const groups = new Map<string, AlertOption[]>();
    (kept ?? []).forEach((a: any) => {
      const oid =
        queriedDesignation ||
        (a?.objectId ??
          a?.diaObjectId ??
          a?.object_id ??
          a?.object ??
          a?.candidate?.objectId);
      if (!oid) return;
      groups.set(oid, [...(groups.get(oid) ?? []), toAlertOption(a)]);
    });
    return groups;
  }, [kept, queriedDesignation]);
  const pageCount = Math.ceil(byObject.size / PAGE_SIZE);
  const current = Math.min(page, pageCount);
  const start = (current - 1) * PAGE_SIZE;
  const pageGroups = [...byObject].slice(start, start + PAGE_SIZE);

  if (brokersLoading) return <Spinner />;

  return (
    <Box
      sx={{
        height: "calc(100vh - 5.25rem)",
        display: "flex",
        flexDirection: "column",
        overflow: "auto",
      }}
    >
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
            value={activeTab}
            onChange={(_event, value) => setTab(value)}
          >
            {tabs.map((t) => (
              <TooltipTab
                key={t.label}
                label={t.label}
                disabled={Boolean(t.disabledReason)}
                tooltip={t.disabledReason}
              />
            ))}
          </Tabs>

          {activeTab === 0 && (
            <BrokerAlertSearch
              value={form}
              onChange={setForm}
              onSearch={() => search(form)}
              surveys={surveys}
              designationSearch={designationSearch}
              searching={isFetching}
            />
          )}

          {activeTab === 1 && <FilterCatalog brokerId={brokerId} />}
          {activeTab === 2 && (
            <BrokerSchema brokerId={brokerId} surveys={surveys} />
          )}

          <NewFilterDialog
            open={newFilterOpen}
            onClose={() => setNewFilterOpen(false)}
            brokerId={brokerId}
          />
          {activeTab === 3 && (
            <BrokerCredentialsForm
              brokerId={brokerId}
              brokerClassname={broker.broker_classname}
            />
          )}

          {activeTab === 0 && (
            <>
              {error && !isFetching && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {(error as any)?.data?.message || "Failed to query broker."}
                </Alert>
              )}

              {rows && rows.length > 0 && (
                <BrokerAlertFilters
                  fields={fields}
                  filters={filters}
                  onChange={setFilters}
                />
              )}

              {data !== undefined &&
                !error &&
                (byObject.size > 0 ? (
                  <>
                    <Typography variant="subtitle2" gutterBottom>
                      {`${byObject.size} object${
                        byObject.size === 1 ? "" : "s"
                      }, showing ${start + 1}–${start + pageGroups.length}`}
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
                      {pageGroups.map(([oid, alerts]) => (
                        <BrokerAlertCard
                          key={oid}
                          brokerId={brokerId}
                          brokerClassname={broker.broker_classname}
                          objectId={oid}
                          survey={queriedSurvey}
                          alerts={alerts}
                          expanded={pageGroups.length === 1}
                          movingObject={Boolean(queriedDesignation)}
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
                ) : kept?.length === 0 ? (
                  <Typography
                    color="text.secondary"
                    sx={{ py: 4, textAlign: "center" }}
                  >
                    No alerts found.
                  </Typography>
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
