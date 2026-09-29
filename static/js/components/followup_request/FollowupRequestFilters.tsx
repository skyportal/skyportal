import { useState } from "react";
import dayjs from "dayjs";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";

import { useGetFollowupRequestsQuery } from "../../ducks/followup_requests";
import { useGetUsersQuery } from "../../ducks/users";
import Paper from "../Paper";
import { STATUS_FILTERS } from "./status";
import useTriggeredAllocations from "./useTriggeredAllocations";

const HOUR_MS = 3600 * 1000;
const DAY_MS = 24 * HOUR_MS;

export const WINDOWS = [
  { key: "1h", label: "1 hour", ms: HOUR_MS },
  { key: "24h", label: "24 hours", ms: DAY_MS },
  { key: "1w", label: "1 week", ms: 7 * DAY_MS },
  { key: "30d", label: "30 days", ms: 30 * DAY_MS },
  { key: "all", label: "All", ms: Infinity },
  { key: "custom", label: "Custom", ms: Infinity },
];

export interface FollowupRequestFiltersState {
  windowKey: string;
  startDate?: string | undefined;
  endDate?: string | undefined;
  status?: string | undefined;
  sourceID?: string | undefined;
  instrumentID?: number | undefined;
  allocationID?: number | undefined;
  requesters?: number[] | undefined;
  priorityThreshold?: number | undefined;
  observationStartDate?: string | undefined;
  observationEndDate?: string | undefined;
}

const DateTimeField = ({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string | undefined;
  onChange: (value: string | undefined) => void;
}) => (
  <TextField
    size="small"
    type="datetime-local"
    label={label}
    value={value ? dayjs(value).format("YYYY-MM-DDTHH:mm") : ""}
    onChange={(e) =>
      onChange(e.target.value ? dayjs(e.target.value).toISOString() : undefined)
    }
    slotProps={{ inputLabel: { shrink: true } }}
    sx={{ minWidth: 200 }}
  />
);

const useRequestCount = (params: Record<string, any>) =>
  useGetFollowupRequestsQuery(params).data?.totalMatches ?? 0;

interface FollowupRequestFiltersProps {
  filters: FollowupRequestFiltersState;
  onChange: (changes: Partial<FollowupRequestFiltersState>) => void;
  countParams: Record<string, any>;
}

const FollowupRequestFilters = ({
  filters,
  onChange,
  countParams,
}: FollowupRequestFiltersProps) => {
  const { allocations, instruments } = useTriggeredAllocations();
  const users = useGetUsersQuery().data?.users ?? [];
  const [customAnchor, setCustomAnchor] = useState<HTMLElement | null>(null);

  const base = { ...countParams, numPerPage: 1, pageNumber: 1 };
  const total = useRequestCount(base);
  const counts = [
    useRequestCount({ ...base, status: STATUS_FILTERS[0]!.status }),
    useRequestCount({ ...base, status: STATUS_FILTERS[1]!.status }),
    useRequestCount({ ...base, status: STATUS_FILTERS[2]!.status }),
    useRequestCount({ ...base, status: STATUS_FILTERS[3]!.status }),
    useRequestCount({ ...base, status: STATUS_FILTERS[4]!.status }),
  ];
  const other = Math.max(0, total - counts.reduce((a, b) => a + b, 0));

  const instrumentAllocations = allocations.filter(
    ({ instrument_id }) =>
      !filters.instrumentID || instrument_id === filters.instrumentID,
  );
  const allocationLabel = (allocation: any) =>
    `${allocation.pi} (${
      instruments.find(({ id }: any) => id === allocation.instrument_id)?.name
    })`;

  return (
    <Paper sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
        }}
      >
        <ToggleButtonGroup
          size="small"
          exclusive
          value={filters.windowKey}
          onChange={(_e, windowKey) => windowKey && onChange({ windowKey })}
        >
          {WINDOWS.map(({ key, label }) => (
            <ToggleButton
              key={key}
              value={key}
              onClick={(e) =>
                key === "custom" && setCustomAnchor(e.currentTarget)
              }
            >
              {label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <Popover
          open={!!customAnchor}
          anchorEl={customAnchor}
          onClose={() => setCustomAnchor(null)}
          anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        >
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, p: 2 }}>
            <Typography variant="subtitle2">Created</Typography>
            <DateTimeField
              label="From"
              value={filters.startDate}
              onChange={(startDate) => onChange({ startDate })}
            />
            <DateTimeField
              label="To"
              value={filters.endDate}
              onChange={(endDate) => onChange({ endDate })}
            />
          </Box>
        </Popover>
        <ToggleButtonGroup
          exclusive
          value={filters.status ?? ""}
          onChange={(_e, status) =>
            status !== null && onChange({ status: status || undefined })
          }
          sx={{ flexWrap: "wrap" }}
        >
          {[
            { label: "All", status: "", color: "text.primary", count: total },
            ...STATUS_FILTERS.map((filter, index) => ({
              ...filter,
              color:
                filter.color === "default"
                  ? "text.secondary"
                  : `${filter.color}.main`,
              count: counts[index],
            })),
          ].map(({ label, status, color, count }) => (
            <ToggleButton
              key={label}
              value={status}
              sx={{ flexDirection: "column", minWidth: "6rem", py: 0.5 }}
            >
              <Typography variant="h6" sx={{ color }}>
                {count}
              </Typography>
              <Typography variant="caption">{label}</Typography>
            </ToggleButton>
          ))}
          {other > 0 && (
            <ToggleButton
              value="other"
              disabled
              sx={{ flexDirection: "column", minWidth: "6rem", py: 0.5 }}
            >
              <Typography variant="h6">{other}</Typography>
              <Typography variant="caption">Other</Typography>
            </ToggleButton>
          )}
        </ToggleButtonGroup>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: 2,
        }}
      >
        <TextField
          size="small"
          label="Source ID"
          name="sourceID"
          value={filters.sourceID ?? ""}
          onChange={(e) => onChange({ sourceID: e.target.value })}
        />
        <Autocomplete
          size="small"
          options={instruments}
          value={
            instruments.find(({ id }: any) => id === filters.instrumentID) ??
            null
          }
          onChange={(_e, instrument) =>
            onChange({
              instrumentID: instrument?.id,
              allocationID: undefined,
            })
          }
          renderInput={(params) => <TextField {...params} label="Instrument" />}
        />
        <Autocomplete
          size="small"
          options={instrumentAllocations}
          getOptionLabel={allocationLabel}
          value={
            allocations.find(({ id }) => id === filters.allocationID) ?? null
          }
          onChange={(_e, allocation) =>
            onChange({ allocationID: allocation?.id })
          }
          renderInput={(params) => <TextField {...params} label="Allocation" />}
        />
        <Autocomplete
          size="small"
          multiple
          options={users}
          getOptionLabel={(user: any) => user.username}
          value={users.filter(({ id }: any) =>
            filters.requesters?.includes(id),
          )}
          onChange={(_e, selected) =>
            onChange({ requesters: selected.map(({ id }: any) => id) })
          }
          renderInput={(params) => <TextField {...params} label="Requesters" />}
        />
        <TextField
          size="small"
          type="number"
          label="Minimum priority"
          value={filters.priorityThreshold ?? ""}
          onChange={(e) =>
            onChange({
              priorityThreshold:
                e.target.value === "" ? undefined : Number(e.target.value),
            })
          }
        />
        <DateTimeField
          label="Observation from"
          value={filters.observationStartDate}
          onChange={(observationStartDate) =>
            onChange({ observationStartDate })
          }
        />
        <DateTimeField
          label="Observation to"
          value={filters.observationEndDate}
          onChange={(observationEndDate) => onChange({ observationEndDate })}
        />
      </Box>
    </Paper>
  );
};

export default FollowupRequestFilters;
