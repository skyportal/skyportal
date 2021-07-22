import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import Form from "@rjsf/material-ui";
import CircularProgress from "@material-ui/core/CircularProgress";
import { makeStyles } from "@material-ui/core/styles";
import * as Actions from "../ducks/source";
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
  allocationSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const FollowupRequestForm = ({
  obj_id,
  instrumentList,
  instrumentFormParams,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationList } = useSelector((state) => state.allocations);
  const allGroups = useSelector((state) => state.groups.all);
  const [selectedAllocationId, setSelectedAllocationId] = useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // Initialize the select
    setSelectedAllocationId(allocationList[0]?.id);
    setSelectedGroupIds([allocationList[0]?.group_id]);
  }, [setSelectedAllocationId, allocationList, setSelectedGroupIds]);

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
    return <h3>Loading...</h3>;
  }

  const groupLookUp = {};
  allGroups.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp = {};
  telescopeList.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp = {};
  allocationList.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};
  instrumentList.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSelectedAllocationChange = (e) => {
    setSelectedAllocationId(e.target.value);
  };

  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    const json = {
      obj_id,
      allocation_id: selectedAllocationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
    };
    await dispatch(Actions.submitFollowupRequest(json));
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
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        value={selectedAllocationId}
        onChange={handleSelectedAllocationChange}
        name="followupRequestAllocationSelect"
        className={classes.allocationSelect}
      >
        {allocationList.map((allocation) => (
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

FollowupRequestForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  instrumentList: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    })
  ).isRequired,
  instrumentFormParams: PropTypes.shape({
    formSchema: PropTypes.objectOf(PropTypes.any),
    uiSchema: PropTypes.objectOf(PropTypes.any),
    implementedMethods: PropTypes.objectOf(PropTypes.any),
  }).isRequired,
};

export default FollowupRequestForm;
