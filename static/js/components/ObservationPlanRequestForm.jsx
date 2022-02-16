import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import Form from "@rjsf/material-ui";
import CircularProgress from "@material-ui/core/CircularProgress";
import { makeStyles } from "@material-ui/core/styles";
import * as gcnEventActions from "../ducks/gcnEvent";
import * as allocationActions from "../ducks/allocations";
import * as instrumentActions from "../ducks/instruments";
import GroupShareSelect from "./GroupShareSelect";

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
  allocationSelectItem: {
    whiteSpace: "break-spaces",
  },
  localizationSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

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

  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(
        allocationActions.fetchAllocations({
          apitype: "api_classname_obsplan",
        })
      );

      const { data } = result;
      setSelectedAllocationId(data[0]?.id);
      setSelectedGroupIds([data[0]?.group_id]);
      setSelectedLocalizationId(gcnevent.localizations[0]?.id);
    };

    getAllocations();

    dispatch(
      instrumentActions.fetchInstrumentForms({
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

  console.log("allocationList", allocationList);
  console.log("selectedAllocationId", selectedAllocationId);
  console.log("instrumentFormParams", instrumentFormParams);

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

  const handleSelectedAllocationChange = (e) => {
    setSelectedAllocationId(e.target.value);
  };

  const handleSelectedLocalizationChange = (e) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    const json = {
      gcnevent_id: gcnevent.id,
      allocation_id: selectedAllocationId,
      localization_id: selectedLocalizationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
    };
    await dispatch(gcnEventActions.submitObservationPlanRequest(json));
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

  console.log("instrumentFormParams", instrumentFormParams);
  console.log("allocationLookUp", allocationLookUp);
  console.log("selectedAllocationId", selectedAllocationId);

  return (
    <div className={classes.container}>
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
        value={selectedLocalizationId}
        onChange={handleSelectedLocalizationChange}
        name="followupRequestLocalizationSelect"
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
      <div data-testid="followup-request-form">
        <Form
          schema={
            instrumentFormParams[
              allocationLookUp[selectedAllocationId].instrument_id
            ].formSchema
          }
          uiSchema={
            instrumentFormParams[
              allocationLookUp[selectedAllocationId].instrument_id
            ].uiSchema
          }
          liveValidate
          validate={validate}
          onSubmit={handleSubmit}
          disabled={isSubmitting}
        />
        {isSubmitting && (
          <div className={classes.marginTop}>
            <CircularProgress />
          </div>
        )}
      </div>
    </div>
  );
};

ObservationPlanRequestForm.propTypes = {
  gcnevent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.string,
        localization_name: PropTypes.string,
      })
    ),
    id: PropTypes.number,
  }).isRequired,
  instrumentFormParams: PropTypes.shape({
    formSchema: PropTypes.objectOf(PropTypes.any),
    uiSchema: PropTypes.objectOf(PropTypes.any),
    implementedMethods: PropTypes.objectOf(PropTypes.any),
  }).isRequired,
};

export default ObservationPlanRequestForm;
