import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { lazy, Suspense, useEffect, useState } from "react";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";

import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import { makeStyles } from "tss-react/mui";
import Typography from "@mui/material/Typography";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { skipToken } from "@reduxjs/toolkit/query";

import { useAppDispatch } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import Button from "../Button";

import { useGetAllocationsApiObsplanQuery } from "../../ducks/allocations";
import {
  useGetGcnEventQuery,
  useSubmitObservationPlanRequestMutation,
} from "../../ducks/gcnEvent";
import { useLazyGetInstrumentSkymapQuery } from "../../ducks/instrument";
import {
  useGetInstrumentsQuery,
  useGetInstrumentObsplanFormsQuery,
} from "../../ducks/instruments";
import { useLazyGetPlanWithSameNameExistsQuery } from "../../ducks/observationPlans";
import { useGetLocalizationQuery } from "../../ducks/localization";
import { download } from "../../utils/download";
import GroupShareSelect from "../group/GroupShareSelect";
const LocalizationPlot = lazy(() => import("../localization/LocalizationPlot"));

dayjs.extend(relativeTime);
dayjs.extend(utc);

const projectionOptions = ["orthographic", "mollweide"];
const gridOptions = ["primary & secondary", "primary", "secondary"];

const useStyles = makeStyles()(() => ({
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
  container: {
    width: "99%",
    marginBottom: "1rem",
    "& > *": {
      marginTop: "1rem",
      marginBottom: "1rem",
    },
  },
}));

interface FieldSelectProps {
  skymapInstrument?: any;
  selectedFields: number[];
  setSelectedFields: (...a: any[]) => void;
}

const FieldSelect = ({
  skymapInstrument = null,
  selectedFields,
  setSelectedFields,
}: FieldSelectProps) => {
  const fields: number[] = [];
  skymapInstrument?.fields?.forEach((field: any) => {
    fields.push(Number(field.field_id));
  });
  fields.sort((a, b) => a - b);

  const handleSelectedFieldChange = (e: any) => {
    setSelectedFields(e.target.value);
  };

  const clearSelectedFields = () => {
    setSelectedFields([]);
  };

  const selectAllFields = () => {
    setSelectedFields(fields);
  };

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <FormControl size="small" sx={{ flex: 1 }}>
        <InputLabel id="fieldsToUseSelectLabel">Fields to use</InputLabel>
        <Select
          label="Fields to use"
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="fieldsToUseSelectLabel"
          name="fieldsToUseSelect"
          multiple
          value={selectedFields || []}
          onChange={handleSelectedFieldChange}
        >
          {fields?.map((field) => (
            <MenuItem value={field} key={field}>
              {field}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <Button
        id="clear-fieldsToUseSelect"
        size="small"
        onClick={() => clearSelectedFields()}
      >
        Clear all
      </Button>
      <Button
        id="all-fieldsToUseSelect"
        size="small"
        onClick={() => selectAllFields()}
      >
        Select all
      </Button>
    </Box>
  );
};

const PLOT_LAYERS = {
  localization: true,
  instrument: true,
  sun_moon: true,
};

interface ObservationPlanGlobeProps {
  gcnEvent: any;
  loc: any;
  skymapInstrument?: any;
  selectedFields: number[];
  setSelectedFields: (...a: any[]) => void;
  selectedProjection?: string | undefined;
  airmassValue?: number | undefined;
}

const ObservationPlanGlobe = ({
  gcnEvent,
  loc,
  skymapInstrument = null,
  selectedFields,
  setSelectedFields,
  selectedProjection = "orthographic",
  airmassValue = 2.5,
}: ObservationPlanGlobeProps) =>
  gcnEvent?.localizations?.some((l: any) => l.id === loc?.id) ? (
    <Suspense fallback={<CircularProgress />}>
      <LocalizationPlot
        localization={loc}
        instrument={skymapInstrument}
        options={PLOT_LAYERS}
        selectedFields={selectedFields}
        setSelectedFields={setSelectedFields}
        projection={selectedProjection}
        airmass_threshold={airmassValue}
      />
    </Suspense>
  ) : (
    <CircularProgress />
  );

const MyObjectFieldTemplate = (props: any) => {
  const { properties } = props;

  return (
    <Grid container spacing={2}>
      {properties.map((prop: any) => (
        <Grid size={4} key={prop.content.key}>
          {prop.content}
        </Grid>
      ))}
    </Grid>
  );
};

interface ObservationPlanRequestFormProps {
  dateobs: string;
  instrumentObsplanFormParams?: Record<string, any>;
}

const ObservationPlanRequestForm = ({
  dateobs,
}: ObservationPlanRequestFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [fetchInstrumentSkymap] = useLazyGetInstrumentSkymapQuery();
  const [fetchPlanWithSameNameExists] = useLazyGetPlanWithSameNameExistsQuery();

  const { data: gcnEvent } = useGetGcnEventQuery(dateobs ?? skipToken) as {
    data: any;
  };
  const [submitObservationPlanRequest] =
    useSubmitObservationPlanRequestMutation();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationListApiObsplan = [] } =
    useGetAllocationsApiObsplanQuery();
  const { useAMPM } =
    useGetProfileQuery().data?.preferences ?? ({} as { useAMPM?: boolean });

  const allGroups = useGetGroupsQuery().data?.all ?? null;
  const [selectedAllocationId, setSelectedAllocationId] = useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [selectedLocalizationId, setSelectedLocalizationId] =
    useState<any>(null);

  const selectedLocalizationName = gcnEvent?.localizations?.find(
    (loc: any) => loc.id === selectedLocalizationId,
  )?.localization_name;
  const { data: obsplanLoc } = useGetLocalizationQuery(
    {
      dateobs: gcnEvent?.dateobs,
      localization_name: selectedLocalizationName,
    },
    {
      skip:
        !gcnEvent?.dateobs ||
        !selectedLocalizationName ||
        !(gcnEvent?.localizations?.length > 0),
    },
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [planQueues, setPlanQueues] = useState<any[]>([]);
  const [skymapInstrument, setSkymapInstrument] = useState<any>(null);
  const [selectedFields, setSelectedFields] = useState<number[]>([]);
  const [multiPlansChecked, setMultiPlansChecked] = useState(false);

  const defaultAirmassTime = new Date(
    dayjs(gcnEvent?.dateobs).format("YYYY-MM-DDTHH:mm:ssZ"),
  );
  const [airmassTime, setAirmassTime] = useState(defaultAirmassTime);
  const [airmassValue, setAirmassValue] = useState<any>(2.5);
  const [temporaryAirmassTime, setTemporaryAirmassTime] =
    useState(defaultAirmassTime);

  const [fetchingLocalization, setFetchingLocalization] = useState(false);

  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentObsplanFormParams = {} } =
    useGetInstrumentObsplanFormsQuery();

  const groupLookUp: Record<string, any> = {};

  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp: Record<string, any> = {};

  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp: Record<string, any> = {};

  allocationListApiObsplan?.forEach((allocation: any) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp: Record<string, any> = {};

  instrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const [selectedProjection, setSelectedProjection] = useState(
    projectionOptions[0],
  );

  const [selectedFormData, setSelectedFormData] = useState<any>({});

  useEffect(() => {
    const fetchSkymapInstrument = async () => {
      if (!obsplanLoc) return;
      setFetchingLocalization(true);
      fetchInstrumentSkymap({
        id: instLookUp[allocationLookUp[selectedAllocationId]?.instrument_id]
          ?.id,
        localization: obsplanLoc as {
          dateobs: string;
          localization_name: string;
        },
        airmassTime: airmassTime.toJSON(),
      })
        .unwrap()
        .then((response: any) => {
          setSkymapInstrument(response);
        })
        .catch(() => {})
        .finally(() => {
          setFetchingLocalization(false);
        });
    };
    if (
      gcnEvent &&
      instrumentList?.length > 0 &&
      selectedAllocationId &&
      airmassTime &&
      obsplanLoc &&
      instLookUp[allocationLookUp[selectedAllocationId]?.instrument_id]?.id &&
      gcnEvent?.localizations?.length > 0 &&
      (gcnEvent?.localizations || []).find(
        (loc: any) => loc.id === obsplanLoc?.id,
      ) &&
      fetchingLocalization === false
    ) {
      fetchSkymapInstrument();
    }
  }, [
    dispatch,
    setSkymapInstrument,
    obsplanLoc,
    selectedAllocationId,
    airmassTime,
    instrumentList,
  ]);

  const [grid, setGrid] = useState("primary & secondary");
  const [downloadAnchor, setDownloadAnchor] = useState<HTMLElement | null>(
    null,
  );

  useEffect(() => {
    if (allocationListApiObsplan?.length > 0 && !selectedAllocationId) {
      const sortedAllocationListApiObsplan = [...allocationListApiObsplan];
      sortedAllocationListApiObsplan.sort(
        (a, b) => a["instrument_id"] - b["instrument_id"],
      );
      setSelectedAllocationId(sortedAllocationListApiObsplan[0]?.["id"]);
      setSelectedGroupIds([sortedAllocationListApiObsplan[0]?.["group_id"]]);
      setSelectedLocalizationId(gcnEvent?.localizations?.[0]?.id);
    }

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    dispatch,
    gcnEvent,
    allocationListApiObsplan,
    setSelectedAllocationId,
    setSelectedGroupIds,
    setSelectedLocalizationId,
  ]);

  // filter out the allocations that dont have "observaton_plan" in the types
  const filteredAllocationListApiObsplan = allocationListApiObsplan.filter(
    (allocation: any) => allocation.types.includes("observation_plan"),
  );

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationListApiObsplan is not
  // empty.
  if (!allocationListApiObsplan.length) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No allocations with an observation plan API
      </Typography>
    );
  }

  if (!filteredAllocationListApiObsplan.length) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No allocations with an observation plan API and the observation plan
        type
      </Typography>
    );
  }

  if (
    !selectedAllocationId ||
    !Object.keys(instrumentObsplanFormParams).length ||
    !allGroups?.length ||
    !telescopeList.length ||
    !instrumentList.length ||
    dateobs !== gcnEvent?.dateobs
  )
    return <CircularProgress />;

  const handleSelectedAllocationChange = (e: any) => {
    setSelectedAllocationId(e.target.value);
    setSelectedGroupIds([allocationLookUp[e.target.value]?.group_id]);
  };

  const handleSelectedLocalizationChange = (e: any) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleQueueSubmit = async ({ formData }: { formData: any }) => {
    // if there is already a plan with the same name in the queue, show an error
    const planQueueExists = planQueues.find(
      (planQueue) => planQueue.payload.queue_name === formData.queue_name,
    );
    if (planQueueExists) {
      dispatch(
        showNotification(
          "An observation plan with the same name already exists in the queue. Use another name",
          "warning",
        ),
      );
      return;
    }
    // if there is already a plan with the same name in the DB, show an error
    try {
      const response = await fetchPlanWithSameNameExists(
        formData.queue_name,
      ).unwrap();
      if (response.exists === true) {
        dispatch(
          showNotification(
            "An observation plan with the same name already exists. Use another name",
            "warning",
          ),
        );
      } else {
        if (selectedFields.length > 0) {
          formData.field_ids = selectedFields;
        }
        const json = {
          gcnevent_id: gcnEvent?.id,
          allocation_id: selectedAllocationId,
          localization_id: selectedLocalizationId,
          target_group_ids: selectedGroupIds,
          payload: formData,
        };
        setPlanQueues([...planQueues, json]);
      }
    } catch {
      // notification handled by baseQuery
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    if (planQueues.length === 0) {
      dispatch(showNotification("Need at least one queue to submit.", "error"));
    } else {
      const json = {
        observation_plans: planQueues,
        combine_plans: multiPlansChecked,
      };
      const result = await submitObservationPlanRequest(json);
      // the server creates none of the plans if any is rejected
      if (!("error" in result)) setPlanQueues([]);
    }
    setIsSubmitting(false);
  };

  const validate = (formData: any, errors: any) => {
    const instrumentId = allocationLookUp[selectedAllocationId]?.instrument_id;
    const instrument = instrumentList.find(
      (inst: any) => inst.id === instrumentId,
    );
    const instrumentsFilters = instrument?.["filters"];
    if (
      instrumentsFilters &&
      formData.filters !== undefined &&
      formData.filters !== ""
    ) {
      const formDataFilters = formData.filters.split(",");
      if (
        !formDataFilters.every((filter: any) =>
          instrumentsFilters.includes(filter),
        )
      ) {
        errors.filters.addError(
          `Filters must be a subset of the instrument filters: ${instrumentsFilters}`,
        );
      }
    }
    if (
      formData.start_date &&
      formData.end_date &&
      formData.start_date > formData.end_date
    ) {
      errors.start_date.addError("Start Date must come before End Date");
    }

    return errors;
  };

  const handleChange = (newValue: any) => {
    setTemporaryAirmassTime(new Date(newValue));
  };

  const setAirmass = () => {
    setAirmassTime(temporaryAirmassTime);
    dispatch(
      showNotification("Updating airmass tiles... patience please.", "info"),
    );
  };

  const exportData = (data: any) => {
    download(
      JSON.stringify(data.fields),
      "text/json",
      `${dateobs.replaceAll(":", "-")}_fields_${data.name}.json`,
    );
  };

  const filteredFieldsSkyMapInstrument = (skymap_instrument: any) => {
    // if skymap_instrument.name !== ZTF, just return it as is
    if (skymap_instrument?.name !== "ZTF" || grid === "primary & secondary") {
      return skymap_instrument;
    }
    if (skymap_instrument?.name === "ZTF" && grid === "primary") {
      // remove fields where field_id >= 881
      return {
        ...skymap_instrument,
        fields: skymap_instrument.fields.filter(
          (field: any) => field.field_id < 881,
        ),
      };
    }
    if (skymap_instrument?.name === "ZTF" && grid === "secondary") {
      // remove fields where field_id < 881
      return {
        ...skymap_instrument,
        fields: skymap_instrument.fields.filter(
          (field: any) => field.field_id >= 881,
        ),
      };
    }
    return skymap_instrument;
  };

  return (
    <Grid container spacing={4}>
      <Grid size={{ xs: 12, sm: 12, md: 6, lg: 4 }}>
        <Grid
          container
          spacing={4}
          sx={{
            alignItems: "center",
          }}
        >
          <Grid size={{ xs: 12, sm: 7, md: 12 }}>
            <ObservationPlanGlobe
              gcnEvent={gcnEvent}
              loc={obsplanLoc}
              skymapInstrument={filteredFieldsSkyMapInstrument(
                skymapInstrument,
              )}
              selectedFields={selectedFields}
              setSelectedFields={setSelectedFields}
              selectedProjection={selectedProjection}
              airmassValue={airmassValue}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 5, md: 12 }}>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Box sx={{ display: "flex", gap: 1 }}>
                <TextField
                  select
                  size="small"
                  label="Projection"
                  value={selectedProjection}
                  onChange={(e) => setSelectedProjection(e.target.value)}
                  fullWidth
                >
                  {projectionOptions.map((option) => (
                    <MenuItem value={option} key={option}>
                      {option}
                    </MenuItem>
                  ))}
                </TextField>
                {skymapInstrument?.name === "ZTF" && (
                  <TextField
                    select
                    size="small"
                    label="Grid"
                    value={grid}
                    onChange={(e) => setGrid(e.target.value)}
                    fullWidth
                  >
                    {gridOptions.map((option) => (
                      <MenuItem value={option} key={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              </Box>
              <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <DateTimePicker
                    value={temporaryAirmassTime}
                    onChange={(newValue) => handleChange(newValue)}
                    label="Airmass time (UTC)"
                    ampm={useAMPM}
                    slotProps={{
                      textField: { size: "small", sx: { flex: 1 } },
                    }}
                  />
                </LocalizationProvider>
                <TextField
                  id="airmassThreshold"
                  size="small"
                  label="Threshold"
                  type="number"
                  value={airmassValue}
                  onChange={(e) => setAirmassValue(e.target.value)}
                  slotProps={{
                    htmlInput: { step: 0.1, min: 1.0, max: 3.0 },
                  }}
                  sx={{ width: 100 }}
                />
                <Button
                  id="setAirmassSelect"
                  size="small"
                  onClick={() => setAirmass()}
                >
                  Update
                </Button>
              </Box>
              <Box>
                <Button
                  size="small"
                  onClick={(e: any) => setDownloadAnchor(e.currentTarget)}
                >
                  Download
                </Button>
                <Menu
                  anchorEl={downloadAnchor}
                  open={Boolean(downloadAnchor)}
                  onClose={() => setDownloadAnchor(null)}
                  onClick={() => setDownloadAnchor(null)}
                >
                  <MenuItem
                    component="a"
                    href={`/api/localization/${selectedLocalizationId}/observability`}
                    download={`observabilityChartRequest-${selectedLocalizationId}`}
                    data-testid={`observabilityChartRequest_${selectedLocalizationId}`}
                  >
                    Observability chart
                  </MenuItem>
                  <MenuItem
                    component="a"
                    href={`/api/localization/${selectedLocalizationId}/airmass/${
                      instLookUp[
                        allocationLookUp[selectedAllocationId]?.instrument_id
                      ]?.telescope_id
                    }`}
                    download={`airmassChartRequest-${selectedAllocationId}`}
                    data-testid={`airmassChartRequest_${selectedAllocationId}`}
                  >
                    Airmass chart
                  </MenuItem>
                  <MenuItem
                    component="a"
                    href={`/api/localization/${selectedLocalizationId}/worldmap`}
                    download={`worldmapChartRequest-${selectedLocalizationId}`}
                    data-testid={`worldmapChartRequest_${selectedLocalizationId}`}
                  >
                    World map chart
                  </MenuItem>
                  <MenuItem
                    onClick={() => exportData(skymapInstrument)}
                    data-testid="exportSkymapInstrument"
                    disabled={
                      !skymapInstrument ||
                      skymapInstrument?.fields?.length === 0
                    }
                  >
                    Fields
                  </MenuItem>
                </Menu>
              </Box>
            </Stack>
          </Grid>
        </Grid>
      </Grid>
      <Grid size={{ xs: 12, sm: 12, md: 6, lg: 8 }}>
        <Stack spacing={2} sx={{ mt: 1, mb: 2 }}>
          <FieldSelect
            selectedFields={selectedFields}
            setSelectedFields={setSelectedFields}
            skymapInstrument={skymapInstrument}
          />
          <FormControl size="small" fullWidth>
            <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
            <Select
              label="Allocation"
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="allocationSelectLabel"
              value={selectedAllocationId}
              onChange={handleSelectedAllocationChange}
              name="followupRequestAllocationSelect"
            >
              {filteredAllocationListApiObsplan?.map((allocation: any) => (
                <MenuItem value={allocation.id} key={allocation.id}>
                  {`${
                    telLookUp[
                      instLookUp[allocation.instrument_id]?.telescope_id
                    ]?.name
                  } / ${instLookUp[allocation.instrument_id]?.name} - ${
                    groupLookUp[allocation.group_id]?.name
                  } (PI ${allocation.pi})`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" fullWidth>
            <InputLabel id="localizationSelectLabel">Localization</InputLabel>
            <Select
              label="Localization"
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="localizationSelectLabel"
              value={selectedLocalizationId || ""}
              onChange={handleSelectedLocalizationChange}
              name="observationPlanRequestLocalizationSelect"
            >
              {gcnEvent.localizations?.map((localization: any) => (
                <MenuItem value={localization.id} key={localization.id}>
                  {`Skymap: ${localization.localization_name} / Created: ${localization.created_at}`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>
        <GroupShareSelect
          groupList={allGroups}
          setGroupIDs={setSelectedGroupIds}
          groupIDs={selectedGroupIds}
        />
        <div data-testid="observationplan-request-form">
          <div style={{ marginTop: "1rem" }}>
            <Form
              schema={
                (instrumentObsplanFormParams
                  ? instrumentObsplanFormParams[
                      allocationLookUp[selectedAllocationId]?.instrument_id
                    ]?.formSchema
                  : {}) as any
              }
              formData={selectedFormData}
              onChange={({ formData }) => setSelectedFormData(formData)}
              validator={validator}
              uiSchema={
                instrumentObsplanFormParams
                  ? instrumentObsplanFormParams[
                      allocationLookUp[selectedAllocationId]?.instrument_id
                    ]?.uiSchema
                  : {}
              }
              templates={{ ObjectFieldTemplate: MyObjectFieldTemplate }}
              liveValidate
              customValidate={validate as any}
              onSubmit={handleQueueSubmit as any}
              disabled={isSubmitting}
            >
              <Button
                secondary
                size="small"
                type="submit"
                style={{ marginTop: "1rem" }}
              >
                Add to Queue
              </Button>
            </Form>
          </div>
          {isSubmitting && (
            <div className={classes.marginTop}>
              <CircularProgress />
            </div>
          )}
        </div>
        <div>
          {planQueues?.map((plan) => (
            <Chip
              key={plan.payload.queue_name}
              label={`${
                instLookUp[allocationLookUp[plan.allocation_id]?.instrument_id]
                  ?.name
              }: ${plan.payload.queue_name}`}
              data-testid={`queueName_${plan.payload.queue_name}`}
              onDelete={() => {
                setPlanQueues(
                  planQueues.filter(
                    (queue) =>
                      queue.payload.queue_name !== plan.payload.queue_name,
                  ),
                );
              }}
            />
          ))}
        </div>
        <div>
          {planQueues.length !== 0 && (
            <>
              <Button
                secondary
                size="small"
                type="submit"
                onClick={handleSubmit}
              >
                Generate Observation Plans
              </Button>
              <FormControlLabel
                label="Combine plans"
                control={
                  <Checkbox
                    onChange={(event) =>
                      setMultiPlansChecked(event.target.checked)
                    }
                    checked={multiPlansChecked}
                    data-testid="combinedPlansCheckBox"
                  />
                }
              />
            </>
          )}
          {isSubmitting && (
            <div className={classes.marginTop}>
              <CircularProgress />
            </div>
          )}
        </div>
      </Grid>
    </Grid>
  );
};

export default ObservationPlanRequestForm;
