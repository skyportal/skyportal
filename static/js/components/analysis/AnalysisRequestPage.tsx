import { useState } from "react";
import { Link } from "react-router-dom";
import { makeStyles } from "tss-react/mui";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import StyledDataGrid from "../StyledDataGrid";
import DefaultAnalysisList from "./DefaultAnalysisList";
import { useGetAnalysesQuery } from "../../ducks/source";
import { useGetAnalysisServicesQuery } from "../../ducks/analysis_services";
import { useGetProfileQuery } from "../../ducks/profile";

const useStyles = makeStyles()((theme) => ({
  root: { width: "100%" },
  serviceBlock: { padding: theme.spacing(1), marginBottom: theme.spacing(1.5) },
}));

const Plot: any = createPlotlyComponent(Plotly);

const HOUR_MS = 3600 * 1000;
const DAY_MS = 24 * HOUR_MS;
const COMPLETED_COLOR = "#2e7d32";
const ACTIVE_COLOR = "#ed6c02";
const FAILED_COLOR = "#d32f2f";

const ACTIVE_STATUSES = ["queued", "pending", "running"];

const statusColor = (status: string) => {
  if (status === "completed") return "success";
  if (ACTIVE_STATUSES.includes(status)) return "warning";
  return "error"; // failure, cancelled, timed_out
};

// SkyPortal timestamps are naive UTC; append Z so they parse as UTC, not local.
const parseUTC = (ts?: string): number => {
  if (!ts) return NaN;
  const s = /[zZ]|[+-]\d\d:?\d\d$/.test(ts) ? ts : `${ts}Z`;
  return new Date(s).getTime();
};

const HealthTile = ({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) => (
  <Paper
    variant="outlined"
    style={{ padding: "0.5rem 1rem", textAlign: "center", minWidth: "6.5rem" }}
  >
    <Typography variant="h5" style={{ color }}>
      {value}
    </Typography>
    <Typography variant="caption">{label}</Typography>
  </Paper>
);

// Selectable time windows for the health summary (by last_activity).
const HEALTH_WINDOWS = [
  { key: "1h", label: "1 hour", ms: HOUR_MS },
  { key: "24h", label: "24 hours", ms: DAY_MS },
  { key: "1w", label: "1 week", ms: 7 * DAY_MS },
  { key: "30d", label: "30 days", ms: 30 * DAY_MS },
  { key: "all", label: "Lifetime", ms: Infinity },
];

// Per-status buckets for the tiles/donut (analysis status is an enum).
const STATUS_BUCKETS: { status: string; label: string; color: string }[] = [
  { status: "completed", label: "Completed", color: COMPLETED_COLOR },
  { status: "queued", label: "Queued", color: "#0288d1" },
  { status: "pending", label: "Pending", color: ACTIVE_COLOR },
  { status: "running", label: "Running", color: "#7e57c2" },
  { status: "failure", label: "Failed", color: FAILED_COLOR },
  { status: "cancelled", label: "Cancelled", color: "#757575" },
  { status: "timed_out", label: "Timed out", color: "#9e6f00" },
];
const OTHER_COLOR = "#bdbdbd";

// Health summary for analysis requests: per-status split within a selectable
// time window. Computed client-side from the fetched analyses (status +
// last_activity timestamp); the numbers and donut update on selection.
const AnalysisHealth = ({ analyses }: { analyses: any[] }) => {
  // captured at mount (recomputed on refetch/revisit) — keeps render pure
  const [now] = useState(() => Date.now());
  const [windowKey, setWindowKey] = useState("24h");
  const win =
    HEALTH_WINDOWS.find((w) => w.key === windowKey) ??
    HEALTH_WINDOWS[HEALTH_WINDOWS.length - 1]!;

  const counts: Record<string, number> = {};
  let total = 0;
  let other = 0;
  analyses.forEach((a: any) => {
    const t = parseUTC(a.last_activity || a.created_at);
    if (win.ms !== Infinity && now - t > win.ms) return;
    total += 1;
    const bucket = STATUS_BUCKETS.find((b) => b.status === a.status);
    if (bucket) counts[bucket.status] = (counts[bucket.status] || 0) + 1;
    else other += 1;
  });

  const slices = STATUS_BUCKETS.map((b) => ({
    label: b.label,
    value: counts[b.status] || 0,
    color: b.color,
  }));
  if (other > 0) {
    slices.push({ label: "Other", value: other, color: OTHER_COLOR });
  }
  const nonZero = slices.filter((s) => s.value > 0);

  return (
    <Paper style={{ padding: "1rem", marginBottom: "1rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <Typography variant="h6">Analysis health</Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={windowKey}
          onChange={(_e, v) => v && setWindowKey(v)}
        >
          {HEALTH_WINDOWS.map((w) => (
            <ToggleButton key={w.key} value={w.key}>
              {w.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
          marginTop: "0.5rem",
        }}
      >
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <HealthTile label="Total" value={total} />
          {nonZero.map((s) => (
            <HealthTile
              key={s.label}
              label={s.label}
              value={s.value}
              color={s.color}
            />
          ))}
        </div>
        <div style={{ flex: "1 1 260px", minWidth: 240 }}>
          {total === 0 ? (
            <Typography variant="body2" style={{ fontStyle: "italic" }}>
              No analyses in this window.
            </Typography>
          ) : (
            <Plot
              data={[
                {
                  type: "pie",
                  hole: 0.4,
                  labels: nonZero.map((s) => s.label),
                  values: nonZero.map((s) => s.value),
                  marker: { colors: nonZero.map((s) => s.color) },
                  textinfo: "label+value",
                  sort: false,
                },
              ]}
              layout={{
                height: 230,
                margin: { t: 10, b: 10, l: 10, r: 10 },
                showlegend: false,
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </div>
      </div>
    </Paper>
  );
};

// Tab 1: global status view of all accessible analysis requests (ObjAnalysis),
// the analysis-side analog of the Follow-up Requests page.
const AnalysisRequestList = () => {
  const { classes } = useStyles();
  const { data: analyses } = useGetAnalysesQuery({
    analysis_resource_type: "obj",
    params: {},
  });

  const renderObj = (params: any) => (
    <Link to={`/source/${params.row.obj_id}`} role="link">
      {params.row.obj_id}
    </Link>
  );

  const renderStatus = (params: any) => (
    <Chip
      size="small"
      variant="outlined"
      label={params.row.status}
      color={statusColor(params.row.status) as any}
    />
  );

  const renderLink = (params: any) => (
    <Link
      to={`/source/${params.row.obj_id}/analysis/${params.row.id}`}
      role="link"
    >
      view
    </Link>
  );

  const columns: any[] = [
    {
      field: "obj_id",
      headerName: "Object",
      flex: 1,
      minWidth: 140,
      renderCell: renderObj,
    },
    {
      field: "analysis_service_name",
      headerName: "Service",
      flex: 1,
      minWidth: 160,
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 120,
      renderCell: renderStatus,
    },
    {
      field: "status_message",
      headerName: "Message",
      flex: 1.5,
      minWidth: 200,
      sortable: false,
    },
    {
      field: "created_at",
      headerName: "Created",
      flex: 1,
      minWidth: 170,
    },
    {
      field: "link",
      headerName: " ",
      minWidth: 70,
      filterable: false,
      sortable: false,
      renderCell: renderLink,
    },
  ];

  return (
    <div className={classes.root}>
      <AnalysisHealth analyses={(analyses as any[]) || []} />
      <Paper>
        <Typography variant="h6">Analysis Requests</Typography>
        <StyledDataGrid
          autoHeight
          rows={(analyses as any[]) || []}
          columns={columns}
          getRowId={(row: any) => row.id}
          initialState={{
            pagination: { paginationModel: { pageSize: 25 } },
            sorting: { sortModel: [{ field: "created_at", sort: "desc" }] },
          }}
          pageSizeOptions={[10, 25, 50, 100]}
        />
      </Paper>
    </div>
  );
};

// Tab 2: per-service overview of configured default (auto-triggered) analyses.
// Defaults are nested under each service, so we render one read-only list per
// service (configuration lives on the Analysis Services page).
const DefaultAnalysesOverview = () => {
  const { classes } = useStyles();
  const { data: analysisServices } = useGetAnalysisServicesQuery();
  const { data: currentUser } = useGetProfileQuery();
  const deletePermission =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage Analysis Services") ||
    false;

  return (
    <div className={classes.root}>
      {((analysisServices as any[]) || []).map((service: any) => (
        <Paper key={service.id} className={classes.serviceBlock}>
          <Typography variant="subtitle1">
            {service.display_name || service.name}
          </Typography>
          <DefaultAnalysisList
            analysisService={service}
            deletePermission={deletePermission}
            showForm={false}
          />
        </Paper>
      ))}
    </div>
  );
};

const AnalysisRequestPage = () => {
  const [tabIndex, setTabIndex] = useState(0);

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <Tabs value={tabIndex} onChange={(_e, v) => setTabIndex(v)} centered>
          <Tab label="Analysis Requests" />
          <Tab label="Default Analyses" />
        </Tabs>
        {tabIndex === 0 ? <AnalysisRequestList /> : <DefaultAnalysesOverview />}
      </Grid>
    </Grid>
  );
};

export default AnalysisRequestPage;
