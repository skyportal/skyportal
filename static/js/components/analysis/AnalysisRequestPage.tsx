import { useState } from "react";
import { Link } from "react-router-dom";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import SegmentedControl from "../SegmentedControl";
import DefaultAnalysisList from "./DefaultAnalysisList";
import { useGetAnalysesQuery } from "../../ducks/source";
import { useGetAnalysisServicesQuery } from "../../ducks/analysis_services";
import { useGetProfileQuery } from "../../ducks/profile";

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
  return "error";
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
    sx={{ px: 2, py: 1, textAlign: "center", minWidth: "6.5rem" }}
  >
    <Typography variant="h5" sx={{ color }}>
      {value}
    </Typography>
    <Typography variant="caption">{label}</Typography>
  </Paper>
);

const HEALTH_WINDOWS = [
  { key: "1h", label: "1 hour", ms: HOUR_MS },
  { key: "24h", label: "24 hours", ms: DAY_MS },
  { key: "1w", label: "1 week", ms: 7 * DAY_MS },
  { key: "30d", label: "30 days", ms: 30 * DAY_MS },
  { key: "all", label: "Lifetime", ms: Infinity },
];

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

const AnalysisHealth = ({ analyses }: { analyses: any[] }) => {
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
    <Paper sx={{ p: 2 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 1,
        }}
      >
        <Typography variant="h6">Analysis health</Typography>
        <SegmentedControl
          value={windowKey}
          onChange={setWindowKey}
          options={HEALTH_WINDOWS.map((w) => ({
            value: w.key,
            label: w.label,
          }))}
        />
      </Box>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 2,
          alignItems: "center",
          mt: 1,
        }}
      >
        <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
          <HealthTile label="Total" value={total} />
          {nonZero.map((s) => (
            <HealthTile
              key={s.label}
              label={s.label}
              value={s.value}
              color={s.color}
            />
          ))}
        </Box>
        <Box sx={{ flex: "1 1 260px", minWidth: 240 }}>
          {total === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No analyses in this window
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
        </Box>
      </Box>
    </Paper>
  );
};

const AnalysisRequestsToolbar = () => (
  <DataGridToolbar title="Analysis Requests" />
);

const AnalysisRequestList = () => {
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
    <>
      <AnalysisHealth analyses={(analyses as any[]) || []} />
      <StyledDataGrid
        autoHeight
        rows={(analyses as any[]) || []}
        columns={columns}
        showToolbar
        slots={{ toolbar: AnalysisRequestsToolbar }}
        initialState={{
          sorting: { sortModel: [{ field: "created_at", sort: "desc" }] },
        }}
      />
    </>
  );
};

const DefaultAnalysesOverview = () => {
  const { data: analysisServices } = useGetAnalysisServicesQuery();
  const { data: currentUser } = useGetProfileQuery();
  const deletePermission =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage Analysis Services") ||
    false;

  return (
    <>
      {((analysisServices as any[]) || []).map((service: any) => (
        <Paper key={service.id} sx={{ p: 1 }}>
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
    </>
  );
};

const AnalysisRequestPage = () => {
  const [tabIndex, setTabIndex] = useState(0);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Tabs
        value={tabIndex}
        onChange={(_e, v) => setTabIndex(v)}
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Analysis Requests" />
        <Tab label="Default Analyses" />
      </Tabs>
      {tabIndex === 0 ? <AnalysisRequestList /> : <DefaultAnalysesOverview />}
    </Box>
  );
};

export default AnalysisRequestPage;
