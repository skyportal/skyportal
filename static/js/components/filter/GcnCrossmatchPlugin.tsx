import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Chip from "@mui/material/Chip";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import Button from "../Button";
import {
  useGetFilterQuery,
  useUpdateFilterAltdataMutation,
} from "../../ducks/filter";

const KEY = "gcn_crossmatch";

/** Settings a filter's crossmatch inherits; blank means "use the default". */
const SETTINGS: { key: string; label: string; help: string }[] = [
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
  const [updateAltdata] = useUpdateFilterAltdataMutation();

  const [enabled, setEnabled] = useState(false);
  const [tags, setTags] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

  const stored = filter?.altdata?.[KEY];

  useEffect(() => {
    if (!filter) return;
    const config = stored ?? {};
    setEnabled(Boolean(config.enabled));
    setTags((config.filters?.gcn_tags ?? []).join(", "));
    setValues(
      Object.fromEntries(
        SETTINGS.map(({ key }) => [
          key,
          config[key] === undefined || config[key] === null
            ? ""
            : String(config[key]),
        ]),
      ),
    );
  }, [filter, stored]);

  if (!filter) return <></>;

  const handleSave = async () => {
    const config: Record<string, any> = { enabled };
    SETTINGS.forEach(({ key }) => {
      const raw = values[key];
      // an empty box means "inherit", not "zero"
      if (raw !== undefined && raw !== "") {
        const parsed = Number(raw);
        if (!Number.isNaN(parsed)) config[key] = parsed;
      }
    });
    const gcnTags = tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (gcnTags.length) config["filters"] = { gcn_tags: gcnTags };

    await updateAltdata({
      filter_id: filter.id,
      altdata: { ...(filter.altdata ?? {}), [KEY]: config },
    });
    setSaved(true);
  };

  return (
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography sx={{ fontWeight: 500 }}>GCN crossmatch</Typography>
        {stored?.enabled && (
          <Chip size="small" color="primary" label="on" sx={{ ml: 1 }} />
        )}
      </AccordionSummary>
      <AccordionDetails>
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 1 }}>
          Search this filter&apos;s broker for alerts inside the localization of
          each recent GCN event, and raise what lands there as candidates for
          this filter&apos;s group.
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
              helperText={`${help} — blank inherits the default`}
              value={values[key] ?? ""}
              onChange={(event) => {
                setValues({ ...values, [key]: event.target.value });
                setSaved(false);
              }}
            />
          ))}
          <div>
            <Button primary onClick={handleSave} name="saveGcnCrossmatch">
              Save
            </Button>
            {saved && (
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", display: "inline", ml: 1 }}
              >
                Saved
              </Typography>
            )}
          </div>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
};

export default GcnCrossmatchPlugin;
