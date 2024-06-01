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

import * as earthquakeActions from "../../ducks/earthquake";
import * as mmadetectorActions from "../../ducks/mmadetector";
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
    marginBottom: "1rem",
    "& > *": {
      marginTop: "1rem",
      marginBottom: "1rem",
    },
  },
}));

const EarthquakePredictionForm = ({ earthquake }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { mmadetectorList } = useSelector((state) => state.mmadetectors);
  const allGroups = useSelector((state) => state.groups.all);
  const [selectedMMADetectorId, setSelectedMMADetectorId] = useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const groupLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allGroups?.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const mmadetectorLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  mmadetectorList?.forEach((mmadetector) => {
    mmadetectorLookUp[mmadetector.id] = mmadetector;
  });

  useEffect(() => {
    const getMMADetectors = async () => {
      // Wait for the mmadetectors to update before setting
      // the new default form fields, so that the mmadetectors list can
      // update

      const result = await dispatch(mmadetectorActions.fetchMMADetectors());

      const { data } = result;
      setSelectedMMADetectorId(data[0]?.id);
    };

    getMMADetectors();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedMMADetectorId, earthquake]);

  if (!allGroups || allGroups.length === 0 || mmadetectorList.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    await dispatch(
      earthquakeActions.submitPrediction(
        earthquake.event_id,
        selectedMMADetectorId,
        formData,
      ),
    );
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

  const handleSelectedMMADetectorChange = (e) => {
    setSelectedMMADetectorId(e.target.value);
  };

  const EarthquakePredictionFormSchema = {
    type: "object",
    properties: {
      modelName: {
        type: "string",
        oneOf: [
          { enum: ["model1"], title: "Model 1" },
          { enum: ["model2"], title: "Model 2" },
          { enum: ["model3"], title: "Model 3" },
        ],
        default: "model1",
        title: "Model",
      },
    },
    required: ["modelName"],
  };

  return (
    <div className={classes.container}>
      <div>
        <InputLabel id="mmadetectorSelectLabel">MMADetector</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="mmadetectorSelectLabel"
          value={selectedMMADetectorId || ""}
          onChange={handleSelectedMMADetectorChange}
          name="earthquakeMMADetectorSelect"
          className={classes.mmadetectorSelect}
        >
          {mmadetectorList?.map((mmadetector) => (
            <MenuItem
              value={mmadetector.id}
              key={mmadetector.id}
              className={classes.mmadetectorSelectItem}
            >
              {`${mmadetector.name}`}
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
            schema={EarthquakePredictionFormSchema}
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

EarthquakePredictionForm.propTypes = {
  earthquake: PropTypes.shape({
    event_id: PropTypes.string,
    id: PropTypes.number,
  }).isRequired,
};

export default EarthquakePredictionForm;
