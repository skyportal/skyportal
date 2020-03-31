import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import PropTypes from 'prop-types';

import * as Actions from '../ducks/source';


const FollowupRequestForm = ({ source }) => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const [formState, setFormState] = useState({
    source_id: source.id,
    instrument_id: "",
    start_date: "",
    end_date: "",
    priority: ""
  });

  const handleInputChange = (e) => {
    const newState = {};
    newState[e.target.name] = e.target.type === 'checkbox' ?
      e.target.checked : e.target.value;
    setFormState({
      ...formState,
      ...newState
    });
  };

  const handleSubmit = () => {
    dispatch(Actions.submitFollowupRequest(formState));
  };

  return (
    <div>
      <h3>
        Submit new follow-up request
      </h3>
      <div>
        <select
          name="instrument_id"
          value={formState.instrument_id}
          onChange={handleInputChange}
        >
          <option value="null">
            Select Instrument
          </option>
          {
            instrumentList.map((instrument) => (
              <option value={instrument.id} key={instrument.id}>
                {instrument.name}
              </option>
            ))
          }
        </select>
      </div>
      <div>
        <label>
          Start Date
        </label>
        <input
          type="text"
          name="start_date"
          value={formState.start_date}
          onChange={handleInputChange}
          size="6"
        />
        &nbsp;&nbsp;
        <label>
          End Date
        </label>
        <input
          type="text"
          name="end_date"
          value={formState.end_date}
          onChange={handleInputChange}
          size="6"
        />
      </div>
      <div>
        <select name="priority" value={formState.priority} onChange={handleInputChange}>
          <option value="null">
            Select Priority
          </option>
          {
            ["1", "2", "3", "4", "5"].map((val) => (
              <option value={val} key={val}>
                {val}
              </option>
            ))
          }
        </select>
      </div>
      <button type="button" onClick={handleSubmit}>
        Submit
      </button>
    </div>
  );
};

FollowupRequestForm.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string
  }).isRequired
};

export default FollowupRequestForm;
