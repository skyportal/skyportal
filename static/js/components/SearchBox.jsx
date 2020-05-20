import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

import Paper from "@material-ui/core/Paper";
import Button from "@material-ui/core/Button";
import ButtonGroup from "@material-ui/core/ButtonGroup";
import Checkbox from "@material-ui/core/Checkbox";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import TextField from "@material-ui/core/TextField";
import { makeStyles } from "@material-ui/core/styles";
import { useForm, Controller } from "react-hook-form";

import * as Actions from "../ducks/sources";


const SearchBox = ({ sources }) => {
  const dispatch = useDispatch();

  const { handleSubmit, register, getValues, control, reset } = useForm();

  const [jumpToPageInputValue, setJumpToPageInputValue] = useState("");

  const onSubmit = (data) => {
    dispatch(Actions.fetchSources(data));
  };

  const handleClickReset = () => {
    reset();
    dispatch(Actions.fetchSources());
  };

  const handleClickNextPage = (event) => {
    event.preventDefault();
    const data = {
      ...getValues(),
      pageNumber: sources.pageNumber + 1,
      totalMatches: sources.totalMatches,
    };
    dispatch(Actions.fetchSources(data));
  };

  const handleClickPreviousPage = (event) => {
    event.preventDefault();
    const data = {
      ...getValues(),
      pageNumber: sources.pageNumber - 1,
      totalMatches: sources.totalMatches,
    };
    dispatch(Actions.fetchSources(data));
  };

  const handleJumpToPageInputChange = (event) => {
    setJumpToPageInputValue(event.target.value);
  };

  const handleClickJumpToPage = (event) => {
    event.preventDefault();
    const data = {
      ...getValues(),
      pageNumber: jumpToPageInputValue,
      totalMatches: sources.totalMatches,
    };
    dispatch(Actions.fetchSources(data));
  };

  const useStyles = makeStyles((theme) => ({
    paper: {
      padding: "1rem",
    },
    root: {
      display: "flex",
      flexWrap: "wrap",
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
      <form className={classes.root} onSubmit={handleSubmit(onSubmit)}>
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
            inputRef={register}
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
            inputRef={register}
          />
          <TextField
            size="small"
            label="Dec (degrees)"
            name="dec"
            inputRef={register}
          />
          <TextField
            size="small"
            label="Radius (degrees)"
            name="radius"
            inputRef={register}
          />
        </div>
        <div className={classes.blockWrapper}>
          <h5 className={classes.title}>Filter by Time Last Detected (UTC)</h5>
        </div>
        <div className={classes.blockWrapper}>
          <TextField
            size="small"
            label="Start Date"
            name="startDate"
            inputRef={register}
            placeholder="2012-08-30T00:00:00"
          />
          <TextField
            size="small"
            label="End Date"
            name="endDate"
            inputRef={register}
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
            inputRef={register}
          />
          <FormControlLabel
            label="TNS Name"
            labelPlacement="start"
            control={(
              <Controller
                as={<Checkbox color="primary" type="checkbox" />}
                name="hasTNSname"
                control={control}
                defaultValue={false}
              />
            )}
          />
        </div>
        <div className={classes.blockWrapper}>
          <ButtonGroup
            variant="contained"
            color="primary"
            aria-label="contained primary button group"
          >
            <Button
              variant="contained"
              color="primary"
              type="submit"
              disabled={sources.queryInProgress}
            >
              Submit
            </Button>
            <Button variant="contained" color="primary" onClick={handleClickReset}>
              Reset
            </Button>
          </ButtonGroup>
        </div>
      </form>
      {sources && (
        <div>
          <div style={{ display: "inline-block" }}>
            <Button
              type="button"
              onClick={handleClickPreviousPage}
              disabled={sources.pageNumber === 1}
            >
              View Previous 100 Sources
            </Button>
          </div>
          <div style={{ display: "inline-block" }}>
            <i>
              Displaying&nbsp;
              {sources.numberingStart}
              -
              {sources.numberingEnd}
              &nbsp; of&nbsp;
              {sources.totalMatches}
              &nbsp; matching sources.
            </i>
          </div>
          <div style={{ display: "inline-block" }}>
            <Button
              type="button"
              onClick={handleClickNextPage}
              disabled={sources.lastPage}
            >
              View Next 100 Sources
            </Button>
          </div>
          <div>
            <i>or&nbsp;&nbsp;</i>
            <Button type="button" onClick={handleClickJumpToPage}>
              Jump to page:
            </Button>
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
    pageNumber: PropTypes.number,
    numberingStart: PropTypes.any,
    totalMatches: PropTypes.any,
    queryInProgress: PropTypes.any,
    numberingEnd: PropTypes.any,
  }).isRequired,
};

export default SearchBox;
