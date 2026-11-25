import { FormEvent } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import InputAdornment from "@mui/material/InputAdornment";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";

import SegmentedControl from "../SegmentedControl";
import { dec_to_deg, ra_to_deg } from "../../units";

export type SearchMode = "object" | "designation" | "position";

export interface AlertSearch {
  mode: SearchMode;
  objectId: string;
  designation: string;
  ra: string;
  dec: string;
  radius: string;
  survey: string;
}

export const DEFAULT_SEARCH: AlertSearch = {
  mode: "object",
  objectId: "",
  designation: "",
  ra: "",
  dec: "",
  radius: "5",
  survey: "",
};

const ARGUS_OBJECT_ID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

// Mirrors the backend's survey_from_object_id.
export const guessSurvey = (objectId: string) => {
  const id = objectId.trim();
  if (/^ZTF\d{2}[a-z]{7}$/.test(id)) return "ZTF";
  if (/^[ACT]20\d{13}[pm]\d{6}$/.test(id)) return "DECAM";
  if (/^(sso)?\d+$/.test(id)) return "LSST";
  if (ARGUS_OBJECT_ID.test(id)) return "ARGUS";
  if (/^ASKAP-\d+$/.test(id)) return "ASKAP";
  return undefined;
};

const autoSurvey = (objectId: string, surveys: string[]) => {
  const guessed = guessSurvey(objectId);
  return (
    (guessed && surveys.includes(guessed) ? guessed : undefined) ||
    surveys[0] ||
    "ZTF"
  );
};

export const searchSurvey = (search: AlertSearch, surveys: string[]) => {
  if (search.mode === "designation") return "ZTF";
  if (search.survey) return search.survey;
  return autoSurvey(search.mode === "object" ? search.objectId : "", surveys);
};

const inRange = (value: number, min: number, max: number) =>
  Number.isFinite(value) && value >= min && value <= max;

const fieldErrors = (search: AlertSearch) => ({
  ra: search.ra.trim() !== "" && !inRange(ra_to_deg(search.ra.trim()), 0, 360),
  dec:
    search.dec.trim() !== "" &&
    !inRange(dec_to_deg(search.dec.trim()), -90, 90),
  radius: search.radius.trim() !== "" && !(Number(search.radius) > 0),
});

export const isComplete = (search: AlertSearch) => {
  if (search.mode === "object") return search.objectId.trim() !== "";
  if (search.mode === "designation") return search.designation.trim() !== "";
  const errors = fieldErrors(search);
  return (
    [search.ra, search.dec, search.radius].every((v) => v.trim() !== "") &&
    !errors.ra &&
    !errors.dec &&
    !errors.radius
  );
};

interface BrokerAlertSearchProps {
  value: AlertSearch;
  onChange: (value: AlertSearch) => void;
  onSearch: () => void;
  surveys: string[];
  designationSearch: boolean;
  searching: boolean;
}

const BrokerAlertSearch = ({
  value,
  onChange,
  onSearch,
  surveys,
  designationSearch,
  searching,
}: BrokerAlertSearchProps) => {
  const set = (patch: Partial<AlertSearch>) => onChange({ ...value, ...patch });
  const errors = fieldErrors(value);
  const shrink = { inputLabel: { shrink: true } };
  const modes = [
    { value: "object" as const, label: "Object" },
    ...(designationSearch
      ? [{ value: "designation" as const, label: "Solar system" }]
      : []),
    { value: "position" as const, label: "Cone search" },
  ];

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (isComplete(value) && !searching) onSearch();
  };

  const surveyField = surveys.length > 1 && (
    <TextField
      select
      size="small"
      label="Survey"
      value={value.mode === "designation" ? "ZTF" : value.survey}
      disabled={value.mode === "designation"}
      onChange={(e) => set({ survey: e.target.value })}
      slotProps={{
        select: {
          displayEmpty: true,
          renderValue: (selected: unknown) =>
            (selected as string) ||
            (value.mode !== "object"
              ? autoSurvey("", surveys)
              : value.objectId.trim()
                ? `Auto (${autoSurvey(value.objectId, surveys)})`
                : "Auto"),
        },
        ...shrink,
      }}
      sx={{ width: 150, flexShrink: 0 }}
    >
      {value.mode === "object" && <MenuItem value="">Auto</MenuItem>}
      {surveys.map((s) => (
        <MenuItem key={s} value={s}>
          {s}
        </MenuItem>
      ))}
    </TextField>
  );

  return (
    <Paper
      variant="outlined"
      component="form"
      onSubmit={submit}
      sx={{ p: 2, mb: 2, display: "flex", flexDirection: "column", gap: 2 }}
    >
      <Box>
        <SegmentedControl
          value={value.mode}
          options={modes}
          onChange={(mode) => set({ mode })}
        />
      </Box>
      <Box
        sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 2 }}
      >
        {value.mode === "object" && (
          <TextField
            size="small"
            label="Object ID"
            value={value.objectId}
            slotProps={shrink}
            onChange={(e) => set({ objectId: e.target.value })}
            autoFocus
            sx={{ flex: "1 1 18rem" }}
          />
        )}
        {value.mode === "designation" && (
          <TextField
            size="small"
            label="Designation"
            placeholder="e.g. 6993, 10P"
            value={value.designation}
            slotProps={shrink}
            onChange={(e) => set({ designation: e.target.value })}
            autoFocus
            sx={{ flex: "1 1 18rem" }}
          />
        )}
        {value.mode === "position" && (
          <>
            <TextField
              size="small"
              label="RA"
              placeholder="deg or HH:MM:SS"
              value={value.ra}
              error={errors.ra}
              slotProps={shrink}
              onChange={(e) => set({ ra: e.target.value })}
              autoFocus
              sx={{ flex: "1 1 10rem" }}
            />
            <TextField
              size="small"
              label="Dec"
              placeholder="deg or ±DD:MM:SS"
              value={value.dec}
              error={errors.dec}
              slotProps={shrink}
              onChange={(e) => set({ dec: e.target.value })}
              sx={{ flex: "1 1 10rem" }}
            />
            <TextField
              size="small"
              label="Radius"
              value={value.radius}
              error={errors.radius}
              onChange={(e) => set({ radius: e.target.value })}
              slotProps={{
                ...shrink,
                input: {
                  endAdornment: (
                    <InputAdornment position="end">arcsec</InputAdornment>
                  ),
                },
              }}
              sx={{ flex: "0 1 9rem" }}
            />
          </>
        )}
        {surveyField}
        <Button
          type="submit"
          variant="contained"
          disabled={!isComplete(value) || searching}
          sx={{ flexShrink: 0 }}
        >
          {searching ? "Searching…" : "Search"}
        </Button>
      </Box>
    </Paper>
  );
};

export default BrokerAlertSearch;
