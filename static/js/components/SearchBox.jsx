import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";

import {
  Box,
  Paper,
  Button,
  ButtonGroup,
  Checkbox,
  FormControlLabel,
  TextField,
} from "@material-ui/core";
import { makeStyles } from "@material-ui/core/styles";

import * as Actions from "../ducks/sources";

import styles from "./SearchBox.css";

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
    hasTNSname: false,
  });

  const [jumpToPageInputValue, setJumpToPageInputValue] = useState("");

  const handleInputChange = (event) => {
    const newState = {};
    newState[event.target.name] =
      event.target.type === "checkbox"
        ? event.target.checked
        : event.target.value;
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
    dispatch(Actions.fetchSources(vals));
  };

  const useStyles = makeStyles((theme) => ({
    paper: {
      padding: "1rem"
    },
    root: {
      display: 'flex',
      flexWrap: 'wrap',
      width: "35rem",
      "& .MuiTextField-root": {
        margin: theme.spacing(0.2),
        width: "10rem",
      },
    },
    blockWrapper: {
      width: "100%",
    },
    title: {
      margin: "1rem 0rem 0rem 0rem",
    },
  }));

  const classes = useStyles();

  return (
    <Paper className={classes.paper} variant="outlined">
      <form className={classes.root} noValidate autoComplete="off">
        <div className={classes.blockWrapper}>
          <h4> Filter Sources </h4>
        </div>
        <div className={classes.blockWrapper}>
          <h5 className={classes.title}> Filter by Name or ID </h5>
        </div>
        <div className={classes.blockWrapper}>
          <TextField
            fullWidth
            label="Source ID/Name"
            name="sourceID"
            value={formState.sourceID}
            onChange={handleInputChange}
          />
        </div>

        <div className={classes.blockWrapper}>
          <h5 className={classes.title}> Filter by Position </h5>
        </div>
        <div className={classes.blockWrapper}>
          <TextField
            size="small"
            label="RA (degrees)"
            name="ra"
            value={formState.ra}
            onChange={handleInputChange}
          />
          <TextField
            size="small"
            label="Dec (degrees)"
            name="dec"
            value={formState.dec}
            onChange={handleInputChange}
          />
          <TextField
            size="small"
            label="Radius (degrees)"
            name="radius"
            value={formState.radius}
            onChange={handleInputChange}
          />
        </div>
        <div className={classes.blockWrapper}>
          <h5 className={classes.title}>
            {" "}
            Filter by Time Last Detected (UTC){" "}
          </h5>
        </div>
        <div className={classes.blockWrapper}>
          <TextField
            size="small"
            label="Start Date"
            name="startDate"
            value={formState.startDate}
            onChange={handleInputChange}
            placeholder="2012-08-30T00:00:00"
          />
          <TextField
            size="small"
            label="End Date"
            name="endDate"
            value={formState.endDate}
            onChange={handleInputChange}
            placeholder="2012-08-30T00:00:00"
          />
        </div>
        <div className={classes.blockWrapper}>
          <h5 className={classes.title}> Filter by Simbad Class </h5>
        </div>
        <div className={classes.blockWrapper}>
          <TextField
            size="small"
            label="Class Name"
            type="text"
            name="simbadClass"
            value={formState.simbadClass}
            onChange={handleInputChange}
          />
          <FormControlLabel
            label="TNS Name"
            labelPlacement="start"
            control={
              <Checkbox
                color="primary"
                type="checkbox"
                name="hasTNSname"
                checked={formState.hasTNSname}
                onChange={handleInputChange}
              />
            }
          />
        </div>
        <div className={classes.blockWrapper}>
        <ButtonGroup variant="contained" color="primary" aria-label="contained primary button group">
        <Button
            variant="contained"
            color="primary"
            onClick={handleSubmit}
            disabled={sources.queryInProgress}
          >
            Submit
          </Button>
          <Button variant="contained" color="primary" onClick={handleReset}>
            Reset
          </Button>
        </ButtonGroup>
        </div>
      </form>
      {sources && (
        <div className={styles.tableSubTitle}>
          <div style={{ display: "inline-block" }}>
            <button
              className={styles.inlineButton}
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
              {sources.sourceNumberingStart}-{sources.sourceNumberingEnd}
              &nbsp; of&nbsp;
              {sources.totalMatches}
              &nbsp; matching sources.
            </i>
          </div>
          <div style={{ display: "inline-block" }}>
            <button
              className={styles.inlineButton}
              type="button"
              onClick={handleClickNextPage}
              disabled={sources.lastPage}
            >
              View Next 100 Sources
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
          </div>
        </div>
      )}
    </Paper>
  );
};

SearchBox.propTypes = {
  sources: PropTypes.shape({
    lastPage: PropTypes.bool,
    latest: PropTypes.any,
    pageNumber: PropTypes.number,
    sourceNumberingStart: PropTypes.any,
    sourcesNumberingEnd: PropTypes.any,
    totalMatches: PropTypes.any,
    queryInProgress: PropTypes.any,
    sourceNumberingEnd: PropTypes.any,
  }).isRequired,
};

export default SearchBox;
