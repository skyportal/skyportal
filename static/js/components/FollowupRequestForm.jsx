import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import Form from "@rjsf/material-ui";
import * as Actions from "../ducks/source";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

const FollowupRequestForm = ({
  obj_id,
  instrumentList,
  instrumentFormParams,
}) => {
  const dispatch = useDispatch();
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationList } = useSelector((state) => state.allocations);
  const allGroups = useSelector((state) => state.groups.all);
  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [selectedAllocationId, setSelectedAllocationId] = useState(null);
  const allocationInstIds = allocationList.map((a) => a.instrument_id);
  const allocatedInstrumentIds = Object.keys(instrumentFormParams)
    .map((k) => parseInt(k, 10))
    .filter((i) => allocationInstIds.includes(i));

  // initialize the form fields that are outside of the schema
  // this needs to be in a useEffect hook so that the state setters are not
  // called unconditionally, resulting in an infinite re-render loop
  useEffect(() => {
    const defaultInstId = allocatedInstrumentIds[0];
    const defaultAllocationId = allocationList.filter(
      (allocation) => allocation.instrument_id === defaultInstId
    )[0]?.id;
    setSelectedInstrumentId(defaultInstId);
    setSelectedAllocationId(defaultAllocationId);
  }, [allocationList, instrumentFormParams, allocatedInstrumentIds]);

  if (allocatedInstrumentIds.length === 0) {
    return <h3>No robotic instruments available...</h3>;
  }

  if (allGroups.length === 0 || telescopeList.length === 0) {
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

  const instIDToName = {};
  const instLookUp = {};
  instrumentList.forEach((instrumentObj) => {
    instIDToName[instrumentObj.id] = instrumentObj.name;
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSelectedInstrumentChange = (e) => {
    setSelectedInstrumentId(e.target.value);
  };

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
      <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
      <Select
        labelId="instrumentSelectLabel"
        value={selectedInstrumentId}
        onChange={handleSelectedInstrumentChange}
        name="followupRequestInstrumentSelect"
      >
        {allocatedInstrumentIds
          .filter((instrument_id) =>
            Object.keys(telLookUp)
              .map((t) => parseInt(t, 10))
              .includes(instLookUp[instrument_id].telescope_id)
          )
          .map((instrument_id) => (
            <MenuItem value={instrument_id} key={instrument_id}>
              {instLookUp[instrument_id].name}
            </MenuItem>
          ))}
      </Select>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      {selectedInstrumentId && (
        <Select
          labelId="allocationSelectLabel"
          value={selectedAllocationId}
          onChange={handleSelectedAllocationChange}
          name="followupRequestAllocationSelect"
        >
          {allocationList
            .filter(
              (allocation) => allocation.instrument_id === selectedInstrumentId
            )
            .map((allocation) => (
              <MenuItem value={allocation.id} key={allocation.id}>
                {`${groupLookUp[allocation.group_id].name} (PI ${
                  allocation.pi
                })`}
              </MenuItem>
            ))}
        </Select>
      )}
      {selectedInstrumentId && selectedAllocationId && (
        <Form
          schema={instrumentFormParams[selectedInstrumentId].formSchema}
          uiSchema={instrumentFormParams[selectedInstrumentId].uiSchema}
          onSubmit={handleSubmit}
        />
      )}
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
