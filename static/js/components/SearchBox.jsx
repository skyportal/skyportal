import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";

import { makeStyles } from "@material-ui/core/styles";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import FormControl from "@material-ui/core/FormControl";
import Select from "@material-ui/core/Select";
import * as Actions from "../ducks/sources";

const useStyles = makeStyles((theme) => ({
  formControl: {
    margin: theme.spacing(2),
    minWidth: 250,
  },
  selectEmpty: {
    margin: theme.spacing(2),
  },
}));
const SearchBox = ({ sources }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [formState, setFormState] = useState({
    sourceID: "",
    ra: "",
    dec: "",
    radius: "",
    startDate: "",
    endDate: "",
    simbadClass: "",
    hasTNSname: false,
    entriesPerPage: 100,
  });

  const [jumpToPageInputValue, setJumpToPageInputValue] = useState("");

  const handleInputChange = (event) => {
    const newState = {};
    newState[event.target.name] = event.target.type === "checkbox" ? event.target.checked : event.target.value;
    setFormState({
      ...formState,
      ...newState,
    });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    dispatch(Actions.fetchSources(formState));
  };

  const handleReset = () => {
    setFormState({
      sourceID: "",
      ra: "",
      dec: "",
      radius: "",
      startDate: "",
      endDate: "",
      simbadClass: "",
      hasTNSname: false,
      entriesPerPage: "",
    });
    dispatch(Actions.fetchSources());
  };

  const handleClickNextPage = (event) => {
    event.preventDefault();
    const vals = {
      ...formState,
      pageNumber: sources.pageNumber + 1,
      totalMatches: sources.totalMatches,
    };
    dispatch(Actions.fetchSources(vals));
  };

  const handleClickPreviousPage = (event) => {
    event.preventDefault();
    const vals = {
      ...formState,
      pageNumber: sources.pageNumber - 1,
      totalMatches: sources.totalMatches,
    };
    dispatch(Actions.fetchSources(vals));
  };

  const handleJumpToPageInputChange = (event) => {
    setJumpToPageInputValue(event.target.value);
  };

  const handleClickJumpToPage = (event) => {
    event.preventDefault();
    const vals = {
      ...formState,
      pageNumber: jumpToPageInputValue,
      totalMatches: sources.totalMatches,
    };
    if (event.target.value < 1) {
      vals.pageNumber = 1;
    } else if (event.target.value > Math.ceil(sources.totalMatches / 100)) {
      vals.pageNumber = Math.ceil(sources.totalMatches / 100);
    }
    dispatch(Actions.fetchSources(vals));
  };
  return (
    <div>
      <h4>Filter Sources</h4>
      <form onSubmit={handleSubmit}>
        <table>
          <tbody>
            <tr>
              <td colSpan="3">
                <b>By Name/ID</b>
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
                <b>By Position&nbsp;</b>
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
                  <b>By Time Last Detected&nbsp;</b>
                </label>
              </td>
            </tr>
            <tr>
              <td colSpan="3">
                Required format: %Y-%m-%dT%H:%M:%S in UTC time, e.g.
                2012-08-30T00:00:00
              </td>
            </tr>
            <tr>
              <td>
                <label>Start Date:&nbsp;</label>
                <input
                  type="text"
                  name="startDate"
                  value={formState.startDate}
                  onChange={handleInputChange}
                  size="6"
                />
              </td>
              <td>
                <label>End Date:&nbsp;</label>
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
                  <b>By Simbad Class&nbsp;</b>
                </label>
              </td>
            </tr>
            <tr>
              <td>
                <label>Class:&nbsp;</label>
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
                  <b>Must Have TNS Name:&nbsp;</b>
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
                <input
                  type="submit"
                  id="submitQueryButton"
                  disabled={sources.queryInProgress}
                />
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
        {sources && (
          <div>
            <div style={{ display: "inline-block" }}>
              <button
                type="button"
                onClick={handleClickPreviousPage}
                disabled={sources.pageNumber === 1}
              >
                View Previous
                {formState.entriesPerPage}
                Sources
              </button>
            </div>
            <div style={{ display: "inline-block" }}>
              <i>
                Displaying&nbsp;
                {sources.sourceNumberingStart}
                -
                {sources.sourceNumberingEnd}
                &nbsp; of&nbsp;
                {sources.totalMatches}
                &nbsp; matching sources.
              </i>
            </div>
            <div style={{ display: "inline-block" }}>
              <button
                type="button"
                onClick={handleClickNextPage}
                disabled={sources.lastPage}
              >
                View Next
                {formState.entriesPerPage}
                Sources
              </button>
            </div>
            <div>
              <i>or&nbsp;&nbsp;</i>
              <button type="button" onClick={handleClickJumpToPage}>
                Jump to page:
              </button>
              &nbsp;&nbsp;
              <input
                type="text"
                style={{ width: "25px" }}
                onChange={handleJumpToPageInputChange}
                value={jumpToPageInputValue}
                name="jumpToPageInputField"
              />
              <FormControl variant="filled" className={classes.formControl}>
                <InputLabel id="demo-simple-select-filled-label">
                  Number of Entries per Page
                </InputLabel>
                <Select
                  name="entriesPerPage"
                  labelId="demo-simple-select-filled-label"
                  id="demo-simple-select-filled"
                  value={formState.entriesPerPage}
                  onChange={handleInputChange}
                >
                  <MenuItem value={10}>10</MenuItem>
                  <MenuItem value={25}>25</MenuItem>
                  <MenuItem value={50}>50</MenuItem>
                  <MenuItem value={100}>100</MenuItem>
                </Select>
              </FormControl>
            </div>
          </div>
        )}
      </form>
      <br />
    </div>
  );
};

SearchBox.propTypes = {
  sources: PropTypes.shape({
    queryInProgress: PropTypes.bool,
    totalMatches: PropTypes.number.isRequired,
    sourceNumberingStart: PropTypes.number.isRequired,
    sourceNumberingEnd: PropTypes.number.isRequired,
    pageNumber: PropTypes.number.isRequired,
    lastPage: PropTypes.bool.isRequired,
  }).isRequired,
};

export default SearchBox;
