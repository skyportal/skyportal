import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { makeStyles } from "tss-react/mui";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import Tooltip from "@mui/material/Tooltip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import StyledDataGrid from "../StyledDataGrid";
import { useGetObservationPlanRequestsQuery } from "../../ducks/observationPlans";

const useStyles = makeStyles()(() => ({
  root: { width: "100%" },
}));

const Plot: any = createPlotlyComponent(Plotly);

const HOUR_MS = 3600 * 1000;
const DAY_MS = 24 * HOUR_MS;
const COMPLETED_COLOR = "#2e7d32";
const ACTIVE_COLOR = "#ed6c02";
const FAILED_COLOR = "#d32f2f";

const DONE_STATUSES = ["complete", "submitted to telescope queue"];
const ACTIVE_STATUSES = ["pending submission", "running"];

// Statuses are free text: a failure carries the exception that caused it, so
// anything not recognised is treated as a failure rather than assumed benign.
const statusKind = (status?: string) => {
  if (!status) return "failed";
  if (DONE_STATUSES.includes(status)) return "done";
  if (ACTIVE_STATUSES.includes(status)) return "active";
  return "failed";
};

const statusColor = (status?: string) => {
  const kind = statusKind(status);
  if (kind === "done") return "success";
  if (kind === "active") return "warning";
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
    style={{ padding: "0.5rem 1rem", textAlign: "center", minWidth: "6.5rem" }}
  >
    <Typography variant="h6" style={color ? { color } : undefined}>
      {value}
    </Typography>
    <Typography variant="caption">{label}</Typography>
  </Paper>
);

const ObservationPlanHealth = ({ requests }: { requests: any[] }) => {
  // Captured once, so the window is measured from page load rather than
  // shifting under every render.
  const [now] = useState(() => Date.now());
  const [windowMs, setWindowMs] = useState<number>(7 * DAY_MS);

  const { tiles, total, slowest } = useMemo(() => {
    const cutoff = now - windowMs;
    const recent = requests.filter((r) => parseUTC(r.created_at) >= cutoff);
    const counts = { done: 0, active: 0, failed: 0 };
    let slowestSeconds = 0;
    recent.forEach((r) => {
      counts[statusKind(r.status) as keyof typeof counts] += 1;
      const secs = (parseUTC(r.modified) - parseUTC(r.created_at)) / 1000;
      if (Number.isFinite(secs) && secs > slowestSeconds) slowestSeconds = secs;
    });
    return {
      tiles: [
        { label: "Complete", value: counts.done, color: COMPLETED_COLOR },
        { label: "In progress", value: counts.active, color: ACTIVE_COLOR },
        { label: "Failed", value: counts.failed, color: FAILED_COLOR },
      ],
      total: recent.length,
      slowest: slowestSeconds,
    };
  }, [requests, windowMs, now]);

  const nonZero = tiles.filter((t) => t.value > 0);

  return (
    <Paper style={{ padding: "1rem", marginBottom: "1rem" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <Typography variant="h6">Queue health</Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={windowMs}
          onChange={(_e, v) => v && setWindowMs(v)}
        >
          <ToggleButton value={DAY_MS}>24h</ToggleButton>
          <ToggleButton value={7 * DAY_MS}>7d</ToggleButton>
          <ToggleButton value={30 * DAY_MS}>30d</ToggleButton>
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
          <HealthTile label="Slowest (min)" value={Math.round(slowest / 60)} />
        </div>
        <div style={{ flex: "1 1 260px", minWidth: 240 }}>
          {total === 0 ? (
            <Typography variant="body2" style={{ fontStyle: "italic" }}>
              No observation plan requests in this window.
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

const ObservationPlanRequestPage = () => {
  const { classes } = useStyles();
  const { data } = useGetObservationPlanRequestsQuery({ numPerPage: 500 });
  const requests = useMemo(() => (data?.requests as any[]) || [], [data]);

  const rows = useMemo(
    () =>
      requests.map((r) => ({
        ...r,
        scheduler: r.payload?.scheduler || "gwemopt",
        localization_name: r.payload?.localization_name || "",
        queue_name: r.payload?.queue_name || "",
        // What the request actually cost, which is what makes a slow queue visible.
        duration_s: Math.round(
          (parseUTC(r.modified) - parseUTC(r.created_at)) / 1000,
        ),
      })),
    [requests],
  );

  const renderEvent = (params: any) =>
    params.row.dateobs ? (
      <Link to={`/gcn_events/${params.row.dateobs}`} role="link">
        {params.row.dateobs}
      </Link>
    ) : (
      ""
    );

  const renderStatus = (params: any) => (
    <Tooltip title={params.row.status || ""}>
      <Chip
        size="small"
        variant="outlined"
        label={(params.row.status || "").slice(0, 34)}
        color={statusColor(params.row.status) as any}
      />
    </Tooltip>
  );

  const columns: any[] = [
    { field: "id", headerName: "ID", width: 80 },
    {
      field: "dateobs",
      headerName: "Event",
      flex: 1,
      minWidth: 170,
      renderCell: renderEvent,
    },
    { field: "instrument_name", headerName: "Instrument", minWidth: 110 },
    { field: "scheduler", headerName: "Scheduler", minWidth: 110 },
    {
      field: "localization_name",
      headerName: "Skymap",
      flex: 1,
      minWidth: 200,
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 180,
      renderCell: renderStatus,
    },
    { field: "duration_s", headerName: "Duration (s)", minWidth: 110 },
    { field: "created_at", headerName: "Created", flex: 1, minWidth: 170 },
  ];

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <div className={classes.root}>
          <ObservationPlanHealth requests={requests} />
          <Paper>
            <Typography variant="h6">Observation Plan Requests</Typography>
            <StyledDataGrid
              autoHeight
              rows={rows}
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
      </Grid>
    </Grid>
  );
};

export default ObservationPlanRequestPage;
