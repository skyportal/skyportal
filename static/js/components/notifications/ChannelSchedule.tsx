import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import type { Channel } from "./channels";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";

const DEFAULT_START = 8;
const DEFAULT_END = 20;
const HOURS = Array.from({ length: 25 }, (_, hour) => hour);

const localHour = (utcHour: number) => {
  const date = new Date();
  date.setUTCHours(utcHour, 0, 0, 0);
  return date.toLocaleTimeString([], { hour: "numeric" });
};

const Choice = ({
  label,
  selected,
  onClick,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
}) => (
  <Box
    component="button"
    type="button"
    aria-pressed={selected}
    onClick={onClick}
    sx={(theme) => ({
      border: 0,
      padding: "0.25rem 0.75rem",
      borderRadius: 999,
      fontFamily: "inherit",
      fontSize: "0.8125rem",
      fontWeight: 500,
      cursor: "pointer",
      color: selected ? "primary.main" : "text.secondary",
      backgroundColor: selected
        ? alpha(theme.palette.primary.main, 0.12)
        : "transparent",
      transition: "all 120ms",
      "&:hover, &:focus-visible": { color: "primary.main", outline: "none" },
    })}
  >
    {label}
  </Box>
);

const HourSelect = ({
  value,
  disabled,
  label,
  onChange,
}: {
  value: number;
  disabled: boolean;
  label: string;
  onChange: (hour: number) => void;
}) => (
  <Select
    size="small"
    variant="standard"
    value={value}
    disabled={disabled}
    onChange={(event) => onChange(Number(event.target.value))}
    inputProps={{ "aria-label": label }}
    MenuProps={{ slotProps: { paper: { sx: { maxHeight: 280 } } } }}
    sx={{ fontSize: "0.875rem" }}
  >
    {HOURS.map((hour) => (
      <MenuItem key={hour} value={hour}>
        {hour}h
      </MenuItem>
    ))}
  </Select>
);

interface ChannelScheduleProps {
  type: string;
  channel: Channel;
}

const ChannelSchedule = ({ type, channel }: ChannelScheduleProps) => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const prefs =
    profile?.preferences["notifications"]?.[type]?.[channel.key] ?? {};
  const onShift = prefs.on_shift === true;
  const slot: number[] = prefs.time_slot ?? [];
  const hasSlot = slot.length > 0;
  const limited = onShift || hasSlot;
  const start = slot[0] ?? DEFAULT_START;
  const end = slot[1] ?? DEFAULT_END;

  const update = (values: Record<string, unknown>) =>
    updateUserPreferences({
      notifications: { [type]: { [channel.key]: values } },
    });

  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        columnGap: 2,
        rowGap: 0.5,
        padding: "0.375rem 0.75rem",
        borderRadius: 2,
        backgroundColor: "action.hover",
      }}
    >
      <Typography variant="body2" sx={{ fontWeight: 600, minWidth: "5.5rem" }}>
        {channel.label}
      </Typography>
      <Box
        sx={{
          display: "inline-flex",
          padding: "2px",
          borderRadius: 999,
          border: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Choice
          label="Anytime"
          selected={!limited}
          onClick={() => update({ on_shift: false, time_slot: [] })}
        />
        <Choice
          label="Only when"
          selected={limited}
          onClick={() =>
            !limited && update({ time_slot: [DEFAULT_START, DEFAULT_END] })
          }
        />
      </Box>
      {limited && (
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            columnGap: 1,
          }}
        >
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={onShift}
                name={`on_shift_${channel.key}`}
                onChange={(event) => update({ on_shift: event.target.checked })}
              />
            }
            label={<Typography variant="body2">I am on shift</Typography>}
            sx={{ marginRight: 0 }}
          />
          <Typography variant="body2" color="textSecondary">
            or
          </Typography>
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={hasSlot}
                name={`time_slot_${channel.key}`}
                onChange={(event) =>
                  update({
                    time_slot: event.target.checked ? [start, end] : [],
                  })
                }
              />
            }
            label={<Typography variant="body2">between</Typography>}
            sx={{ marginRight: 0 }}
          />
          <HourSelect
            value={start}
            disabled={!hasSlot}
            label="time_slot_start"
            onChange={(hour) => update({ time_slot: [hour, end] })}
          />
          <Typography variant="body2">and</Typography>
          <HourSelect
            value={end}
            disabled={!hasSlot}
            label="time_slot_end"
            onChange={(hour) => update({ time_slot: [start, hour] })}
          />
          <Typography variant="body2" color="textSecondary">
            UTC
            {hasSlot &&
              new Date().getTimezoneOffset() !== 0 &&
              ` (${localHour(start)} to ${localHour(end)} local)`}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default ChannelSchedule;
