import { useMemo } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import FormHelperText from "@mui/material/FormHelperText";
import InputLabel from "@mui/material/InputLabel";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import OutlinedInput from "@mui/material/OutlinedInput";
import Select from "@mui/material/Select";

import { useGetStreamsQuery } from "../../../../ducks/streams";

/** The survey token a stream name belongs to ("ZTF Public+Partnership" -> "ZTF"). */
export const surveyToken = (stream?: string | null) =>
  stream ? stream.split(" ")[0] : undefined;

/** Every survey the user has a stream for, which is what a module may be scoped to. */
export const useSurveyTokens = () => {
  const { data: streams } = useGetStreamsQuery();
  return useMemo(() => {
    const tokens = (streams ?? [])
      .map((stream: any) => surveyToken(stream?.name))
      .filter(Boolean) as string[];
    return Array.from(new Set(tokens)).sort();
  }, [streams]);
};

interface ModuleStreamsProps {
  value: string[];
  onChange: (streams: string[]) => void;
  label?: string;
}

/** Which surveys a saved variable/block is offered in.
 *
 * The builder hides a module whose surveys exclude the filter being edited, so
 * a module saved against one survey is invisible in every other until this is
 * widened -- which is why it is asked for rather than assumed.
 */
const ModuleStreams = ({
  value,
  onChange,
  label = "Available in",
}: ModuleStreamsProps) => {
  const tokens = useSurveyTokens();
  const options = useMemo(
    () => Array.from(new Set([...tokens, ...value])).sort(),
    [tokens, value],
  );

  return (
    <FormControl fullWidth size="small" sx={{ mt: 1 }}>
      <InputLabel id="module-streams-label">{label}</InputLabel>
      <Select
        multiple
        labelId="module-streams-label"
        value={value}
        input={<OutlinedInput label={label} />}
        onChange={(e) => {
          const next = e.target.value;
          onChange(typeof next === "string" ? next.split(",") : next);
        }}
        renderValue={(selected) => (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {(selected as string[]).map((s) => (
              <Chip key={s} label={s} size="small" />
            ))}
          </Box>
        )}
        data-testid="moduleStreamsSelect"
      >
        {options.map((token) => (
          <MenuItem key={token} value={token}>
            <Checkbox checked={value.includes(token)} size="small" />
            <ListItemText primary={token} />
          </MenuItem>
        ))}
      </Select>
      <FormHelperText>
        {value.length === 0
          ? "Offered in every survey."
          : "Hidden in surveys not listed here."}
      </FormHelperText>
    </FormControl>
  );
};

export default ModuleStreams;
