import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { lazy, Suspense, useEffect, useState } from "react";

import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";

import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import { makeStyles } from "tss-react/mui";
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
  allocationSelect: {
    width: "100%",
  },
  localizationSelect: {
    width: "100%",
  },
  fieldsToUseSelect: {
    width: "75%",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
    "& > *": {
      marginTop: "1rem",
      marginBottom: "1rem",
    },
  },
  buttons: {
    display: "grid",
    gridGap: "1rem",
    gridTemplateColumns: "repeat(auto-fit, minmax(6.5rem, 1fr))",
    "& > button": {
      maxHeight: "4rem",
      // no space between 2 lines of text
      lineHeight: "1rem",
    },
    marginTop: "0.5rem",
    marginBottom: "1rem",
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
  const { classes } = useStyles();

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
    <div style={{ display: "flex", flexDirection: "column" }}>
      <InputLabel id="fieldsToUseSelectLabel">Fields to use</InputLabel>
      <div style={{ display: "flex", flexDirection: "row" }}>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="fieldsToSelectLabel"
          name="fieldsToUseSelect"
          className={classes.fieldsToUseSelect}
          multiple
          value={selectedFields || []}
          onChange={handleSelectedFieldChange}
        >
          {fields?.map((field) => (
            <MenuItem value={field} key={field} className={classes.SelectItem}>
              {field}
            </MenuItem>
          ))}
        </Select>
        <Button
          id="clear-fieldsToUseSelect"
          onClick={() => clearSelectedFields()}
          style={{ marginLeft: "1rem" }}
        >
          Clear all
        </Button>
        <Button id="all-fieldsToUseSelect" onClick={() => selectAllFields()}>
          Select all
        </Button>
      </div>
    </div>
  );
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
}: ObservationPlanGlobeProps) => {
  const displayOptionsDefault = {
    localization: true,
    sources: false,
    galaxies: false,
    instrument: true,
    observations: false,
  };
  return !loc ||
    gcnEvent?.localizations?.length === 0 ||
    gcnEvent?.localizations?.find((l: any) => l.id === loc.id) === undefined ? (
    <CircularProgress />
  ) : (
    <Suspense fallback={<CircularProgress />}>
      <LocalizationPlot
        localization={loc}
        instrument={skymapInstrument}
        options={displayOptionsDefault}
        selectedFields={selectedFields}
        setSelectedFields={setSelectedFields}
        projection={selectedProjection}
        airmass_threshold={airmassValue}
      />
    </Suspense>
  );
};

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
    return <h3>No allocations with an observation plan API...</h3>;
  }

  if (!filteredAllocationListApiObsplan.length) {
    return (
      <h3>
        No allocations with an observation plan API and observation plan type
        set...
      </h3>
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
      await submitObservationPlanRequest(json);
      setPlanQueues([]);
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
    const jsonString = `data:text/json;chatset=utf-8,${encodeURIComponent(
      JSON.stringify(data.fields),
    )}`;
    const link = document.createElement("a");
    link.href = jsonString;
    link.download = `${dateobs.replaceAll(":", "-")}_fields_${data.name}.json`;
    link.click();
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
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                marginTop: "0.5rem",
              }}
            >
              <InputLabel
                style={{ marginTop: "0.5rem", marginBottom: "0.25rem" }}
                id="projection"
              >
                Projection
              </InputLabel>
              <Select
                labelId="projection"
                id="projection"
                value={selectedProjection}
                onChange={(e) => setSelectedProjection(e.target.value)}
                style={{ width: "100%" }}
              >
                {projectionOptions.map((option) => (
                  <MenuItem value={option} key={option}>
                    {option}
                  </MenuItem>
                ))}
              </Select>
              {skymapInstrument?.name === "ZTF" && (
                <div>
                  {/* show an MUI select to pick primary & secondary, primary, or secondary for the grid */}
                  <InputLabel
                    style={{ marginTop: "0.5rem", marginBottom: "0.25rem" }}
                    id="grid"
                  >
                    Grid
                  </InputLabel>
                  <Select
                    labelId="grid"
                    id="grid"
                    value={grid}
                    onChange={(e) => setGrid(e.target.value)}
                    style={{ width: "100%" }}
                  >
                    {gridOptions.map((option) => (
                      <MenuItem value={option} key={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </Select>
                </div>
              )}
              <InputLabel
                id="airmassTimeSelectLabel"
                style={{ marginBottom: "0.5rem" }}
              >
                Airmass Time
              </InputLabel>
              <Grid
                container
                spacing={1}
                sx={{
                  alignItems: "center",
                }}
              >
                <Grid
                  style={{
                    display: "grid",
                    gridTemplateColumns: "3fr 1fr",
                    gap: "0.2rem",
                  }}
                >
                  <LocalizationProvider dateAdapter={AdapterDateFns}>
                    <DateTimePicker
                      value={temporaryAirmassTime}
                      onChange={(newValue) => handleChange(newValue)}
                      label="Time to compute airmass (UTC)"
                      {...({ showTodayButton: false } as any)}
                      ampm={useAMPM}
                      slotProps={{ textField: { variant: "outlined" } }}
                      {...({ style: { minWidth: "100%" } } as any)}
                    />
                  </LocalizationProvider>
                  <TextField
                    id="airmassThreshold"
                    label="Threshold"
                    type="number"
                    value={airmassValue}
                    onChange={(e) => setAirmassValue(e.target.value)}
                    slotProps={{
                      inputLabel: {
                        shrink: true,
                      },
                      htmlInput: {
                        step: 0.1,
                        min: 1.0,
                        max: 3.0,
                      },
                    }}
                    style={{ width: "100%" }}
                  />
                </Grid>
                <Grid>
                  <Button id="setAirmassSelect" onClick={() => setAirmass()}>
                    Update airmass calculation
                  </Button>
                </Grid>
              </Grid>
            </div>
            <div className={classes.buttons}>
              <Button
                secondary
                href={`/api/localization/${selectedLocalizationId}/observability`}
                download={`observabilityChartRequest-${selectedLocalizationId}`}
                size="small"
                type="submit"
                data-testid={`observabilityChartRequest_${selectedLocalizationId}`}
              >
                Observability Chart
              </Button>
              <Button
                secondary
                href={`/api/localization/${selectedLocalizationId}/airmass/${
                  instLookUp[
                    allocationLookUp[selectedAllocationId]?.instrument_id
                  ]?.telescope_id
                }`}
                download={`airmassChartRequest-${selectedAllocationId}`}
                size="small"
                type="submit"
                data-testid={`airmassChartRequest_${selectedAllocationId}`}
              >
                Airmass Chart
              </Button>
              <Button
                secondary
                href={`/api/localization/${selectedLocalizationId}/worldmap`}
                download={`worldmapChartRequest-${selectedLocalizationId}`}
                size="small"
                type="submit"
                data-testid={`worldmapChartRequest_${selectedLocalizationId}`}
              >
                World Map Chart
              </Button>
              <Button
                secondary
                onClick={() => exportData(skymapInstrument)}
                size="small"
                type="submit"
                data-testid="exportSkymapInstrument"
                disabled={
                  !skymapInstrument || skymapInstrument?.fields?.length === 0
                }
              >
                Download Fields
              </Button>
            </div>
          </Grid>
        </Grid>
      </Grid>
      <Grid size={{ xs: 12, sm: 12, md: 6, lg: 8 }}>
        <div>
          <FieldSelect
            selectedFields={selectedFields}
            setSelectedFields={setSelectedFields}
            skymapInstrument={skymapInstrument}
          />
          <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
          <Select
            inputProps={{ MenuProps: { disableScrollLock: true } }}
            labelId="allocationSelectLabel"
            value={selectedAllocationId}
            onChange={handleSelectedAllocationChange}
            name="followupRequestAllocationSelect"
            className={classes.allocationSelect}
          >
            {filteredAllocationListApiObsplan?.map((allocation: any) => (
              <MenuItem
                value={allocation.id}
                key={allocation.id}
                className={classes.SelectItem}
              >
                {`${
                  telLookUp[instLookUp[allocation.instrument_id]?.telescope_id]
                    ?.name
                } / ${instLookUp[allocation.instrument_id]?.name} - ${
                  groupLookUp[allocation.group_id]?.name
                } (PI ${allocation.pi})`}
              </MenuItem>
            ))}
          </Select>
        </div>
        <div>
          <InputLabel id="allocationSelectLabel">Localization</InputLabel>
          <Select
            inputProps={{ MenuProps: { disableScrollLock: true } }}
            labelId="localizationSelectLabel"
            value={selectedLocalizationId || ""}
            onChange={handleSelectedLocalizationChange}
            name="observationPlanRequestLocalizationSelect"
            className={classes.localizationSelect}
          >
            {gcnEvent.localizations?.map((localization: any) => (
              <MenuItem
                value={localization.id}
                key={localization.id}
                className={classes.SelectItem}
              >
                {`Skymap: ${localization.localization_name} / Created: ${localization.created_at}`}
              </MenuItem>
            ))}
          </Select>
        </div>
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
