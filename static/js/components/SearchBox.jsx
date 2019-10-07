import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

import * as Actions from '../ducks/sources';


const SearchBox = ({ sources }) => {
  const dispatch = useDispatch();

  const [formState, setFormState] = useState({
    sourceID: "",
    ra: "",
    dec: "",
    radius: "",
    startDate: "",
    endDate: "",
    simbadClass: "",
    hasTNSname: false
  });

  const handleInputChange = (event) => {
    const newState = {};
    newState[event.target.name] = event.target.type === 'checkbox' ?
      event.target.checked : event.target.value;
    setFormState({
      ...formState,
      ...newState
    });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    dispatch(Actions.submitSourceFilterParams(formState));
  };

  const handleReset = (event) => {
    setFormState({
      sourceID: "",
      ra: "",
      dec: "",
      radius: "",
      startDate: "",
      endDate: "",
      simbadClass: "",
      hasTNSname: false
    });
    dispatch(Actions.fetchSources());
  };

  const handleClickNextPage = (event) => {
    event.preventDefault();
    const vals = { ...formState, pageNumber: sources.pageNumber + 1 };
    dispatch(Actions.submitSourceFilterParams(vals));
  };

  const handleClickPreviousPage = (event) => {
    event.preventDefault();
    const vals = { ...formState, pageNumber: sources.pageNumber - 1 };
    dispatch(Actions.submitSourceFilterParams(vals));
  };

  return (
    <div>
      <h4>
        Filter Sources
      </h4>
      <form onSubmit={handleSubmit}>
        <table>
          <tbody>
            <tr>
              <td colSpan="3">
                <b>
                  By Name/ID
                </b>
              </td>
            </tr>
            <tr>
              <td colSpan="3">
                <label>
                  Source ID/Name (can be substring):
                  <input
                    type="text"
                    name="sourceID"
                    value={formState.sourceID}
                    onChange={handleInputChange}
                    size="6"
                  />
                </label>
              </td>
            </tr>
            <tr>
              <td colSpan="3">
                <b>
                  By Position&nbsp;
                </b>
              </td>
            </tr>
            <tr>
              <td>
                <label>
                  RA (degrees):
                  <input
                    type="text"
                    name="ra"
                    value={formState.ra}
                    onChange={handleInputChange}
                    size="6"
                  />
                </label>
              </td>
              <td>
                <label>
                  Dec (degrees):
                  <input
                    type="text"
                    name="dec"
                    value={formState.dec}
                    onChange={handleInputChange}
                    size="6"
                  />
                </label>
              </td>
              <td>
                <label>
                  Radius (degrees):
                  <input
                    type="text"
                    name="radius"
                    value={formState.radius}
                    onChange={handleInputChange}
                    size="6"
                  />
                </label>
              </td>
            </tr>
            <tr>
              <td colSpan="3">
                <label>
                  <b>
                    By Time Last Detected&nbsp;
                  </b>
                </label>
              </td>
            </tr>
            <tr>
              <td colSpan="3">
                Required format: %Y-%m-%dT%H:%M:%S in UTC time, e.g. 2012-08-30T00:00:00
              </td>
            </tr>
            <tr>
              <td>
                <label>
                  Start Date:&nbsp;
                </label>
                <input
                  type="text"
                  name="startDate"
                  value={formState.startDate}
                  onChange={handleInputChange}
                  size="6"
                />
              </td>
              <td>
                <label>
                  End Date:&nbsp;
                </label>
                <input
                  type="text"
                  name="endDate"
                  value={formState.endDate}
                  onChange={handleInputChange}
                  size="6"
                />
              </td>
            </tr>
            <tr>
              <td>
                <label>
                  <b>
                    By Simbad Class&nbsp;
                  </b>
                </label>
              </td>
            </tr>
            <tr>
              <td>
                <label>
                  Class:&nbsp;
                </label>
                <input
                  type="text"
                  name="simbadClass"
                  value={formState.simbadClass}
                  onChange={handleInputChange}
                  size="6"
                />
              </td>
            </tr>
            <tr>
              <td>
                <label>
                  <b>
                    Must Have TNS Name:&nbsp;
                  </b>
                </label>
                <input
                  type="checkbox"
                  name="hasTNSname"
                  checked={formState.hasTNSname}
                  onChange={handleInputChange}
                  size="6"
                />
              </td>
            </tr>
            <tr>
              <td>
                <input type="submit" disabled={sources.queryInProgress} />
              </td>
              <td>
                <button type="button" onClick={handleReset}>
                  Reset
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <br />
        {
          sources && (
            <div>
              <div style={{ display: "inline-block" }}>
                <button
                  type="button"
                  onClick={handleClickPreviousPage}
                  disabled={sources.pageNumber === 1}
                >
                  View Previous 100 Sources
                </button>
              </div>
              <div style={{ display: "inline-block" }}>
                <i>
                  Displaying&nbsp;
                  {sources.sourceNumberingStart}
                  -
                  {sources.sourceNumberingEnd}
                  &nbsp;
                  of&nbsp;
                  {sources.totalMatches}
                  &nbsp;
                  matching sources.
                </i>
              </div>
              <div style={{ display: "inline-block" }}>
                <button
                  type="button"
                  onClick={handleClickNextPage}
                  disabled={sources.lastPage}
                >
                  View Next 100 Sources
                </button>
              </div>
            </div>
          )
        }
      </form>
      <br />
    </div>
  );
};
SearchBox.propTypes = {
  sources: PropTypes.object.isRequired
};

export default SearchBox;
