import { useEffect, useState } from "react";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Slider from "@mui/material/Slider";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";

import type { Channel } from "./channels";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";

const DEFAULT_SLOT = [8, 20];

const ascending = (slot: number[]) => [...slot].sort((a, b) => a - b);

interface ChannelScheduleProps {
  type: string;
  channel: Channel;
}

const ChannelSchedule = ({ type, channel }: ChannelScheduleProps) => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const prefs =
    profile?.preferences["notifications"]?.[type]?.[channel.key] ?? {};
  const saved: number[] = prefs.time_slot ?? [];
  const [slot, setSlot] = useState<number[]>(
    ascending(saved.length ? saved : DEFAULT_SLOT),
  );

  useEffect(() => {
    if (saved.length) setSlot(ascending(saved));
  }, [saved.join(",")]);

  const inverted = saved.length === 2 && (saved[0] ?? 0) > (saved[1] ?? 0);
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
        padding: "0.25rem 0.75rem",
        borderRadius: 2,
        backgroundColor: "action.hover",
      }}
    >
      <Typography variant="body2" sx={{ fontWeight: 600, minWidth: "5.5rem" }}>
        {channel.label}
      </Typography>
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={prefs.on_shift === true}
            name={`on_shift_${channel.key}`}
            onChange={(event) => update({ on_shift: event.target.checked })}
          />
        }
        label={<Typography variant="body2">While I am on shift</Typography>}
      />
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={saved.length > 0}
            name={`time_slot_${channel.key}`}
            onChange={(event) => {
              setSlot(DEFAULT_SLOT);
              update({ time_slot: event.target.checked ? DEFAULT_SLOT : [] });
            }}
          />
        }
        label={<Typography variant="body2">Only between (UTC)</Typography>}
      />
      {saved.length > 0 && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            flexGrow: 1,
            minWidth: "16rem",
            paddingTop: 3,
          }}
        >
          <Slider
            size="small"
            getAriaLabel={() => "time_slot_slider"}
            value={slot}
            onChange={(_, value) => setSlot(value as number[])}
            onChangeCommitted={(_, value) => {
              const range = value as number[];
              update({ time_slot: inverted ? [...range].reverse() : range });
            }}
            valueLabelDisplay="on"
            valueLabelFormat={(hour) => `${hour}h`}
            min={0}
            max={24}
            step={1}
            marks
            track={inverted ? "inverted" : "normal"}
          />
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={inverted}
                onChange={() =>
                  update({ time_slot: inverted ? slot : [...slot].reverse() })
                }
                {...({ label: "Invert" } as any)}
              />
            }
            label={<Typography variant="body2">Outside</Typography>}
          />
        </Box>
      )}
    </Box>
  );
};

export default ChannelSchedule;
