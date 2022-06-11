import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import PropTypes from "prop-types";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import Form from "@rjsf/material-ui";
import CircularProgress from "@material-ui/core/CircularProgress";
import { makeStyles } from "@material-ui/core/styles";
import { showNotification } from "baselayer/components/Notifications";
import GeoPropTypes from "geojson-prop-types";

import * as gcnEventActions from "../ducks/gcnEvent";
import * as allocationActions from "../ducks/allocations";
import * as instrumentsActions from "../ducks/instruments";
import * as instrumentActions from "../ducks/instrument";
import GroupShareSelect from "./GroupShareSelect";
import LocalizationPlot from "./LocalizationPlot";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

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
    width: "80%",
  },
  allocationSelectItem: {
    whiteSpace: "break-spaces",
  },
  localizationSelectItem: {
    whiteSpace: "break-spaces",
  },
  fieldsToUseSelectItem: {
    whiteSpace: "break-spaces",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const ObservationPlanGlobe = ({ loc, skymapInstrument }) => {
  const classes = useStyles();
  // dummy state for rerendering component
  const [dummy, setDummy] = useState();

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

  const fields = [];
  skymapInstrument?.fields?.forEach((field) => {
    fields.push(Number(field.id));
  });
  fields.sort((a, b) => a - b);

  const handleSelectedFieldChange = (e) => {
    const fields = e.target.value;
    skymapInstrument?.fields?.forEach((f) => {
      if (fields.includes(Number(f.id))) {
        f.selected = true;
      } else {
        f.selected = false;
      }
    });
    setDummy([]);
  };

  const clearSelectedFields = () => {
    skymapInstrument?.fields?.forEach((f) => {
      f.selected = false;
    });
    setDummy([]);
  };

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
              height={300}
              width={600}
              setDummy={setDummy}
            />
          </div>
        )}
      </div>

      <div>
        <InputLabel id="fieldsToUseSelectLabel">Fields to use</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="fieldsToSelectLabel"
          name="fieldsToUseSelect"
          className={classes.fieldsToUseSelect}
          multiple
          value={
            skymapInstrument?.fields
              ?.filter((f) => f?.selected)
              .map((f) => f?.field_id) || []
          }
          onChange={handleSelectedFieldChange}
        >
          {fields?.map((field) => (
            <MenuItem
              value={field}
              key={field}
              className={classes.fieldsToUseSelectItem}
            >
              {field}
            </MenuItem>
          ))}
        </Select>
        <Button
          id="clear-fieldsToUseSelect"
          size="small"
          color="secondary"
          onClick={() => clearSelectedFields()}
        >
          Clear Fields
        </Button>
      </div>
    </div>
  );
};

ObservationPlanGlobe.propTypes = {
  loc: PropTypes.shape({
    id: PropTypes.number,
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
  }).isRequired,
  instrument: PropTypes.shape({
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
  instrument: null,
};

const ObservationPlanRequestForm = ({ gcnevent }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationList } = useSelector((state) => state.allocations);

  const allGroups = useSelector((state) => state.groups.all);
  const [selectedAllocationId, setSelectedAllocationId] = useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [planQueues, setPlanQueues] = useState([]);
  const [skymapInstrument, setSkymapInstrument] = useState(null);

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
  allocationList?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const loc = gcnevent.localizations[0];

  useEffect(() => {
    const fetchSkymapInstrument = async () => {
      const response = await dispatch(
        instrumentActions.fetchInstrumentSkymap(
          instLookUp[allocationLookUp[selectedAllocationId]?.instrument_id]?.id,
          loc
        )
      );
      setSkymapInstrument(response.data);
    };
    fetchSkymapInstrument();
  }, [dispatch, setSkymapInstrument, loc, selectedAllocationId]);

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(
        allocationActions.fetchAllocations({
          apiType: "api_classname_obsplan",
        })
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
    dispatch(
      allocationActions.fetchAllocations({
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
  // render to update it, so it can be null even if allocationList is not
  // empty.
  if (
    allocationList.length === 0 ||
    !selectedAllocationId ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <h3>No robotic instruments available...</h3>;
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
    const selectedFields = skymapInstrument?.fields
      ?.filter((f) => f.selected)
      .map((f) => f.id);
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

    return errors;
  };

  return (
    <div className={classes.container}>
      <div>
        <ObservationPlanGlobe
          loc={gcnevent.localizations[0]}
          skymapInstrument={skymapInstrument}
        />
      </div>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        value={selectedAllocationId}
        onChange={handleSelectedAllocationChange}
        name="followupRequestAllocationSelect"
        className={classes.allocationSelect}
      >
        {allocationList?.map((allocation) => (
          <MenuItem
            value={allocation.id}
            key={allocation.id}
            className={classes.allocationSelectItem}
          >
            {`${
              telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
            } / ${instLookUp[allocation.instrument_id].name} - ${
              groupLookUp[allocation.group_id].name
            } (PI ${allocation.pi})`}
          </MenuItem>
        ))}
      </Select>
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
            className={classes.localizationSelectItem}
          >
            {`${localization.localization_name}`}
          </MenuItem>
        ))}
      </Select>
      <br />
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
                : []
            }
            uiSchema={
              instrumentFormParams
                ? instrumentFormParams[
                    allocationLookUp[selectedAllocationId].instrument_id
                  ]?.uiSchema
                : []
            }
            liveValidate
            validate={validate}
            onSubmit={handleQueueSubmit}
            disabled={isSubmitting}
          >
            <Button
              size="small"
              color="primary"
              type="submit"
              variant="outlined"
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
                .name
            }: ${plan.payload.queue_name}`}
            data-testid={`queueName_${plan.payload.queue_name}`}
          />
        ))}
      </div>
      <div>
        {planQueues.length !== 0 && (
          <Button
            size="small"
            color="primary"
            type="submit"
            variant="outlined"
            onClick={handleSubmit}
          >
            Generate Observation Plans
          </Button>
        )}
        {isSubmitting && (
          <div className={classes.marginTop}>
            <CircularProgress />
          </div>
        )}
      </div>
      <div>
        <Button
          href={`/api/localization/${selectedLocalizationId}/airmass/${
            instLookUp[allocationLookUp[selectedAllocationId].instrument_id]
              .telescope_id
          }`}
          download={`airmassChartRequest-${selectedAllocationId}`}
          size="small"
          color="primary"
          type="submit"
          variant="outlined"
          data-testid={`airmassChartRequest_${selectedAllocationId}`}
        >
          Airmass Chart
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
