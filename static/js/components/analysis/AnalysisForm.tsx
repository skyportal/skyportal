import { skipToken } from "@reduxjs/toolkit/query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { showNotification } from "baselayer/components/Notifications";

import { useGetGroupsQuery } from "../../ducks/groups";
import { useFetchSourcePhotometryQuery } from "../../ducks/photometry";
import { useGetAnalysisServicesQuery } from "../../ducks/analysis_services";
import {
  useStartAnalysisMutation,
  useGetAssociatedGcnsQuery,
} from "../../ducks/source";
import { useAppDispatch } from "../../types/hooks";
import { utc_to_mjd } from "../../units";
import SearchableSelect from "../SearchableSelect";
import GroupShareSelect from "../group/GroupShareSelect";

dayjs.extend(utc);

const ANALYSIS_TYPE_LABELS: Record<string, string> = {
  lightcurve_fitting: "Light-Curve Fitting",
  spectrum_fitting: "Spectral Classification",
  period_finding: "Period Finding",
  gw_search: "Gravitational-Wave Searches",
  meta_analysis: "Meta / Summarization",
};

const toUtcInput = (date: string) =>
  dayjs.utc(date).format("YYYY-MM-DDTHH:mm:ss");

const serviceLabel = (service: any) =>
  service?.display_name || service?.name || "";

const readAsDataUrl = (file: File) =>
  new Promise<string>((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.readAsDataURL(file);
  });

const isTrue = (value: any) => ["True", "true", "t"].includes(value);

const buildSchema = (service: any, photometry: any[] | undefined) => {
  const properties: Record<string, any> = {};
  const uiSchema: Record<string, any> = {};
  const required = ["show_parameters", "show_plots", "show_corner"];
  const fileKeys: string[] = [];
  let acceptsTriggerTime = false;

  Object.entries(service?.optional_analysis_parameters ?? {}).forEach(
    ([key, params]: [string, any]) => {
      if (key === "trigger_time") {
        acceptsTriggerTime = true;
        return;
      }
      if (Array.isArray(params) || typeof params !== "object") {
        if (
          Array.isArray(params) &&
          ["True", "False"].every((val) => params.includes(val))
        ) {
          properties[key] = { type: "boolean" };
        } else {
          properties[key] = {
            type: "string",
            enum: params,
            default: params?.[0],
          };
          required.push(key);
        }
        return;
      }
      if (Array.isArray(params?.enum)) {
        properties[key] = { type: "string", enum: params.enum };
      } else if (params?.type === "file") {
        // rjsf v6 data-url FileWidget loops under MUI v7, so files bypass rjsf.
        fileKeys.push(key);
        return;
      } else if (["number", "string", "boolean"].includes(params?.type)) {
        properties[key] = { type: params.type };
      } else {
        return;
      }

      const title = params.title || key;
      properties[key].title = params.units
        ? `${title} (${params.units})`
        : title;
      if (params.default !== undefined) {
        properties[key].default = params.default;
      } else if (params.enum) {
        properties[key].default = params.enum[0];
      }
      if (params.description) properties[key].description = params.description;
      if (isTrue(params.required)) required.push(key);
    },
  );

  if (
    service?.optional_analysis_parameters &&
    service.input_data_types?.includes("photometry") &&
    photometry
  ) {
    const filters = [
      ...new Set(photometry.map((p: any) => p.filter).filter(Boolean)),
    ];
    const instruments: Record<number, string> = {};
    photometry.forEach(({ instrument_id, instrument_name }: any) => {
      if (instrument_id && instrument_name && !instruments[instrument_id]) {
        instruments[instrument_id] = instrument_name;
      }
    });
    const instrumentIds = Object.keys(instruments).map(Number);
    properties["input_filters_photometry_filters"] = {
      type: "array",
      title: "Filters to include (optional)",
      items: { type: "string", enum: filters },
      uniqueItems: true,
    };
    properties["input_filters_photometry_instruments"] = {
      type: "array",
      title: "Instruments to include (optional)",
      items: { type: "integer", enum: instrumentIds },
      uniqueItems: true,
    };
    uiSchema["input_filters_photometry_instruments"] = {
      "ui:enumNames": instrumentIds.map((id) => instruments[id]),
    };
  }

  return {
    schema: {
      type: "object",
      properties: {
        ...properties,
        show_parameters: {
          type: "boolean",
          title: "Show Parameters",
          default: true,
        },
        show_plots: { type: "boolean", title: "Show Plots", default: true },
        show_corner: { type: "boolean", title: "Show Corner", default: true },
      },
      required,
    },
    uiSchema,
    fileKeys,
    acceptsTriggerTime,
  };
};

const FieldGrid = ({ properties }: any) => (
  <Box
    sx={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
      columnGap: 2,
    }}
  >
    {properties.filter((p: any) => !p.hidden).map((p: any) => p.content)}
  </Box>
);

interface AnalysisFormProps {
  obj_id: string;
  analysisResourceType?: string;
}

const AnalysisForm = ({
  obj_id,
  analysisResourceType = "obj",
}: AnalysisFormProps) => {
  const dispatch = useAppDispatch();
  const [startAnalysis] = useStartAnalysisMutation();
  const isObj = analysisResourceType === "obj";

  const { data: photometry, isSuccess: photometryLoaded } =
    useFetchSourcePhotometryQuery(isObj ? { id: obj_id } : skipToken);
  const { data: associatedGcnsData } = useGetAssociatedGcnsQuery(
    isObj ? obj_id : skipToken,
  );
  const associatedGCNs: string[] = useMemo(
    () => (associatedGcnsData as any)?.gcns ?? [],
    [associatedGcnsData],
  );
  const { data: analysisServiceList = [], isLoading: servicesLoading } =
    useGetAnalysisServicesQuery();
  const { data: groupsData, isLoading: groupsLoading } = useGetGroupsQuery();
  const userAccessibleGroups = groupsData?.userAccessible;
  const singleUserGroup = groupsData?.user?.find(
    (g: any) => g.single_user_group,
  );

  const [selectedServiceId, setSelectedServiceId] = useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [runPrivately, setRunPrivately] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [triggerTimeUtc, setTriggerTimeUtc] = useState("");
  const fileValues = useRef<Record<string, File | null>>({});

  const selectedService: any = analysisServiceList.find(
    (s: any) => s.id === selectedServiceId,
  );

  const serviceHasRequiredInputs = useCallback(
    (service: any) =>
      !service?.input_data_types?.includes("photometry") ||
      !photometryLoaded ||
      (photometry?.length ?? 0) > 0,
    [photometry, photometryLoaded],
  );

  // Stable schema: rebuilding it each render resets the uncontrolled rjsf form.
  const { schema, uiSchema, fileKeys, acceptsTriggerTime } = useMemo(
    () => buildSchema(selectedService, photometry),
    [selectedService, photometry],
  );

  useEffect(() => {
    setTriggerTimeUtc(
      acceptsTriggerTime && associatedGCNs.length > 0
        ? toUtcInput(associatedGCNs[0]!)
        : "",
    );
  }, [selectedServiceId, acceptsTriggerTime, associatedGCNs]);

  useEffect(() => {
    if (selectedServiceId == null && analysisServiceList.length > 0) {
      const firstEnabled =
        analysisServiceList.find(
          (s: any) =>
            s?.display_on_resource_dropdown !== false &&
            serviceHasRequiredInputs(s),
        ) || analysisServiceList[0];
      setSelectedServiceId(firstEnabled?.id);
    }
  }, [analysisServiceList, selectedServiceId, serviceHasRequiredInputs]);

  if (servicesLoading || groupsLoading) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <CircularProgress size="1rem" />
        <Typography variant="body2" color="text.secondary">
          Loading analysis services...
        </Typography>
      </Box>
    );
  }
  if (!userAccessibleGroups?.length || !analysisServiceList.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No analysis services are available to you.
      </Typography>
    );
  }
  if (!selectedService) return null;

  const serviceOptions = analysisServiceList
    .filter(
      (s: any, i: number) =>
        s.display_on_resource_dropdown !== false &&
        analysisServiceList.findIndex((o: any) => o.name === s.name) === i,
    )
    // Autocomplete groupBy needs the options sorted by group.
    .sort(
      (a: any, b: any) =>
        (a.analysis_type || "").localeCompare(b.analysis_type || "") ||
        serviceLabel(a).localeCompare(serviceLabel(b)),
    );
  const shareableGroups = (selectedService.groups ?? []).filter((g: any) =>
    userAccessibleGroups.some((u: any) => u.id === g.id),
  );
  const triggerTime = triggerTimeUtc.trim();
  const triggerMjd = triggerTime ? utc_to_mjd(triggerTime) : null;

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setIsSubmitting(true);
    const {
      show_parameters,
      show_plots,
      show_corner,
      input_filters_photometry_filters: filters,
      input_filters_photometry_instruments: instruments,
      ...analysis_parameters
    } = formData;

    await Promise.all(
      fileKeys.map(async (key) => {
        const file = fileValues.current[key];
        if (file) analysis_parameters[key] = await readAsDataUrl(file);
      }),
    );
    if (acceptsTriggerTime && triggerMjd !== null) {
      analysis_parameters.trigger_time = triggerMjd;
    }

    try {
      await startAnalysis({
        id: obj_id,
        analysis_service_id: selectedServiceId,
        analysis_resource_type: analysisResourceType,
        formData: {
          show_parameters,
          show_plots,
          show_corner,
          analysis_parameters,
          input_filters: selectedService.input_data_types?.includes(
            "photometry",
          )
            ? {
                photometry: {
                  ...(filters && { filters }),
                  ...(instruments && { instruments }),
                },
              }
            : {},
          group_ids:
            runPrivately && singleUserGroup
              ? [singleUserGroup.id]
              : selectedGroupIds,
        },
      }).unwrap();
      dispatch(
        showNotification(
          `Analysis started with ${serviceLabel(selectedService) || "service"}.`,
        ),
      );
    } catch (error: any) {
      dispatch(
        showNotification(
          `Failed to start analysis: ${error?.message || error?.data?.message || "unknown error"}`,
          "error",
        ),
      );
    }
    setIsSubmitting(false);
  };

  return (
    <Stack spacing={2}>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-end",
          columnGap: 3,
          rowGap: 1,
        }}
      >
        <SearchableSelect
          options={serviceOptions}
          value={selectedService}
          onChange={(_e: any, value: any) =>
            setSelectedServiceId(value?.id ?? null)
          }
          getOptionLabel={serviceLabel}
          groupBy={(option: any) =>
            ANALYSIS_TYPE_LABELS[option?.analysis_type] ||
            option?.analysis_type ||
            "Other"
          }
          getOptionDisabled={(option: any) => !serviceHasRequiredInputs(option)}
          isOptionEqualToValue={(option: any, value: any) =>
            option?.id === value?.id
          }
          label="Start New Analysis"
          textFieldProps={{
            name: "analysisServiceSelect",
            "data-testid": "analysisServiceSelect",
          }}
          sx={{ flex: "1 1 320px" }}
        />
        <FormControlLabel
          control={
            <Switch
              checked={runPrivately}
              onChange={(e) => setRunPrivately(e.target.checked)}
              disabled={!singleUserGroup}
              data-testid="analysis-run-privately"
            />
          }
          label="Run privately (results and annotation visible only to me)"
        />
        {!runPrivately && (
          <GroupShareSelect
            groupList={shareableGroups}
            setGroupIDs={setSelectedGroupIds}
            groupIDs={selectedGroupIds}
          />
        )}
      </Box>
      {selectedService.description && (
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          {selectedService.description}
        </Typography>
      )}
      <Stack spacing={2} data-testid="analysis-service-request-form">
        {fileKeys.map((key) => (
          <Box key={key}>
            <InputLabel htmlFor={`root_${key}`}>{key}</InputLabel>
            <input
              type="file"
              id={`root_${key}`}
              onChange={(e) => {
                fileValues.current[key] = e.target.files?.[0] ?? null;
              }}
            />
          </Box>
        ))}
        {acceptsTriggerTime && (
          <Box>
            <InputLabel htmlFor="trigger_time_utc">
              T0: explosion/trigger time (UTC)
            </InputLabel>
            {associatedGCNs.length > 1 && (
              <Select
                inputProps={{ MenuProps: { disableScrollLock: true } }}
                value={
                  associatedGCNs.find(
                    (d) => toUtcInput(d) === triggerTimeUtc,
                  ) || ""
                }
                onChange={(e) => setTriggerTimeUtc(toUtcInput(e.target.value))}
                displayEmpty
                fullWidth
                data-testid="triggerTimeGcnSelect"
              >
                <MenuItem value="">Pick an associated G-event…</MenuItem>
                {associatedGCNs.map((d) => (
                  <MenuItem
                    value={d}
                    key={d}
                    sx={{ whiteSpace: "break-spaces" }}
                  >
                    {d}
                  </MenuItem>
                ))}
              </Select>
            )}
            <Box
              component="input"
              id="trigger_time_utc"
              data-testid="triggerTimeInput"
              type="text"
              value={triggerTimeUtc}
              placeholder="YYYY-MM-DDTHH:MM:SS UTC (blank = first detection − 2 d)"
              onChange={(e: any) => setTriggerTimeUtc(e.target.value)}
              sx={{ width: "100%" }}
            />
            <Box sx={{ fontSize: "0.8rem", opacity: 0.8 }}>
              {!triggerTime
                ? "No T0 set: the fit defaults to first detection − 2 days."
                : triggerMjd === null
                  ? "Unrecognized UTC datetime."
                  : `trigger_time = MJD ${triggerMjd.toFixed(6)}${
                      associatedGCNs.length > 0
                        ? ` (from associated G-event${associatedGCNs.length > 1 ? "s" : ""})`
                        : ""
                    }`}
            </Box>
          </Box>
        )}
        <Form
          key={selectedServiceId}
          schema={schema as any}
          uiSchema={uiSchema}
          validator={validator}
          templates={{ ObjectFieldTemplate: FieldGrid }}
          onSubmit={handleSubmit as any}
        />
        {isSubmitting && <CircularProgress />}
      </Stack>
    </Stack>
  );
};

export default AnalysisForm;
