import React from 'react';
import { useDispatch } from 'react-redux';
import PropTypes from 'prop-types';
import DatePicker from 'react-datepicker';
import { useForm, Controller } from 'react-hook-form';

import * as Actions from '../ducks/source';
import FormValidationError from './FormValidationError';

import 'react-datepicker/dist/react-datepicker-cssmodules.css';

const FollowupRequestForm = ({ obj_id, action, instrumentList, instrumentObsParams, followupRequest = null, title = "Submit new follow-up request", afterSubmit = null }) => {
  const dispatch = useDispatch();
  const obsParams = instrumentObsParams; // Shorten to reduce line length below

  const instIDToName = {};
  instrumentList.forEach((instrumentObj) => {
    instIDToName[instrumentObj.id] = instrumentObj.name;
  });

  const initialFormState = followupRequest !== null ? {
    obj_id: followupRequest.obj_id,
    instrument_id: followupRequest.instrument_id,
    start_date: new Date(followupRequest.start_date),
    end_date: new Date(followupRequest.end_date),
    filters: followupRequest.filters,
    exposure_time: followupRequest.exposure_time,
    priority: followupRequest.priority,
    editable: followupRequest.editable
  } : {
    obj_id,
    instrument_id: "",
    start_date: new Date(),
    end_date: new Date(),
    filters: [],
    exposure_time: "",
    priority: ""
  };

  const { handleSubmit, register, getValues, control, errors, reset } = useForm({
    defaultValues: initialFormState
  });

  let formState = getValues({ nest: true });

  const validateFilters = () => {
    formState = getValues({ nest: true });
    if (Array.isArray(formState.filters)) {
      return formState.filters.filter((v) => Boolean(v)).length >= 1;
    }
    return true;
  };

  const validateDates = () => {
    formState = getValues({ nest: true });
    return formState.start_date < formState.end_date;
  };

  const handleSelectedInstrumentChange = (e) => {
    reset({
      ...initialFormState,
      instrument_id: e.target.value
    });
  };

  const onSubmit = () => {
    const formData = {
      // Need to add obj_id, etc to form data for request
      ...initialFormState,
      ...getValues({ nest: true })
    };
    // We need to include this field in request, but it isn't in form data
    formData.editable = obsParams[instIDToName[formData.instrument_id]].requestsEditable;
    if (action === "createNew") {
      dispatch(Actions.submitFollowupRequest(formData));
    } else if (action === "editExisting") {
      dispatch(Actions.editFollowupRequest(formData, followupRequest.id));
    }
    reset(initialFormState);
    if (afterSubmit !== null) {
      afterSubmit();
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <h3>
          {title}
        </h3>
        <div>
          <label>
            Select Instrument:&nbsp;
          </label>
          <select
            name="instrument_id"
            ref={register({ required: true })}
            onChange={handleSelectedInstrumentChange}
          >
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
          (formState.instrument_id) && (
            <div>
              {
                !obsParams[instIDToName[formState.instrument_id]].requestsEditable &&
                  <FormValidationError message="WARNING: You will not be able to edit or delete this request once submitted." />
              }
              <div>
                {
                  (errors.start_date || errors.end_date) &&
                    <FormValidationError message="Invalid date range." />
                }
                <label>
                  Start Date (YYYY-MM-DD):&nbsp;
                </label>
                <Controller
                  as={<DatePicker dateFormat="yyyy-MM-dd" selected={formState.start_date} />}
                  rules={{ required: true, validate: validateDates }}
                  name="start_date"
                  control={control}
                  valueName="selected"
                  onChange={([selected]) => selected}
                />
              </div>
              <div>
                <label>
                  End Date (YYYY-MM-DD):&nbsp;
                </label>
                <Controller
                  as={<DatePicker dateFormat="yyyy-MM-dd" selected={formState.end_date} />}
                  rules={{ required: true, validate: validateDates }}
                  name="end_date"
                  control={control}
                  valueName="selected"
                  onChange={([selected]) => selected}
                />
              </div>
              <div>
                {
                  obsParams[instIDToName[formState.instrument_id]].filters.type === "checkbox" && (
                    <div>
                      {
                        errors.filters &&
                          <FormValidationError message="Select at least one filter." />
                      }
                      <label>
                        Filters:&nbsp;&nbsp;
                      </label>
                      {
                        obsParams[instIDToName[formState.instrument_id]].filters.options.map(
                          (filter) => (
                            <span key={filter}>
                              <input
                                type="checkbox"
                                name="filters"
                                value={filter}
                                ref={register({ required: true, validate: validateFilters })}
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
                  obsParams[instIDToName[formState.instrument_id]].filters.type === "select" && (
                    <div>
                      {
                        errors.filters &&
                          <FormValidationError message="Please select a filter." />
                      }
                      <label>
                        Filter:&nbsp;&nbsp;
                      </label>
                      <select
                        name="filters"
                        ref={register({ required: true, validate: validateFilters })}
                      >
                        {
                          obsParams[instIDToName[formState.instrument_id]].filters.options.map(
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
                  Object.keys(obsParams[instIDToName[formState.instrument_id]]).includes("exposureTime") && (
                    <div>
                      {
                        errors.exposure_time &&
                          <FormValidationError message="Select an exposure time." />
                      }
                      <label>
                        Exposure time:&nbsp;
                      </label>
                      <select
                        name="exposure_time"
                        ref={register({ required: true })}
                      >
                        {
                          obsParams[instIDToName[formState.instrument_id]].exposureTime.options.map(
                            (expTime) => (
                              <option value={expTime} key={expTime}>
                                {expTime}
                              </option>
                            )
                          )
                        }
                      </select>
                      {
                        Object.keys(obsParams[instIDToName[formState.instrument_id]].exposureTime).includes("note") && (
                          <div>
                            <font color="purple">
                              Note:&nbsp;
                              {obsParams[instIDToName[formState.instrument_id]].exposureTime.note}
                            </font>
                          </div>
                        )
                      }
                    </div>
                  )
                }
              </div>
              <div>
                {
                  errors.priority &&
                    <FormValidationError message="Select priority." />
                }
                <label>
                  Priority:
                </label>
                &nbsp;
                <select name="priority" ref={register({ required: true })}>
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
              <input type="submit" name={`${action}FollowupRequestSubmitButton`} />
            </div>
          )
        }
      </form>
    </div>
  );
};

FollowupRequestForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
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
    obj_id: PropTypes.string,
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
