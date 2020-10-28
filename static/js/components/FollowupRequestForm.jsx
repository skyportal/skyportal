import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import Form from "@rjsf/material-ui";
import { makeStyles } from "@material-ui/core/styles";
import * as Actions from "../ducks/source";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

const useStyles = makeStyles(() => ({
  allocationSelect: {
    maxWidth: "100%",
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

  useEffect(() => {
    // Initialize the select
    setSelectedAllocationId(allocationList[0]?.id);
  }, [setSelectedAllocationId, allocationList]);

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

  const handleSubmit = ({ formData }) => {
    const json = {
      obj_id,
      allocation_id: selectedAllocationId,
      payload: formData,
    };
    dispatch(Actions.submitFollowupRequest(json));
  };

  return (
    <div>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        labelId="allocationSelectLabel"
        value={selectedAllocationId}
        onChange={handleSelectedAllocationChange}
        name="followupRequestAllocationSelect"
        className={classes.allocationSelect}
      >
        {allocationList.map((allocation) => (
          <MenuItem value={allocation.id} key={allocation.id}>
            {`${
              telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
            } / ${instLookUp[allocation.instrument_id].name} - ${
              groupLookUp[allocation.group_id].name
            } (PI ${allocation.pi})`}
          </MenuItem>
        ))}
      </Select>
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
        onSubmit={handleSubmit}
      />
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
