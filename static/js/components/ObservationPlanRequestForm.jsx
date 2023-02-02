import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import PropTypes from "prop-types";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
import { showNotification } from "baselayer/components/Notifications";
import GeoPropTypes from "geojson-prop-types";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import Button from "./Button";

import * as gcnEventActions from "../ducks/gcnEvent";
import * as allocationActions from "../ducks/allocations";
import * as instrumentsActions from "../ducks/instruments";
import * as instrumentActions from "../ducks/instrument";
import GroupShareSelect from "./GroupShareSelect";
import LocalizationPlot from "./LocalizationPlot";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

dayjs.extend(relativeTime);
dayjs.extend(utc);

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
}));

const FieldSelect = ({
  skymapInstrument,
  selectedFields,
  setSelectedFields,
}) => {
  const classes = useStyles();

  const fields = [];
  skymapInstrument?.fields?.forEach((field) => {
    fields.push(Number(field.id));
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
      })
    ),
  }),
  selectedFields: PropTypes.arrayOf(PropTypes.number).isRequired,
  setSelectedFields: PropTypes.func.isRequired,
};

FieldSelect.defaultProps = {
  skymapInstrument: null,
};

const ObservationPlanGlobe = ({
  loc,
  skymapInstrument,
  selectedFields,
  setSelectedFields,
}) => {
  const [rotation, setRotation] = useState([0, 0]);

  const displayOptions = [
    "localization",
    "sources",
    "galaxies",
    "instrument",
    "observations",
  ];
  const displayOptionsDefault = Object.fromEntries(
    displayOptions.map((x) => [x, false])
  );
  displayOptionsDefault.localization = true;
  displayOptionsDefault.instrument = true;

  return (
    <div>
      <div>
        {!loc ? (
          <div>
            <CircularProgress />
          </div>
        ) : (
          <div>
            <LocalizationPlot
              loc={loc}
              instrument={skymapInstrument}
              options={displayOptionsDefault}
              rotation={rotation}
              setRotation={setRotation}
              selectedFields={selectedFields}
              setSelectedFields={setSelectedFields}
            />
          </div>
        )}
      </div>
      <FieldSelect
        selectedFields={selectedFields}
        setSelectedFields={setSelectedFields}
        skymapInstrument={skymapInstrument}
      />
    </div>
  );
};

ObservationPlanGlobe.propTypes = {
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
      })
    ),
  }),
  selectedFields: PropTypes.arrayOf(PropTypes.number).isRequired,
  setSelectedFields: PropTypes.func.isRequired,
};

ObservationPlanGlobe.defaultProps = {
  skymapInstrument: null,
};

const ObservationPlanRequestForm = ({ gcnevent }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationListApiObsplan } = useSelector(
    (state) => state.allocations
  );
  const observationPlanNames = useSelector((state) => state.observationPlans);
  const { useAMPM } = useSelector((state) => state.profile.preferences);

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
    dayjs(gcnevent?.dateobs).format("YYYY-MM-DDTHH:mm:ssZ")
  );
  const [airmassTime, setAirmassTime] = useState(defaultAirmassTime);
  const [temporaryAirmassTime, setTemporaryAirmassTime] =
    useState(defaultAirmassTime);

  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
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

  const loc = gcnevent?.localizations[0];

  useEffect(() => {
    const fetchSkymapInstrument = async () => {
      const response = await dispatch(
        instrumentActions.fetchInstrumentSkymap(
          instLookUp[allocationLookUp[selectedAllocationId]?.instrument_id]?.id,
          loc,
          airmassTime.toJSON()
        )
      );
      setSkymapInstrument(response.data);
    };
    if (
      instLookUp[allocationLookUp[selectedAllocationId]?.instrument_id]?.id &&
      gcnevent &&
      airmassTime
    ) {
      fetchSkymapInstrument();
    }
  }, [dispatch, setSkymapInstrument, loc, selectedAllocationId, airmassTime]);

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(
        allocationActions.fetchAllocationsApiObsplan()
      );

      const { data } = result;
      setSelectedAllocationId(data[0]?.id);
      setSelectedGroupIds([data[0]?.group_id]);
      setSelectedLocalizationId(gcnevent.localizations[0]?.id);
    };

    getAllocations();

    dispatch(
      instrumentsActions.fetchInstrumentForms({
        apiType: "api_classname_obsplan",
      })
    );

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    dispatch,
    setSelectedAllocationId,
    setSelectedGroupIds,
    setSelectedLocalizationId,
  ]);

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationListApiObsplan is not
  // empty.
  if (
    allocationListApiObsplan.length === 0 ||
    !selectedAllocationId ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <h3>No allocations with an observation plan API...</h3>;
  }

  if (
    !allGroups ||
    allGroups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0
  ) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const handleSelectedAllocationChange = (e) => {
    setSelectedAllocationId(e.target.value);
  };

  const handleSelectedLocalizationChange = (e) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleQueueSubmit = async ({ formData }) => {
    if (selectedFields.length > 0) {
      formData.field_ids = selectedFields;
    }
    const json = {
      gcnevent_id: gcnevent.id,
      allocation_id: selectedAllocationId,
      localization_id: selectedLocalizationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
    };
    setPlanQueues([...planQueues, json]);
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
    if (
      formData.start_date &&
      formData.end_date &&
      formData.start_date > formData.end_date
    ) {
      errors.start_date.addError("Start Date must come before End Date");
    }

    if (observationPlanNames.includes(formData.queue_name)) {
      errors.queue_name.addError("Need a unique plan name");
    }

    return errors;
  };

  const handleChange = (newValue) => {
    setTemporaryAirmassTime(new Date(newValue));
  };

  const setAirmass = () => {
    setAirmassTime(temporaryAirmassTime);
    dispatch(
      showNotification("Updating airmass tiles... patience please.", "info")
    );
  };

  return (
    <div className={classes.container}>
      <div>
        <ObservationPlanGlobe
          loc={gcnevent.localizations[0]}
          skymapInstrument={skymapInstrument}
          selectedFields={selectedFields}
          setSelectedFields={setSelectedFields}
        />
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        <InputLabel id="airmassTimeSelectLabel">Airmass Time</InputLabel>
        <div style={{ display: "flex", flexDirection: "row" }}>
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DateTimePicker
              value={temporaryAirmassTime}
              onChange={(newValue) => handleChange(newValue)}
              label="Time to compute airmass (UTC)"
              showTodayButton={false}
              ampm={useAMPM}
              renderInput={(params) => (
                /* eslint-disable-next-line react/jsx-props-no-spreading */
                <TextField id="airmassTimePicker" {...params} />
              )}
            />
          </LocalizationProvider>
          <Button
            id="setAirmassSelect"
            onClick={() => setAirmass()}
            style={{ marginLeft: "1rem" }}
          >
            Update airmass calculation
          </Button>
        </div>
      </div>
      <div>
        <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="allocationSelectLabel"
          value={selectedAllocationId}
          onChange={handleSelectedAllocationChange}
          name="followupRequestAllocationSelect"
          className={classes.allocationSelect}
        >
          {allocationListApiObsplan?.map((allocation) => (
            <MenuItem
              value={allocation.id}
              key={allocation.id}
              className={classes.SelectItem}
            >
              {`${
                telLookUp[instLookUp[allocation.instrument_id].telescope_id]
                  .name
              } / ${instLookUp[allocation.instrument_id].name} - ${
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
          {gcnevent.localizations?.map((localization) => (
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
        <div>
          <Form
            schema={
              instrumentFormParams
                ? instrumentFormParams[
                    allocationLookUp[selectedAllocationId].instrument_id
                  ]?.formSchema
                : {}
            }
            validator={validator}
            uiSchema={
              instrumentFormParams
                ? instrumentFormParams[
                    allocationLookUp[selectedAllocationId].instrument_id
                  ]?.uiSchema
                : {}
            }
            liveValidate
            customValidate={validate}
            onSubmit={handleQueueSubmit}
            disabled={isSubmitting}
          >
            <Button secondary size="small" type="submit">
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
                .name
            }: ${plan.payload.queue_name}`}
            data-testid={`queueName_${plan.payload.queue_name}`}
          />
        ))}
      </div>
      <div>
        {planQueues.length !== 0 && (
          <>
            <Button secondary size="small" type="submit" onClick={handleSubmit}>
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
      <div>
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
            instLookUp[allocationLookUp[selectedAllocationId].instrument_id]
              .telescope_id
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
      </div>
    </div>
  );
};

ObservationPlanRequestForm.propTypes = {
  gcnevent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      })
    ),
    id: PropTypes.number,
  }).isRequired,
  instrumentFormParams: PropTypes.shape({
    formSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    uiSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    implementedMethods: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
  }),
};

ObservationPlanRequestForm.defaultProps = {
  instrumentFormParams: {
    formSchema: {},
    uiSchema: {},
    implementedMethods: {},
  },
};

export default ObservationPlanRequestForm;
