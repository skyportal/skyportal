import { useGetGroupsQuery } from "../../ducks/groups";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import SearchableSelect from "../SearchableSelect";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { useFetchSourcePhotometryQuery } from "../../ducks/photometry";
import { useGetAnalysisServicesQuery } from "../../ducks/analysis_services";
import {
  useStartAnalysisMutation,
  useGetAssociatedGcnsQuery,
} from "../../ducks/source";
import GroupShareSelect from "../group/GroupShareSelect";
import { utc_to_mjd } from "../../units";
import { useAppDispatch } from "../../types/hooks";
import { showNotification } from "baselayer/components/Notifications";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  loading: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
  },
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  marginTop: {
    marginTop: "1rem",
  },
  Select: {
    width: "100%",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
  serviceDescription: {
    margin: "0.25rem 0 0 0",
    fontSize: "0.85rem",
    color: "gray",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
    "& > *": {
      marginTop: "1rem",
      marginBottom: "1rem",
    },
  },
}));

interface AnalysisFormProps {
  obj_id: string;
}

const AnalysisForm = ({ obj_id }: AnalysisFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [startAnalysis] = useStartAnalysisMutation();

  const { data: photometry, isSuccess: photometryLoaded } =
    useFetchSourcePhotometryQuery({ id: obj_id });
  // dateobs (== T0) of GW/GCN events associated with this source, used to
  // prefill the afterglow trigger time (see the trigger_time widget below).
  const { data: associatedGcnsData } = useGetAssociatedGcnsQuery(obj_id);
  const associatedGCNs: string[] = useMemo(
    () => (associatedGcnsData as any)?.gcns ?? [],
    [associatedGcnsData],
  );
  const { data: analysisServiceListData, isLoading: servicesLoading } =
    useGetAnalysisServicesQuery();
  const analysisServiceList = useMemo(
    () => analysisServiceListData ?? [],
    [analysisServiceListData],
  );
  const uniqueNames = [
    ...new Set(analysisServiceList.map((item: any) => item.name)),
  ];
  const uniqueAnalysisServiceList = uniqueNames
    .map((name) => analysisServiceList.find((item: any) => item.name === name))
    .filter(Boolean)
    // Sort by analysis_type (so Autocomplete groups don't fragment) then label.
    .sort((a: any, b: any) => {
      const byType = (a.analysis_type || "").localeCompare(
        b.analysis_type || "",
      );
      return byType !== 0
        ? byType
        : (a.display_name || a.name).localeCompare(b.display_name || b.name);
    });
  // Only groups the user can access (all groups for sysadmins, member groups
  // otherwise); the shareable list is the intersection of these with the
  // selected service's groups, so users can't share with a group they're not in.
  const { data: groupsData, isLoading: groupsLoading } = useGetGroupsQuery();
  const userAccessibleGroups = groupsData?.userAccessible ?? null;
  const [selectedAnalysisServiceId, setSelectedAnalysisServiceId] =
    useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Selected files for `file`-type analysis parameters, handled outside rjsf.
  const fileValues = useRef<Record<string, File | null>>({});
  // T0 (explosion/trigger time) as a UTC datetime string, handled outside rjsf
  // and converted to an MJD `trigger_time` on submit. Prefilled from the
  // source's associated G-event when the selected service accepts it.
  const [triggerTimeUtc, setTriggerTimeUtc] = useState<string>("");

  const groupLookUp: Record<string, any> = {};

  userAccessibleGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const analysisServiceLookUp = useMemo(() => {
    const lookUp: Record<string, any> = {};
    analysisServiceList?.forEach((analysisService: any) => {
      lookUp[analysisService.id] = analysisService;
    });
    return lookUp;
  }, [analysisServiceList]);

  // Whether the source can feed a service's required inputs. We can verify
  // photometry (it's fetched); other input types are assumed available. Only
  // reported false when photometry is loaded and known to be empty, so a
  // photometry-only fitter isn't offered on a source with no photometry.
  const serviceHasRequiredInputs = useCallback(
    (service: any): boolean => {
      const inputs = service?.input_data_types || [];
      // Only judge once the query has resolved (so we don't disable during
      // load); the endpoint yields null or [] for a source with no photometry.
      if (
        inputs.includes("photometry") &&
        photometryLoaded &&
        (photometry?.length ?? 0) === 0
      ) {
        return false;
      }
      return true;
    },
    [photometry, photometryLoaded],
  );

  // Build the rjsf schema in a memo so its reference is stable across renders.
  // The schema is dynamic (derived from the selected service's parameters); if
  // it were rebuilt every render, rjsf v6 would re-derive the uncontrolled form
  // each time and a `data-url` (file) field would infinite-loop ("Maximum
  // update depth exceeded"), resetting formData so the file never registers.
  // The static-schema galaxy/observation upload forms don't hit this.
  const {
    schema: AnalysisSelectionFormSchema,
    uiSchema: AnalysisSelectionFormUiSchema,
    fileKeys,
    acceptsTriggerTime,
  } = useMemo(() => {
    const service = analysisServiceLookUp[selectedAnalysisServiceId];
    const OptionalParameters: Record<string, any> = {};
    const OptionalUiSchema: Record<string, any> = {};
    const RequiredParameters: any[] = [];
    const collectedFileKeys: string[] = [];
    let acceptsTriggerTimeParam = false;
    if (service?.optional_analysis_parameters) {
      Object.keys(service.optional_analysis_parameters).forEach((key) => {
        // trigger_time gets a dedicated UTC datetime widget (with G-event
        // prefill) outside rjsf, so keep it out of the generated schema.
        if (key === "trigger_time") {
          acceptsTriggerTimeParam = true;
          return;
        }
        const params = service?.optional_analysis_parameters[key];
        if (Array.isArray(params)) {
          if (["True", "False"].every((val) => params.includes(val))) {
            OptionalParameters[key] = { type: "boolean" };
          } else {
            // Default to the first allowed value so the dropdown starts filled
            // (a required enum with no default forces the user to touch every
            // one before submit — painful for services with many parameters).
            OptionalParameters[key] = {
              type: "string",
              enum: params,
              default: params[0],
            };
            RequiredParameters.push(key);
          }
        } else if (typeof params === "object") {
          if (Array.isArray(params?.enum)) {
            // Object form of an enum: carries a description/title/units
            // alongside the choices (the bare-array form can't), defaulting to
            // the first value so the dropdown starts filled.
            OptionalParameters[key] = {
              type: "string",
              enum: params.enum,
              title: key,
              default: params.default ?? params.enum[0],
            };
          } else if (params?.type === "number") {
            OptionalParameters[key] = { type: "number", title: key };
          } else if (params?.type === "file") {
            // File params are handled outside rjsf (see the file inputs in the
            // render): rjsf v6's `data-url` FileWidget mis-handles files in this
            // form under MUI v7 (a render loop, and the file never reaches
            // formData). Collect the key and render a plain file input instead.
            collectedFileKeys.push(key);
            return;
          } else if (params?.type === "string") {
            OptionalParameters[key] = { type: "string", title: key };
          }
          if (OptionalParameters[key]) {
            if (params?.default !== undefined)
              OptionalParameters[key].default = params.default;
            if (params?.description)
              OptionalParameters[key].description = params.description;
            // Show units in the field title (e.g. "mejecta (Msun)").
            const title = params?.title || OptionalParameters[key].title || key;
            OptionalParameters[key].title = params?.units
              ? `${title} (${params.units})`
              : title;
            if (
              params?.required &&
              ["True", "true", "t"].includes(params.required)
            ) {
              RequiredParameters.push(key);
            }
          }
        } else {
          OptionalParameters[key] = {
            type: "string",
            enum: params,
            default: params?.[0],
          };
          RequiredParameters.push(key);
        }
      });
      if (
        (service?.input_data_types || []).includes("photometry") &&
        photometry
      ) {
        const filters: any[] = [];
        const instrumentLookUp: Record<string, any> = {};
        photometry.forEach((photometryData: any) => {
          const { filter, instrument_name, instrument_id } = photometryData;
          if (filter && !filters.includes(filter)) filters.push(filter);
          if (
            instrument_name &&
            instrument_id &&
            !instrumentLookUp[instrument_id]
          ) {
            instrumentLookUp[instrument_id] = instrument_name;
          }
        });
        const instrumentIds = Object.keys(instrumentLookUp).map(
          (instrument_id) => parseInt(instrument_id, 10),
        );
        OptionalParameters["input_filters_photometry_filters"] = {
          type: "array",
          title: "Filters to include (optional)",
          items: { type: "string", enum: filters },
          uniqueItems: true,
        };
        OptionalParameters["input_filters_photometry_instruments"] = {
          type: "array",
          title: "Instruments to include (optional)",
          items: { type: "integer", enum: instrumentIds },
          uniqueItems: true,
        };
        OptionalUiSchema["input_filters_photometry_instruments"] = {
          "ui:enumNames": instrumentIds.map((id) => instrumentLookUp[id]),
        };
      }
    }
    return {
      schema: {
        type: "object",
        properties: {
          ...OptionalParameters,
          show_parameters: {
            type: "boolean",
            title: "Show Parameters",
            description: "Whether to render the parameters of this analysis",
            default: true,
          },
          show_plots: {
            type: "boolean",
            title: "Show Plots",
            description: "Whether to render the plots of this analysis",
            default: true,
          },
          show_corner: {
            type: "boolean",
            title: "Show Corner",
            description: "Whether to render the corner of this analysis",
            default: true,
          },
        },
        required: ["show_parameters", "show_plots", "show_corner"].concat(
          RequiredParameters,
        ),
      },
      uiSchema: OptionalUiSchema,
      fileKeys: collectedFileKeys,
      acceptsTriggerTime: acceptsTriggerTimeParam,
    };
  }, [selectedAnalysisServiceId, analysisServiceLookUp, photometry]);

  // Seed the T0 field from the source's first associated G-event when the
  // selected service accepts a trigger time; clear it otherwise. Re-runs only
  // on service / association changes, so a user's manual edit is preserved.
  useEffect(() => {
    if (acceptsTriggerTime && associatedGCNs.length > 0) {
      setTriggerTimeUtc(
        dayjs.utc(associatedGCNs[0]).format("YYYY-MM-DDTHH:mm:ss"),
      );
    } else {
      setTriggerTimeUtc("");
    }
  }, [selectedAnalysisServiceId, acceptsTriggerTime, associatedGCNs]);

  useEffect(() => {
    if (selectedAnalysisServiceId == null && analysisServiceList.length > 0) {
      const firstEnabled =
        analysisServiceList.find(
          (s: any) =>
            s?.display_on_resource_dropdown !== false &&
            serviceHasRequiredInputs(s),
        ) || analysisServiceList[0];
      setSelectedAnalysisServiceId(firstEnabled?.id);
    }
  }, [
    analysisServiceList,
    selectedAnalysisServiceId,
    serviceHasRequiredInputs,
  ]);

  // Returning null while these are still in flight is indistinguishable from
  // having none, so the form looks permanently missing until they land.
  if (servicesLoading || groupsLoading) {
    return (
      <div className={classes.loading}>
        <CircularProgress size="1rem" />
        <Typography variant="body2" color="text.secondary">
          Loading analysis services...
        </Typography>
      </div>
    );
  }

  if (
    !userAccessibleGroups ||
    userAccessibleGroups.length === 0 ||
    !analysisServiceList ||
    analysisServiceList.length === 0
  ) {
    return (
      <Typography variant="body2" color="text.secondary">
        No analysis services are available to you.
      </Typography>
    );
  }

  if (!selectedAnalysisServiceId) {
    return null;
  }

  // Groups the results can be shared with: the selected service's groups that
  // the user can access (intersection).
  const accessibleGroupIds = new Set(
    userAccessibleGroups.map((g: any) => g.id),
  );
  const shareableGroups = (
    analysisServiceLookUp[selectedAnalysisServiceId]?.groups ?? []
  ).filter((g: any) => accessibleGroupIds.has(g.id));

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setIsSubmitting(true);
    const analysis_parameters = {
      ...formData,
    };

    // Merge the files selected via the plain file inputs (file params are not in
    // the rjsf schema) into the parameters as data URLs.
    await Promise.all(
      fileKeys.map(async (key: string) => {
        const file = fileValues.current[key];
        if (file) {
          analysis_parameters[key] = await new Promise<string>((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result as string);
            reader.readAsDataURL(file);
          });
        }
      }),
    );

    delete analysis_parameters.show_parameters;
    delete analysis_parameters.show_plots;
    delete analysis_parameters.show_corner;

    // T0 widget (handled outside rjsf): convert the UTC datetime to an MJD
    // trigger_time the fit backend understands. Blank = let the fit default it.
    if (acceptsTriggerTime && triggerTimeUtc.trim() !== "") {
      const mjd = utc_to_mjd(triggerTimeUtc.trim());
      if (mjd !== null) analysis_parameters.trigger_time = mjd;
    }

    const input_filters: Record<string, any> = {};
    if (
      (
        analysisServiceLookUp[selectedAnalysisServiceId]?.input_data_types || []
      ).includes("photometry")
    ) {
      input_filters["photometry"] = {};
      if (analysis_parameters.input_filters_photometry_filters) {
        delete analysis_parameters.input_filters_photometry_filters;
        input_filters["photometry"].filters =
          formData.input_filters_photometry_filters;
      }
      if (analysis_parameters.input_filters_photometry_instruments) {
        delete analysis_parameters.input_filters_photometry_instruments;
        input_filters["photometry"].instruments =
          formData.input_filters_photometry_instruments;
      }
    }

    const params: Record<string, any> = {
      show_parameters: formData.show_parameters,
      show_plots: formData.show_plots,
      show_corner: formData.show_corner,
      analysis_parameters,
      input_filters,
    };

    if (selectedGroupIds.length >= 0) {
      params["group_ids"] = selectedGroupIds;
    }
    try {
      await startAnalysis({
        id: obj_id,
        analysis_service_id: selectedAnalysisServiceId,
        formData: params,
      }).unwrap();
      const service = analysisServiceLookUp[selectedAnalysisServiceId];
      dispatch(
        showNotification(
          `Analysis started with ${service?.display_name || service?.name || "service"}.`,
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
    <div className={classes.container}>
      <div>
        <SearchableSelect
          options={uniqueAnalysisServiceList.filter(
            (s: any) => s?.display_on_resource_dropdown !== false,
          )}
          value={analysisServiceLookUp[selectedAnalysisServiceId] || null}
          onChange={(_e: any, value: any) =>
            setSelectedAnalysisServiceId(value?.id ?? null)
          }
          getOptionLabel={(option: any) =>
            option?.display_name || option?.name || ""
          }
          groupBy={(option: any) => option?.analysis_type || "other"}
          getOptionDisabled={(option: any) => !serviceHasRequiredInputs(option)}
          isOptionEqualToValue={(option: any, value: any) =>
            option?.id === value?.id
          }
          label="Start New Analysis"
          textFieldProps={{
            name: "analysisServiceSelect",
            "data-testid": "analysisServiceSelect",
          }}
          className={classes.Select}
        />
        {analysisServiceLookUp[selectedAnalysisServiceId]?.description && (
          <p className={classes.serviceDescription}>
            {analysisServiceLookUp[selectedAnalysisServiceId].description}
          </p>
        )}
      </div>
      <GroupShareSelect
        groupList={shareableGroups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
      <div data-testid="analysis-service-request-form">
        {fileKeys.map((key: string) => (
          <div key={key} className={classes.marginTop}>
            <InputLabel htmlFor={`root_${key}`}>{key}</InputLabel>
            <input
              type="file"
              id={`root_${key}`}
              onChange={(e) => {
                fileValues.current[key] = e.target.files?.[0] ?? null;
              }}
            />
          </div>
        ))}
        {acceptsTriggerTime && (
          <div className={classes.marginTop}>
            <InputLabel htmlFor="trigger_time_utc">
              T0 — explosion/trigger time (UTC)
            </InputLabel>
            {associatedGCNs.length > 1 && (
              <Select
                inputProps={{ MenuProps: { disableScrollLock: true } }}
                value={
                  associatedGCNs.find(
                    (d) =>
                      dayjs.utc(d).format("YYYY-MM-DDTHH:mm:ss") ===
                      triggerTimeUtc,
                  ) || ""
                }
                onChange={(e) =>
                  setTriggerTimeUtc(
                    dayjs
                      .utc(e.target.value as string)
                      .format("YYYY-MM-DDTHH:mm:ss"),
                  )
                }
                displayEmpty
                className={classes.Select}
                data-testid="triggerTimeGcnSelect"
              >
                <MenuItem value="">Pick an associated G-event…</MenuItem>
                {associatedGCNs.map((d) => (
                  <MenuItem value={d} key={d} className={classes.SelectItem}>
                    {d}
                  </MenuItem>
                ))}
              </Select>
            )}
            <input
              id="trigger_time_utc"
              data-testid="triggerTimeInput"
              type="text"
              style={{ width: "100%" }}
              value={triggerTimeUtc}
              placeholder="YYYY-MM-DDTHH:MM:SS UTC — blank = first detection − 2 d"
              onChange={(e) => setTriggerTimeUtc(e.target.value)}
            />
            <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>
              {triggerTimeUtc.trim() === ""
                ? "No T0 set — the fit defaults to first detection − 2 days."
                : utc_to_mjd(triggerTimeUtc.trim()) === null
                  ? "Unrecognized UTC datetime."
                  : `trigger_time = MJD ${utc_to_mjd(triggerTimeUtc.trim())!.toFixed(6)}${
                      associatedGCNs.length > 0
                        ? ` (from associated G-event${associatedGCNs.length > 1 ? "s" : ""})`
                        : ""
                    }`}
            </div>
          </div>
        )}
        <div>
          <Form
            key={selectedAnalysisServiceId}
            schema={AnalysisSelectionFormSchema as any}
            uiSchema={AnalysisSelectionFormUiSchema as any}
            validator={validator}
            onSubmit={handleSubmit as any}
          />
        </div>
        {isSubmitting && (
          <div className={classes.marginTop}>
            <CircularProgress />
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisForm;
