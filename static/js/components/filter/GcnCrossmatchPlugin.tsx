import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import Button from "../Button";
import GcnNoticeTypesSelect from "../gcn/GcnNoticeTypesSelect";
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
  {
    key: "min_detections",
    label: "Min detections",
    help: "Detections an object needs, e.g. 2 from its second alert",
  },
  {
    key: "max_days_to_first_detection",
    label: "Max days to first detection",
    help: "First detected after the event and within this many days",
  },
  {
    key: "max_detection_span_days",
    label: "Max detection span (days)",
    help: "Drop objects detected over a longer time than this",
  },
];

const SORT_ORDERS = [
  { value: "Descending", label: "Newest first" },
  { value: "Ascending", label: "Oldest first" },
];

const GcnCrossmatchPlugin = () => {
  const { fid } = useParams();
  const { data: filter, refetch } = useGetFilterQuery(fid ?? "", {
    skip: !fid,
  }) as any;
  const [updateFilter] = useUpdateFilterMutation();

  const [enabled, setEnabled] = useState(false);
  const [tags, setTags] = useState("");
  const [excludedNoticeTypes, setExcludedNoticeTypes] = useState<string[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [sortOrder, setSortOrder] = useState("");
  const [saved, setSaved] = useState(false);

  const stored = filter?.altdata?.[KEY];

  useEffect(() => {
    const config = stored ?? {};
    setEnabled(Boolean(config.enabled));
    setTags((config.filters?.gcn_tags ?? []).join(", "));
    setExcludedNoticeTypes(config.exclude_notice_types ?? []);
    setSortOrder(config.sort_order ?? "");
    setValues(
      Object.fromEntries(
        SETTINGS.map(({ key }) => [key, String(config[key] ?? "")]),
      ),
    );
  }, [filter, stored]);

  if (!filter) return null;

  const handleSave = async () => {
    const { data: current } = await refetch();
    if (!current) return;

    const config: Record<string, any> = {
      ...(current.altdata?.[KEY] ?? {}),
      enabled,
    };
    SETTINGS.forEach(({ key }) => {
      const parsed = Number(values[key]);
      if (values[key] && !Number.isNaN(parsed)) config[key] = parsed;
      else delete config[key];
    });
    const gcnTags = tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    const filters = { ...(config["filters"] ?? {}) };
    if (gcnTags.length) filters["gcn_tags"] = gcnTags;
    else delete filters["gcn_tags"];
    if (Object.keys(filters).length) config["filters"] = filters;
    else delete config["filters"];
    if (excludedNoticeTypes.length)
      config["exclude_notice_types"] = excludedNoticeTypes;
    else delete config["exclude_notice_types"];
    if (sortOrder) config["sort_order"] = sortOrder;
    else delete config["sort_order"];

    const result = await updateFilter({
      filter_id: filter.id,
      altdata: { ...(current.altdata ?? {}), [KEY]: config },
    });
    setSaved(!("error" in result));
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
        <GcnNoticeTypesSelect
          label="Ignore notice types"
          id="selectCrossmatchIgnoredNoticeTypes"
          selectedGcnNoticeTypes={excludedNoticeTypes}
          setSelectedGcnNoticeTypes={(value: string[]) => {
            setExcludedNoticeTypes(value);
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
        <TextField
          select
          size="small"
          label="Sort order"
          helperText="Which alerts are kept when a search hits its limit"
          value={sortOrder}
          onChange={(event) => {
            setSortOrder(event.target.value);
            setSaved(false);
          }}
        >
          <MenuItem value="">Default</MenuItem>
          {SORT_ORDERS.map(({ value, label }) => (
            <MenuItem key={value} value={value}>
              {label}
            </MenuItem>
          ))}
        </TextField>
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
