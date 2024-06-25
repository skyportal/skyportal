import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";

import { showNotification } from "baselayer/components/Notifications";
import * as defaultSurveyEfficienciesActions from "../../ducks/default_survey_efficiencies";

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
  Select: {
    width: "100%",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const NewDefaultSurveyEfficiency = ({ onClose }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [selectedObservationPlanId, setSelectedObservationPlanId] =
    useState(null);
  const { defaultObservationPlanList } = useSelector(
    (state) => state.default_observation_plans,
  );

  const observationPlanLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  defaultObservationPlanList?.forEach((default_observation_plan) => {
    observationPlanLookUp[default_observation_plan.id] =
      default_observation_plan;
  });

  const handleSelectedObservationPlanChange = (e) => {
    setSelectedObservationPlanId(e.target.value);
  };

  const handleSubmit = async ({ formData }) => {
    const optionalInjectionParameters = {};
    if (Object.keys(formData).includes("log10_E0")) {
      optionalInjectionParameters.log10_E0 = formData.log10_E0;
      delete formData.log10_E0;
    }
    if (Object.keys(formData).includes("mag")) {
      optionalInjectionParameters.mag = formData.mag;
      delete formData.mag;
    }
    if (Object.keys(formData).includes("dmag")) {
      optionalInjectionParameters.dmag = formData.dmag;
      delete formData.dmag;
    }

    formData.optionalInjectionParameters = JSON.stringify(
      optionalInjectionParameters,
    );

    const json = {
      default_observationplan_request_id: selectedObservationPlanId,
      payload: formData,
    };
    const result = await dispatch(
      defaultSurveyEfficienciesActions.submitDefaultSurveyEfficiency(json),
    );
    if (result.status === "success") {
      dispatch(showNotification("New Default Survey Efficiency saved"));
      dispatch(
        defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies(),
      );
      if (typeof onClose === "function") {
        onClose();
      }
    }
  };

  const SimSurveySelectionFormSchema = {
    type: "object",
    properties: {
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
    required: ["localizationCumprob", "modelName"],
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
          {
            properties: {
              modelName: {
                enum: ["kilonova"],
              },
            },
          },
        ],
      },
    },
  };

  const validate = (formData, errors) => {
    const maxInjections = 100000;
    if (formData.numberInjections > maxInjections) {
      errors.numberInjections.addError(
        `Number of injections must be less than ${maxInjections}`,
      );
    }

    return errors;
  };

  return (
    <div className={classes.container}>
      <InputLabel id="observationPlanSelectLabel">Default Plan</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="observationPlanSelectLabel"
        value={selectedObservationPlanId || ""}
        onChange={handleSelectedObservationPlanChange}
        name="observationPlanSelect"
        className={classes.Select}
      >
        {defaultObservationPlanList?.map((default_observation_plan) => (
          <MenuItem
            value={default_observation_plan.id}
            key={default_observation_plan.id}
            className={classes.SelectItem}
          >
            {`${default_observation_plan.default_plan_name}`}
          </MenuItem>
        ))}
      </Select>
      <br />
      <div data-testid="observationplan-request-form">
        <div>
          <Form
            schema={SimSurveySelectionFormSchema}
            validator={validator}
            onSubmit={handleSubmit}
            // eslint-disable-next-line react/jsx-no-bind
            customValidate={validate}
            liveValidate
          />
        </div>
      </div>
    </div>
  );
};

NewDefaultSurveyEfficiency.propTypes = {
  onClose: PropTypes.func,
};

NewDefaultSurveyEfficiency.defaultProps = {
  onClose: null,
};

export default NewDefaultSurveyEfficiency;
