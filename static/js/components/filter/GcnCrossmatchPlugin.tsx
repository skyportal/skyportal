import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import Button from "../Button";
import { useGetFilterQuery, useUpdateFilterMutation } from "../../ducks/filter";

const KEY = "gcn_crossmatch";

const SETTINGS = [
  {
    key: "cumprob",
    label: "Credible region",
    help: "Cumulative probability searched, e.g. 0.95",
  },
  {
    key: "max_credible_level",
    label: "Max credible level",
    help: "Drop matches shallower than this, e.g. 0.5",
  },
  {
    key: "delta_t_before",
    label: "Days before",
    help: "How far before the event to accept alerts",
  },
  {
    key: "delta_t_after",
    label: "Days after",
    help: "How far after the event to accept alerts",
  },
  {
    key: "max_radius_deg",
    label: "Max radius (deg)",
    help: "Skip localizations bounding larger than this",
  },
];

const GcnCrossmatchPlugin = () => {
  const { fid } = useParams();
  const { data: filter } = useGetFilterQuery(fid ?? "", { skip: !fid }) as any;
  const [updateFilter] = useUpdateFilterMutation();

  const [enabled, setEnabled] = useState(false);
  const [tags, setTags] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

  const stored = filter?.altdata?.[KEY];

  useEffect(() => {
    const config = stored ?? {};
    setEnabled(Boolean(config.enabled));
    setTags((config.filters?.gcn_tags ?? []).join(", "));
    setValues(
      Object.fromEntries(
        SETTINGS.map(({ key }) => [key, String(config[key] ?? "")]),
      ),
    );
  }, [filter, stored]);

  if (!filter) return null;

  const handleSave = async () => {
    const config: Record<string, any> = { enabled };
    SETTINGS.forEach(({ key }) => {
      const parsed = Number(values[key]);
      if (values[key] && !Number.isNaN(parsed)) config[key] = parsed;
    });
    const gcnTags = tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (gcnTags.length) config["filters"] = { gcn_tags: gcnTags };

    await updateFilter({
      filter_id: filter.id,
      altdata: { ...(filter.altdata ?? {}), [KEY]: config },
    });
    setSaved(true);
  };

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="h6">GCN crossmatch</Typography>
        {stored?.enabled && <Chip size="small" color="primary" label="on" />}
      </Box>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 1 }}>
        Search this filter&apos;s broker for alerts inside the localization of
        each recent GCN event, and raise what lands there as candidates for this
        filter&apos;s group.
      </Typography>
      <Stack spacing={2}>
        <FormControlLabel
          control={
            <Switch
              checked={enabled}
              onChange={(event) => {
                setEnabled(event.target.checked);
                setSaved(false);
              }}
              slotProps={{
                input: { "aria-label": "enable gcn crossmatch" },
              }}
            />
          }
          label="Crossmatch GCN events with this filter"
        />
        <TextField
          size="small"
          label="Only events tagged (comma separated)"
          helperText="Leave blank for every event, e.g. Einstein Probe, GRB"
          value={tags}
          onChange={(event) => {
            setTags(event.target.value);
            setSaved(false);
          }}
        />
        {SETTINGS.map(({ key, label, help }) => (
          <TextField
            key={key}
            size="small"
            label={label}
            helperText={`${help} (blank inherits the default)`}
            value={values[key] ?? ""}
            onChange={(event) => {
              setValues({ ...values, [key]: event.target.value });
              setSaved(false);
            }}
          />
        ))}
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Tooltip
            describeChild
            title="Save these crossmatch settings. They are stored on the filter, apart from its versions, and apply whichever version is active."
          >
            <Button primary onClick={handleSave}>
              Save
            </Button>
          </Tooltip>
          {saved && (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              Saved
            </Typography>
          )}
        </Box>
      </Stack>
    </Paper>
  );
};

export default GcnCrossmatchPlugin;
