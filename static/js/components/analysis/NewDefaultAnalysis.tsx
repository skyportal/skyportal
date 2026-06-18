import { useMemo, useState } from "react";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import FormLabel from "@mui/material/FormLabel";
import TextField from "@mui/material/TextField";
import RadioGroup from "@mui/material/RadioGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Radio from "@mui/material/Radio";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { useSubmitDefaultAnalysisMutation } from "../../ducks/default_analyses";

const useStyles = makeStyles()(() => ({
  container: { width: "32rem", maxWidth: "100%" },
  field: { marginTop: "1rem", width: "100%" },
  paramsHeader: { marginTop: "1.5rem" },
}));

type ParamField =
  | { key: string; kind: "enum"; options: string[]; default?: any }
  | { key: string; kind: "bool"; default?: any }
  | { key: string; kind: "number"; default?: any; title?: string }
  | { key: string; kind: "string"; default?: any; title?: string };

// Turn a service's optional_analysis_parameters into typed form fields, the same
// way the manual "run analysis" form does — so the default-analysis params align
// with each service: enum -> dropdown, True/False -> boolean, number/string ->
// typed input. (File params are skipped — not meaningful for an auto-trigger.)
const parseServiceParams = (optional: any): ParamField[] => {
  let spec = optional;
  if (typeof spec === "string") {
    try {
      spec = JSON.parse(spec);
    } catch {
      return [];
    }
  }
  const fields: ParamField[] = [];
  Object.entries(spec || {}).forEach(([key, params]: [string, any]) => {
    if (Array.isArray(params)) {
      if (["True", "False"].every((v) => params.includes(v))) {
        fields.push({ key, kind: "bool" });
      } else {
        fields.push({ key, kind: "enum", options: params });
      }
    } else if (params && typeof params === "object") {
      if (params.type === "number") {
        fields.push({
          key,
          kind: "number",
          default: params.default,
          title: params.title,
        });
      } else if (params.type === "boolean") {
        fields.push({ key, kind: "bool", default: params.default });
      } else if (params.type === "string") {
        fields.push({
          key,
          kind: "string",
          default: params.default,
          title: params.title,
        });
      }
    }
  });
  return fields;
};

const initialParamsData = (fields: ParamField[]): Record<string, any> => {
  const data: Record<string, any> = {};
  fields.forEach((f) => {
    if (f.kind === "enum") data[f.key] = f.default ?? f.options[0] ?? "";
    else if (f.kind === "bool") data[f.key] = f.default ?? false;
    else data[f.key] = f.default ?? "";
  });
  return data;
};

interface NewDefaultAnalysisProps {
  analysisService: any;
  onClose?: () => void;
}

// Form to create a DefaultAnalysis: auto-run this service when a source matches
// either a classification (name + probability) or is saved to a group.
const NewDefaultAnalysis = ({
  analysisService,
  onClose,
}: NewDefaultAnalysisProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [submitDefaultAnalysis] = useSubmitDefaultAnalysisMutation();

  const serviceGroups: any[] = analysisService?.groups ?? [];
  const serviceParams = useMemo(
    () => parseServiceParams(analysisService?.optional_analysis_parameters),
    [analysisService],
  );

  const [triggerType, setTriggerType] = useState<"classification" | "group">(
    "classification",
  );
  const [classificationName, setClassificationName] = useState("");
  const [probability, setProbability] = useState("0.9");
  const [triggerGroupId, setTriggerGroupId] = useState<number | "">(
    serviceGroups[0]?.id ?? "",
  );
  const [groupIds, setGroupIds] = useState<number[]>(
    serviceGroups.map((g) => g.id),
  );
  const [dailyLimit, setDailyLimit] = useState("10");
  const [paramsData, setParamsData] = useState<Record<string, any>>(() =>
    initialParamsData(serviceParams),
  );

  const setParam = (key: string, value: any) =>
    setParamsData((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    let source_filter: any;
    if (triggerType === "classification") {
      if (!classificationName) {
        dispatch(showNotification("Enter a classification name", "error"));
        return;
      }
      source_filter = {
        classifications: [
          { name: classificationName, probability: Number(probability) },
        ],
      };
    } else {
      if (!triggerGroupId) {
        dispatch(showNotification("Select a trigger group", "error"));
        return;
      }
      source_filter = { group_id: Number(triggerGroupId) };
    }

    // Assemble default_analysis_parameters from the service-aligned fields.
    const default_analysis_parameters: Record<string, any> = {};
    serviceParams.forEach((f) => {
      const value = paramsData[f.key];
      if (value === "" || value === undefined || value === null) return;
      default_analysis_parameters[f.key] =
        f.kind === "number" ? Number(value) : value;
    });

    submitDefaultAnalysis({
      analysisServiceId: analysisService.id,
      body: {
        source_filter,
        default_analysis_parameters,
        group_ids: groupIds,
        // optional: omit when blank so the API default (10) applies
        ...(dailyLimit.trim() !== ""
          ? { daily_limit: Number(dailyLimit) }
          : {}),
      },
    })
      .unwrap()
      .then(() => {
        dispatch(showNotification("Default analysis created"));
        onClose?.();
      })
      .catch((e: any) =>
        dispatch(
          showNotification(
            e?.data?.message || "Failed to create default analysis",
            "error",
          ),
        ),
      );
  };

  const renderParamField = (f: ParamField) => {
    const value = paramsData[f.key];
    const label = (f as any).title || f.key;
    if (f.kind === "enum") {
      return (
        <FormControl className={classes.field} key={f.key}>
          <InputLabel id={`param-${f.key}-label`}>{label}</InputLabel>
          <Select
            labelId={`param-${f.key}-label`}
            label={label}
            value={value ?? ""}
            onChange={(e) => setParam(f.key, e.target.value)}
          >
            {f.options.map((opt) => (
              <MenuItem key={opt} value={opt}>
                {opt}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    }
    if (f.kind === "bool") {
      return (
        <FormControl className={classes.field} key={f.key}>
          <InputLabel id={`param-${f.key}-label`}>{label}</InputLabel>
          <Select
            labelId={`param-${f.key}-label`}
            label={label}
            value={value ? "true" : "false"}
            onChange={(e) => setParam(f.key, e.target.value === "true")}
          >
            <MenuItem value="true">True</MenuItem>
            <MenuItem value="false">False</MenuItem>
          </Select>
        </FormControl>
      );
    }
    return (
      <TextField
        className={classes.field}
        key={f.key}
        label={label}
        type={f.kind === "number" ? "number" : "text"}
        value={value ?? ""}
        onChange={(e) => setParam(f.key, e.target.value)}
      />
    );
  };

  return (
    <div className={classes.container}>
      <FormControl className={classes.field}>
        <FormLabel>Trigger on</FormLabel>
        <RadioGroup
          row
          value={triggerType}
          onChange={(e) =>
            setTriggerType(e.target.value as "classification" | "group")
          }
        >
          <FormControlLabel
            value="classification"
            control={<Radio />}
            label="Classification"
          />
          <FormControlLabel
            value="group"
            control={<Radio />}
            label="Saved to group"
          />
        </RadioGroup>
      </FormControl>

      {triggerType === "classification" ? (
        <>
          <TextField
            className={classes.field}
            label="Classification name"
            value={classificationName}
            onChange={(e) => setClassificationName(e.target.value)}
          />
          <TextField
            className={classes.field}
            label="Minimum probability"
            type="number"
            inputProps={{ step: 0.05, min: 0, max: 1 }}
            value={probability}
            onChange={(e) => setProbability(e.target.value)}
          />
        </>
      ) : (
        <FormControl className={classes.field}>
          <InputLabel id="trigger-group-label">Trigger group</InputLabel>
          <Select
            labelId="trigger-group-label"
            label="Trigger group"
            value={triggerGroupId}
            onChange={(e) => setTriggerGroupId(e.target.value as number)}
          >
            {serviceGroups.map((g) => (
              <MenuItem key={g.id} value={g.id}>
                {g.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      <TextField
        className={classes.field}
        label="Daily limit (optional)"
        type="number"
        inputProps={{ min: 1 }}
        value={dailyLimit}
        onChange={(e) => setDailyLimit(e.target.value)}
        helperText="Max auto-runs per day; leave blank for the default (10)."
      />

      <FormControl className={classes.field}>
        <InputLabel id="share-groups-label">
          Share results with groups
        </InputLabel>
        <Select
          labelId="share-groups-label"
          label="Share results with groups"
          multiple
          value={groupIds}
          onChange={(e) => setGroupIds(e.target.value as number[])}
        >
          {serviceGroups.map((g) => (
            <MenuItem key={g.id} value={g.id}>
              {g.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {serviceParams.length > 0 && (
        <>
          <Typography className={classes.paramsHeader} variant="subtitle2">
            {analysisService?.display_name || "Analysis"} parameters
          </Typography>
          {serviceParams.map(renderParamField)}
        </>
      )}

      <Button
        primary
        onClick={handleSubmit}
        style={{ marginTop: "1rem" }}
        data-testid="add-default-analysis-button"
      >
        Add default analysis
      </Button>
    </div>
  );
};

export default NewDefaultAnalysis;
