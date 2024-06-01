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
import PropTypes from "prop-types";
import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import GeoPropTypes from "geojson-prop-types";
import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";

import * as allocationActions from "../ducks/allocations";
import * as gcnEventActions from "../ducks/gcnEvent";
import * as instrumentActions from "../ducks/instrument";
import * as instrumentsActions from "../ducks/instruments";
import { planWithSameNameExists } from "../ducks/observationPlans";
import GroupShareSelect from "./group/GroupShareSelect";
import LocalizationPlot from "./localization/LocalizationPlot";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

import * as localizationActions from "../ducks/localization";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const projectionOptions = ["orthographic", "mollweide"];

const useStyles = makeStyles(() => ({
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

const FieldSelect = ({
  skymapInstrument,
  selectedFields,
  setSelectedFields,
}) => {
  const classes = useStyles();

  const fields = [];
  skymapInstrument?.fields?.forEach((field) => {
    fields.push(Number(field.field_id));
  });
  fields.sort((a, b) => a - b);

  const handleSelectedFieldChange = (e) => {
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

FieldSelect.propTypes = {
  skymapInstrument: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    type: PropTypes.string,
    band: PropTypes.string,
    fields: PropTypes.arrayOf(
      PropTypes.shape({
        ra: PropTypes.number,
        dec: PropTypes.number,
        id: PropTypes.number,
        contour: PropTypes.oneOfType([
          GeoPropTypes.FeatureCollection,
          PropTypes.shape({
            type: PropTypes.string,
            features: PropTypes.array, // eslint-disable-line react/forbid-prop-types
          }),
        ]),
        contour_summary: PropTypes.oneOfType([
          GeoPropTypes.FeatureCollection,
          PropTypes.shape({
            type: PropTypes.string,
            features: PropTypes.array, // eslint-disable-line react/forbid-prop-types
          }),
        ]),
      }),
    ),
  }),
  selectedFields: PropTypes.arrayOf(PropTypes.number).isRequired,
  setSelectedFields: PropTypes.func.isRequired,
};

FieldSelect.defaultProps = {
  skymapInstrument: null,
};

const ObservationPlanGlobe = ({
  gcnEvent,
  loc,
  skymapInstrument,
  selectedFields,
  setSelectedFields,
  selectedProjection,
  airmassValue = 2.5,
}) => {
  const displayOptions = [
    "localization",
    "sources",
    "galaxies",
    "instrument",
    "observations",
  ];
  const displayOptionsDefault = Object.fromEntries(
    displayOptions.map((x) => [x, false]),
  );
  displayOptionsDefault.localization = true;
  displayOptionsDefault.instrument = true;
  return !loc ||
    gcnEvent?.localizations?.length === 0 ||
    gcnEvent?.localizations?.find((l) => l.id === loc.id) === undefined ? (
    <CircularProgress />
  ) : (
    <LocalizationPlot
      localization={loc}
      instrument={skymapInstrument}
      options={displayOptionsDefault}
      selectedFields={selectedFields}
      setSelectedFields={setSelectedFields}
      projection={selectedProjection}
      airmass_threshold={airmassValue}
    />
  );
};

ObservationPlanGlobe.propTypes = {
  gcnEvent: PropTypes.shape({
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
      }),
    ),
  }).isRequired,
  loc: PropTypes.shape({
    id: PropTypes.number,
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
  }).isRequired,
  skymapInstrument: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    type: PropTypes.string,
    band: PropTypes.string,
    fields: PropTypes.arrayOf(
      PropTypes.shape({
        ra: PropTypes.number,
        dec: PropTypes.number,
        id: PropTypes.number,
        contour: PropTypes.oneOfType([
          GeoPropTypes.FeatureCollection,
          PropTypes.shape({
            type: PropTypes.string,
            features: PropTypes.array, // eslint-disable-line react/forbid-prop-types
          }),
        ]),
        contour_summary: PropTypes.oneOfType([
          GeoPropTypes.FeatureCollection,
          PropTypes.shape({
            type: PropTypes.string,
            features: PropTypes.array, // eslint-disable-line react/forbid-prop-types
          }),
        ]),
      }),
    ),
  }),
  selectedFields: PropTypes.arrayOf(PropTypes.number).isRequired,
  setSelectedFields: PropTypes.func.isRequired,
  selectedProjection: PropTypes.string,
  airmassValue: PropTypes.number,
};

ObservationPlanGlobe.defaultProps = {
  skymapInstrument: null,
  selectedProjection: "orthographic",
  airmassValue: 2.5,
};

const MyObjectFieldTemplate = (props) => {
  const { properties } = props;

  return (
    <Grid container spacing={2}>
      {properties.map((prop) => (
        <Grid item xs={4} key={prop.content.key}>
          {prop.content}
        </Grid>
      ))}
    </Grid>
  );
};

MyObjectFieldTemplate.propTypes = {
  properties: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      content: PropTypes.node,
    }),
  ).isRequired,
};

const ObservationPlanRequestForm = ({ dateobs }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const gcnEvent = useSelector((state) => state.gcnEvent);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationListApiObsplan } = useSelector(
    (state) => state.allocations,
  );
  const { useAMPM } = useSelector((state) => state.profile.preferences);

  const { obsplanLoc } = useSelector((state) => state.localization);

  const allGroups = useSelector((state) => state.groups.all);
  const [selectedAllocationId, setSelectedAllocationId] = useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [planQueues, setPlanQueues] = useState([]);
  const [skymapInstrument, setSkymapInstrument] = useState(null);
  const [selectedFields, setSelectedFields] = useState([]);
  const [multiPlansChecked, setMultiPlansChecked] = useState(false);

  const defaultAirmassTime = new Date(
    dayjs(gcnEvent?.dateobs).format("YYYY-MM-DDTHH:mm:ssZ"),
  );
  const [airmassTime, setAirmassTime] = useState(defaultAirmassTime);
  const [airmassValue, setAirmassValue] = useState(2.5);
  const [temporaryAirmassTime, setTemporaryAirmassTime] =
    useState(defaultAirmassTime);

  const [fetchingLocalization, setFetchingLocalization] = useState(false);
  const [
    fetchingInstrumentObsplanFormParams,
    setFetchingInstrumentObsplanFormParams,
  ] = useState(false);
  const [
    fetchingAllocationListApiObsplan,
    setFetchingAllocationListApiObsplan,
  ] = useState(false);

  const { instrumentList, instrumentObsplanFormParams } = useSelector(
    (state) => state.instruments,
  );

  const groupLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allGroups?.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allocationListApiObsplan?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const [selectedProjection, setSelectedProjection] = useState(
    projectionOptions[0],
  );

  const [selectedFormData, setSelectedFormData] = useState({});

  useEffect(() => {
    const fetchSkymapInstrument = async () => {
      setFetchingLocalization(true);
      dispatch(
        instrumentActions.fetchInstrumentSkymap(
          instLookUp[allocationLookUp[selectedAllocationId]?.instrument_id]?.id,
          obsplanLoc,
          airmassTime.toJSON(),
        ),
      ).then((response) => {
        setSkymapInstrument(response.data);
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
        (loc) => loc.id === obsplanLoc?.id,
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

  useEffect(() => {
    if (gcnEvent?.localizations?.length > 0 && selectedLocalizationId) {
      dispatch(
        localizationActions.fetchLocalization(
          gcnEvent?.dateobs,
          gcnEvent?.localizations.find(
            (loc) => loc.id === selectedLocalizationId,
          )?.localization_name,
          "obsplan",
        ),
      );
    }
  }, [selectedLocalizationId]);

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      if (
        !allocationListApiObsplan ||
        (allocationListApiObsplan?.length === 0 &&
          !fetchingAllocationListApiObsplan)
      ) {
        setFetchingAllocationListApiObsplan(true);
        dispatch(allocationActions.fetchAllocationsApiObsplan()).then(
          (response) => {
            if (response.status !== "success") {
              showNotification(
                "Error fetching allocations, please try refreshing the page",
                "error",
              );
              return;
            }
            const { data } = response;
            data.sort((a, b) => a.instrument_id - b.instrument_id);
            setSelectedAllocationId(data[0]?.id);
            setSelectedGroupIds([data[0]?.group_id]);
            setSelectedLocalizationId(gcnEvent.localizations[0]?.id);
            setFetchingAllocationListApiObsplan(false);
          },
        );
      } else if (
        allocationListApiObsplan?.length > 0 &&
        !selectedAllocationId
      ) {
        const sortedAllocationListApiObsplan = [...allocationListApiObsplan];
        sortedAllocationListApiObsplan.sort(
          (a, b) => a.instrument_id - b.instrument_id,
        );
        setSelectedAllocationId(sortedAllocationListApiObsplan[0]?.id);
        setSelectedGroupIds([sortedAllocationListApiObsplan[0]?.group_id]);
        setSelectedLocalizationId(gcnEvent.localizations[0]?.id);
      }
    };

    getAllocations();

    if (
      Object.keys(instrumentObsplanFormParams).length === 0 &&
      !fetchingInstrumentObsplanFormParams
    ) {
      setFetchingInstrumentObsplanFormParams(true);
      dispatch(instrumentsActions.fetchInstrumentObsplanForms()).then(() => {
        setFetchingInstrumentObsplanFormParams(false);
      });
    }

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    dispatch,
    gcnEvent,
    setSelectedAllocationId,
    setSelectedGroupIds,
    setSelectedLocalizationId,
  ]);

  // filter out the allocations that dont have "observaton_plan" in the types
  const filteredAllocationListApiObsplan = allocationListApiObsplan.filter(
    (allocation) => allocation.types.includes("observation_plan"),
  );

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationListApiObsplan is not
  // empty.
  if (
    allocationListApiObsplan.length === 0 ||
    !selectedAllocationId ||
    Object.keys(instrumentObsplanFormParams).length === 0
  ) {
    return <h3>No allocations with an observation plan API...</h3>;
  }

  if (filteredAllocationListApiObsplan.length === 0) {
    return (
      <h3>
        No allocations with an observation plan API and observation plan type
        set...
      </h3>
    );
  }

  if (
    !allGroups ||
    allGroups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0 ||
    dateobs !== gcnEvent?.dateobs
  ) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const handleSelectedAllocationChange = (e) => {
    setSelectedAllocationId(e.target.value);
    setSelectedGroupIds([allocationLookUp[e.target.value]?.group_id]);
  };

  const handleSelectedLocalizationChange = (e) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleQueueSubmit = async ({ formData }) => {
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
    dispatch(planWithSameNameExists(formData.queue_name)).then((response) => {
      if (response.status === "success" && response.data.exists === true) {
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
          gcnevent_id: gcnEvent.id,
          allocation_id: selectedAllocationId,
          localization_id: selectedLocalizationId,
          target_group_ids: selectedGroupIds,
          payload: formData,
        };
        setPlanQueues([...planQueues, json]);
      }
    });
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
      await dispatch(gcnEventActions.submitObservationPlanRequest(json));
      setPlanQueues([]);
    }
    setIsSubmitting(false);
  };

  const validate = (formData, errors) => {
    const instrumentId = allocationLookUp[selectedAllocationId]?.instrument_id;
    const instrument = instrumentList.find((inst) => inst.id === instrumentId);
    const instrumentsFilters = instrument?.filters;
    if (
      instrumentsFilters &&
      formData.filters !== undefined &&
      formData.filters !== ""
    ) {
      const formDataFilters = formData.filters.split(",");
      if (
        !formDataFilters.every((filter) => instrumentsFilters.includes(filter))
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

  const handleChange = (newValue) => {
    setTemporaryAirmassTime(new Date(newValue));
  };

  const setAirmass = () => {
    setAirmassTime(temporaryAirmassTime);
    dispatch(
      showNotification("Updating airmass tiles... patience please.", "info"),
    );
  };

  const exportData = (data) => {
    const jsonString = `data:text/json;chatset=utf-8,${encodeURIComponent(
      JSON.stringify(data.fields),
    )}`;
    const link = document.createElement("a");
    link.href = jsonString;
    link.download = `${dateobs.replaceAll(":", "-")}_fields_${data.name}.json`;
    link.click();
  };

  return (
    <Grid container spacing={4}>
      <Grid item xs={12} sm={12} md={6} lg={4}>
        <Grid container spacing={4} alignItems="center">
          <Grid item xs={12} sm={7} md={12}>
            <ObservationPlanGlobe
              gcnEvent={gcnEvent}
              loc={obsplanLoc}
              skymapInstrument={skymapInstrument}
              selectedFields={selectedFields}
              setSelectedFields={setSelectedFields}
              selectedProjection={selectedProjection}
              airmassValue={airmassValue}
            />
          </Grid>
          <Grid item xs={12} sm={5} md={12}>
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
              <InputLabel
                id="airmassTimeSelectLabel"
                style={{ marginBottom: "0.5rem" }}
              >
                Airmass Time
              </InputLabel>
              <Grid container spacing={1} alignItems="center">
                <Grid
                  item
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
                      showTodayButton={false}
                      ampm={useAMPM}
                      slotProps={{ textField: { variant: "outlined" } }}
                      style={{ minWidth: "100%" }}
                    />
                  </LocalizationProvider>
                  <TextField
                    id="airmassThreshold"
                    label="Threshold"
                    type="number"
                    value={airmassValue}
                    onChange={(e) => setAirmassValue(e.target.value)}
                    InputLabelProps={{
                      shrink: true,
                    }}
                    inputProps={{
                      step: 0.1,
                      min: 1.0,
                      max: 3.0,
                    }}
                    style={{ width: "100%" }}
                  />
                </Grid>
                <Grid item>
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
                    allocationLookUp[selectedAllocationId].instrument_id
                  ].telescope_id
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
      <Grid item xs={12} sm={12} md={6} lg={8}>
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
            {filteredAllocationListApiObsplan?.map((allocation) => (
              <MenuItem
                value={allocation.id}
                key={allocation.id}
                className={classes.SelectItem}
              >
                {`${
                  telLookUp[instLookUp[allocation.instrument_id].telescope_id]
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
            {gcnEvent.localizations?.map((localization) => (
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
                instrumentObsplanFormParams
                  ? instrumentObsplanFormParams[
                      allocationLookUp[selectedAllocationId].instrument_id
                    ]?.formSchema
                  : {}
              }
              formData={selectedFormData}
              onChange={({ formData }) => setSelectedFormData(formData)}
              validator={validator}
              uiSchema={
                instrumentObsplanFormParams
                  ? instrumentObsplanFormParams[
                      allocationLookUp[selectedAllocationId].instrument_id
                    ]?.uiSchema
                  : {}
              }
              templates={{ ObjectFieldTemplate: MyObjectFieldTemplate }}
              liveValidate
              customValidate={validate}
              onSubmit={handleQueueSubmit}
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
                instLookUp[allocationLookUp[plan.allocation_id].instrument_id]
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

ObservationPlanRequestForm.propTypes = {
  dateobs: PropTypes.string.isRequired,
  instrumentObsplanFormParams: PropTypes.shape({
    formSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    uiSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    implementedMethods: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
  }),
};

ObservationPlanRequestForm.defaultProps = {
  instrumentObsplanFormParams: {
    formSchema: {},
    uiSchema: {},
    implementedMethods: {},
  },
};

export default ObservationPlanRequestForm;
