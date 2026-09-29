import Box from "@mui/material/Box";
import MuiPaper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import { useGetFollowupRequestsQuery } from "../../ducks/followup_requests";
import Paper from "../Paper";

const Plot: any = createPlotlyComponent(Plotly);

const HOUR_MS = 3600 * 1000;
const DAY_MS = 24 * HOUR_MS;

export const WINDOWS = [
  { key: "1h", label: "1 hour", ms: HOUR_MS },
  { key: "24h", label: "24 hours", ms: DAY_MS },
  { key: "1w", label: "1 week", ms: 7 * DAY_MS },
  { key: "30d", label: "30 days", ms: 30 * DAY_MS },
  { key: "all", label: "Lifetime", ms: Infinity },
];

const COLORS: Record<string, string> = {
  Completed: "#2e7d32",
  Submitted: "#0288d1",
  Pending: "#ed6c02",
  Failed: "#d32f2f",
  Deleted: "#757575",
  Other: "#bdbdbd",
};

const Tile = ({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string | undefined;
}) => (
  <MuiPaper
    variant="outlined"
    sx={{ px: 2, py: 1, textAlign: "center", minWidth: "6rem" }}
  >
    <Typography variant="h5" sx={{ color }}>
      {value}
    </Typography>
    <Typography variant="caption">{label}</Typography>
  </MuiPaper>
);

const useRequestCount = (params: Record<string, any>) =>
  useGetFollowupRequestsQuery(params).data?.totalMatches ?? 0;

interface FollowupHealthProps {
  windowKey: string;
  onWindowChange: (windowKey: string) => void;
  startDate: string | undefined;
}

const FollowupHealth = ({
  windowKey,
  onWindowChange,
  startDate,
}: FollowupHealthProps) => {
  const base = { numPerPage: 1, pageNumber: 1, startDate };

  const total = useRequestCount(base);
  const completed = useRequestCount({ ...base, status: "complete" });
  const submitted = useRequestCount({ ...base, status: "submitted" });
  const pending = useRequestCount({ ...base, status: "pending" });
  const failed = useRequestCount({ ...base, status: "failed" });
  const deleted = useRequestCount({ ...base, status: "deleted" });
  const slices = [
    { label: "Completed", value: completed },
    { label: "Submitted", value: submitted },
    { label: "Pending", value: pending },
    { label: "Failed", value: failed },
    { label: "Deleted", value: deleted },
    {
      label: "Other",
      value: Math.max(
        0,
        total - completed - submitted - pending - failed - deleted,
      ),
    },
  ];
  const nonZero = slices.filter((s) => s.value > 0);

  return (
    <Paper>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 1,
        }}
      >
        <Typography variant="h6">Follow-up request health</Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={windowKey}
          onChange={(_e, v) => v && onWindowChange(v)}
        >
          {WINDOWS.map((w) => (
            <ToggleButton key={w.key} value={w.key}>
              {w.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
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
          <Tile label="Total" value={total} />
          {nonZero.map((s) => (
            <Tile
              key={s.label}
              label={s.label}
              value={s.value}
              color={COLORS[s.label]}
            />
          ))}
        </Box>
        <Box sx={{ flex: "1 1 260px", minWidth: 240 }}>
          {total === 0 ? (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              No requests in this window.
            </Typography>
          ) : (
            <Plot
              data={[
                {
                  type: "pie",
                  hole: 0.4,
                  labels: nonZero.map((s) => s.label),
                  values: nonZero.map((s) => s.value),
                  marker: { colors: nonZero.map((s) => COLORS[s.label]) },
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

export default FollowupHealth;
