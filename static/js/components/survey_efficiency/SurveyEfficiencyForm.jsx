import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { showNotification } from "baselayer/components/Notifications";

import * as surveyEfficiencyObservationsActions from "../../ducks/survey_efficiency_observations";
import * as surveyEfficiencyObservationPlansActions from "../../ducks/survey_efficiency_observation_plans";
import * as instrumentsActions from "../../ducks/instruments";
import GroupShareSelect from "../group/GroupShareSelect";

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
  },
}));

const SurveyEfficiencyForm = ({ gcnevent, observationplanRequest }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationList } = useSelector((state) => state.allocations);

  const allGroups = useSelector((state) => state.groups.all);
  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { instrumentList } = useSelector((state) => state.instruments);

  const instrumentsWithSensitivities = (instrumentList || []).filter(
    (i) => i.sensitivity_data,
  );

  const defaultStartDate = dayjs(gcnevent?.dateobs).format(
    "YYYY-MM-DDTHH:mm:ssZ",
  );
  const defaultEndDate = dayjs(gcnevent?.dateobs)
    .add(7, "day")
    .format("YYYY-MM-DDTHH:mm:ssZ");

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

  const locLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  gcnevent.localizations?.forEach((loc) => {
    locLookUp[loc.id] = loc;
  });

  useEffect(() => {
    const getInstruments = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the instruments list can
      // update

      const result = await dispatch(instrumentsActions.fetchInstruments());

      const { data } = result;
      const newInstrumentsWithSensitivities = data.filter(
        (i) => i.sensitivity_data,
      );
      setSelectedInstrumentId(newInstrumentsWithSensitivities[0]?.id);
      setSelectedLocalizationId(gcnevent.localizations[0]?.id);
    };
    if (!instrumentList || instrumentList.length === 0) {
      getInstruments();
    } else {
      setSelectedInstrumentId(instrumentsWithSensitivities[0]?.id);
      setSelectedLocalizationId(gcnevent?.localizations[0]?.id);
    }

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedInstrumentId, setSelectedLocalizationId, gcnevent]);

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

  const handleSelectedLocalizationChange = (e) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    if (!selectedLocalizationId) {
      dispatch(showNotification("No localization selected", "error"));
      setIsSubmitting(false);
      return;
    }
    if (!selectedInstrumentId) {
      dispatch(showNotification("No instrument selected", "error"));
      setIsSubmitting(false);
      return;
    }
    formData.startDate = formData.startDate
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.endDate = formData.endDate
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.localizationDateobs = locLookUp[selectedLocalizationId].dateobs;
    formData.localizationName = locLookUp[selectedLocalizationId].name;

    const optionalInjectionParameters = {};
    if (
      Object.keys(formData).includes("log10_E0") &&
      formData.log10_E0 !== undefined
    ) {
      optionalInjectionParameters.log10_E0 = formData.log10_E0;
      delete formData.log10_E0;
    }
    if (Object.keys(formData).includes("mag") && formData.mag !== undefined) {
      optionalInjectionParameters.mag = formData.mag;
      delete formData.mag;
    }
    if (Object.keys(formData).includes("dmag") && formData.dmag !== undefined) {
      optionalInjectionParameters.dmag = formData.dmag;
      delete formData.dmag;
    }

    formData.optionalInjectionParameters = JSON.stringify(
      optionalInjectionParameters,
    );

    if (!observationplanRequest) {
      await dispatch(
        surveyEfficiencyObservationsActions.submitSurveyEfficiencyObservations(
          selectedInstrumentId,
          formData,
        ),
      );
    } else {
      await dispatch(
        surveyEfficiencyObservationPlansActions.submitSurveyEfficiencyObservationPlan(
          observationplanRequest.id,
          formData,
        ),
      );
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

    const maxInjections = 100000;
    if (formData.numberInjections > maxInjections) {
      errors.numberInjections.addError(
        `Number of injections must be less than ${maxInjections}`,
      );
    }

    return errors;
  };

  const handleSelectedInstrumentChange = (e) => {
    setSelectedInstrumentId(e.target.value);
  };

  const SimSurveySelectionFormSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        format: "date-time",
        title: "Start Date",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "End Date",
        default: defaultEndDate,
      },
      localizationCumprob: {
        type: "number",
        title: "Cumulative Probability",
        default: 0.95,
      },
      numberInjections: {
        type: "integer",
        title: "Number of Injections",
        default: 1000,
      },
      numberDetections: {
        type: "integer",
        title: "Number of Detections",
        default: 1,
      },
      detectionThreshold: {
        type: "number",
        title: "Detection Threshold [sigma]",
        default: 5.0,
      },
      minimumPhase: {
        type: "number",
        title: "Minimum Phase [days]",
        default: 0.0,
      },
      maximumPhase: {
        type: "number",
        title: "Maximum Phase [days]",
        default: 3.0,
      },
      modelName: {
        type: "string",
        oneOf: [
          { enum: ["kilonova"], title: "Kilonova [GW170817-like]" },
          { enum: ["afterglow"], title: "GRB Afterglow" },
          { enum: ["linear"], title: "Linear model" },
        ],
        default: "kilonova",
        title: "Model",
      },
    },
    required: ["startDate", "endDate", "localizationCumprob"],
    dependencies: {
      modelName: {
        oneOf: [
          {
            properties: {
              modelName: {
                enum: ["afterglow"],
              },
              log10_E0: {
                type: "number",
                title: "log10(Energy [erg/s])",
                default: 53.0,
              },
            },
          },
          {
            properties: {
              modelName: {
                enum: ["linear"],
              },
              mag: {
                type: "number",
                title: "Peak magnitude",
                default: -16.0,
              },
              dmag: {
                type: "number",
                title: "Magnitude decay [1/day]",
                default: 1.0,
              },
            },
          },
        ],
      },
    },
  };

  return (
    <div className={classes.container}>
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
              {`${localization.localization_name}`}
            </MenuItem>
          ))}
        </Select>
      </div>
      <div>
        <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="instrumentSelectLabel"
          value={selectedInstrumentId || ""}
          onChange={handleSelectedInstrumentChange}
          name="gcnPageInstrumentSelect"
          className={classes.instrumentSelect}
        >
          {instrumentsWithSensitivities?.map((instrument) => (
            <MenuItem
              value={instrument.id}
              key={instrument.id}
              className={classes.instrumentSelectItem}
            >
              {`${telLookUp[instrument.telescope_id]?.name} / ${
                instrument.name
              }`}
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
            schema={SimSurveySelectionFormSchema}
            validator={validator}
            onSubmit={handleSubmit}
            // eslint-disable-next-line react/jsx-no-bind
            customValidate={validate}
            disabled={isSubmitting}
            liveValidate
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

SurveyEfficiencyForm.propTypes = {
  gcnevent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      }),
    ),
    id: PropTypes.number,
  }).isRequired,
  observationplanRequest: PropTypes.shape({
    id: PropTypes.number,
  }),
};

SurveyEfficiencyForm.defaultProps = {
  observationplanRequest: null,
};

export default SurveyEfficiencyForm;
