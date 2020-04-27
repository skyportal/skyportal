import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import PropTypes from 'prop-types';
import DatePicker from 'react-datepicker';

import { showNotification } from 'baselayer/components/Notifications';
import * as Actions from '../ducks/source';

import 'react-datepicker/dist/react-datepicker-cssmodules.css';


const FollowupRequestForm = ({ source_id, action, instrumentList, instrumentObsParams, followupRequest = null, title = "Submit new follow-up request", afterSubmit = null }) => {
  const dispatch = useDispatch();
  const obsParams = instrumentObsParams; // Shorten to reduce line length below

  const instIDToName = {};
  instrumentList.forEach((instrumentObj) => {
    instIDToName[instrumentObj.id] = instrumentObj.name;
  });

  const initialFormState = followupRequest !== null ? {
    source_id: followupRequest.source_id,
    instrument_id: followupRequest.instrument_id,
    instrument_name: instIDToName[followupRequest.instrument_id],
    start_date: new Date(followupRequest.start_date),
    end_date: new Date(followupRequest.end_date),
    filters: followupRequest.filters,
    exposure_time: followupRequest.exposure_time,
    priority: followupRequest.priority,
    editable: followupRequest.editable
  } : {
    source_id,
    instrument_id: "",
    instrument_name: "",
    start_date: new Date(),
    end_date: new Date(),
    filters: [],
    exposure_time: "",
    priority: ""
  };
  const [formState, setFormState] = useState({ ...initialFormState });

  const handleInputChange = (e) => {
    let newState = { ...formState };
    newState.filters = [...formState.filters];

    if (e.target.name.startsWith("filterCheckbox_")) {
      const filter = e.target.name.split("filterCheckbox_")[1];
      if (e.target.checked) {
        newState.filters.push(filter);
      } else {
        newState.filters.splice(newState.filters.indexOf(filter), 1);
      }
    } else {
      newState[e.target.name] = e.target.type === 'checkbox' ?
        e.target.checked : e.target.value;

      if (e.target.name === "instrument_id") {
        // Reset form state using newly selected instrument ID & name
        newState = {
          ...initialFormState,
          instrument_id: e.target.value,
          instrument_name: instIDToName[e.target.value],
          editable: obsParams[instIDToName[e.target.value]].requestsEditable
        };
      }
    }
    setFormState({
      ...formState,
      ...newState
    });
  };

  const handleSubmit = () => {
    if (formState.start_date >= formState.end_date) {
      dispatch(showNotification("Please select an end date that is later than the start date.", "error"));
    } else if (formState.priority === "") {
      dispatch(showNotification("Please select a followup request priority.", "error"));
    } else if (Object.keys(obsParams[formState.instrument_name]).includes("exposureTime") &&
               formState.exposure_time === "") {
      dispatch(showNotification("Please select an exposure time.", "error"));
    } else if (formState.filters.length === 0) {
      dispatch(showNotification("Please select valid filter value(s).", "error"));
    } else {
      if (action === "createNew") {
        dispatch(Actions.submitFollowupRequest(formState));
      } else if (action === "editExisting") {
        dispatch(Actions.editFollowupRequest(formState, followupRequest.id));
      }
      setFormState({
        ...formState,
        ...initialFormState
      });
      if (afterSubmit !== null) {
        afterSubmit();
      }
    }
  };

  return (
    <div>
      <h3>
        {title}
      </h3>
      <div>
        <label>
          Select Instrument:&nbsp;
        </label>
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
      {
        formState.instrument_id && (
          <div>
            {
              !obsParams[formState.instrument_name].requestsEditable && (
                <div>
                  <font color="red">
                    WARNING: You will not be able to edit or delete this request once submitted.
                  </font>
                </div>
              )
            }
            <div>
              <label>
                Start Date (YYYY-MM-DD):&nbsp;
              </label>
              <DatePicker
                name="start_date"
                dateFormat="yyyy-MM-dd"
                selected={formState.start_date}
                onChange={(value) => { setFormState({ ...formState, start_date: value }); }}
              />
            </div>
            <div>
              <label>
                End Date (YYYY-MM-DD):&nbsp;
              </label>
              <DatePicker
                name="end_date"
                dateFormat="yyyy-MM-dd"
                selected={formState.end_date}
                onChange={(value) => { setFormState({ ...formState, end_date: value }); }}
              />
            </div>
            <div>
              {
                obsParams[formState.instrument_name].filters.type === "checkbox" && (
                  <div>
                    <label>
                      Filters:&nbsp;&nbsp;
                    </label>
                    {
                      obsParams[formState.instrument_name].filters.options.map(
                        (filter) => (
                          <span key={filter}>
                            <input
                              type="checkbox"
                              name={`filterCheckbox_${filter}`}
                              checked={formState.filters.includes(filter)}
                              onChange={handleInputChange}
                            />
                            <label>
                              {filter}
                            </label>
                            &nbsp;&nbsp;
                          </span>
                        )
                      )
                    }
                  </div>
                )
              }
              {
                obsParams[formState.instrument_name].filters.type === "select" && (
                  <div>
                    <label>
                      Filter:&nbsp;&nbsp;
                    </label>
                    <select
                      name="filters"
                      value={formState.filter}
                      onChange={handleInputChange}
                    >
                      <option value="null">
                        Select Filter
                      </option>
                      {
                        obsParams[formState.instrument_name].filters.options.map(
                          (filter) => (
                            <option value={filter} key={filter}>
                              {filter}
                            </option>
                          )
                        )
                      }
                    </select>
                  </div>
                )
              }
            </div>
            <div>
              {
                Object.keys(obsParams[formState.instrument_name]).includes("exposureTime") && (
                  <div>
                    <label>
                      Exposure time:&nbsp;
                    </label>
                    <select
                      name="exposure_time"
                      value={formState.exposure_time}
                      onChange={handleInputChange}
                    >
                      <option value="null">
                        Select Exposure Time
                      </option>
                      {
                        obsParams[formState.instrument_name].exposureTime.options.map(
                          (expTime) => (
                            <option value={expTime} key={expTime}>
                              {expTime}
                            </option>
                          )
                        )
                      }
                    </select>
                    {
                      Object.keys(obsParams[formState.instrument_name].exposureTime).includes("note") && (
                        <div>
                          <font color="purple">
                            Note:&nbsp;
                            {obsParams[formState.instrument_name].exposureTime.note}
                          </font>
                        </div>
                      )
                    }
                  </div>
                )
              }
            </div>
            <div>
              <label>
                Priority:
              </label>
              &nbsp;
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
            <br />
            <button type="button" onClick={handleSubmit}>
              Submit
            </button>
          </div>
        )
      }
    </div>
  );
};

FollowupRequestForm.propTypes = {
  source_id: PropTypes.string.isRequired,
  action: PropTypes.string.isRequired,
  instrumentList: PropTypes.arrayOf(PropTypes.shape({
    band: PropTypes.string,
    created_at: PropTypes.string,
    id: PropTypes.number,
    name: PropTypes.string,
    type: PropTypes.string,
    telescope_id: PropTypes.number
  })).isRequired,
  instrumentObsParams: PropTypes.objectOf(PropTypes.any).isRequired,
  followupRequest: PropTypes.shape({
    requester: PropTypes.object,
    instrument: PropTypes.object,
    start_date: PropTypes.string,
    end_date: PropTypes.string,
    priority: PropTypes.string,
    status: PropTypes.string,
    source_id: PropTypes.string,
    id: PropTypes.number
  }),
  title: PropTypes.string,
  afterSubmit: PropTypes.func
};

FollowupRequestForm.defaultProps = {
  followupRequest: null,
  title: "Submit new follow-up request",
  afterSubmit: null
};

export default FollowupRequestForm;
