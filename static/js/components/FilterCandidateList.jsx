import React, { useState, useEffect } from "react";
import { useDispatch } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import PropTypes from "prop-types";

import FormControlLabel from "@material-ui/core/FormControlLabel";
import Checkbox from "@material-ui/core/Checkbox";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import { KeyboardDatePicker } from "@material-ui/pickers";
import Paper from "@material-ui/core/Paper";
import SearchIcon from "@material-ui/icons/Search";
import { makeStyles } from "@material-ui/core/styles";

import * as candidatesActions from "../ducks/candidates";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";
import FormValidationError from "./FormValidationError";

const useStyles = makeStyles(() => ({
  filterListContainer: {
    padding: "1rem",
    display: "flex",
    flexFlow: "column nowrap",
  },
  searchButton: {
    marginTop: "1rem",
  },
  pages: {
    marginTop: "1rem",
    "& > div": {
      display: "inline-block",
      marginRight: "1rem",
    },
  },
  jumpToPage: {
    marginTop: "0.3125rem",
    display: "flex",
    flexFlow: "row nowrap",
    alignItems: "flex-end",
    "& > button": {
      marginLeft: "0.5rem",
    },
  },
}));

const FilterCandidateList = ({
  userAccessibleGroups,
  pageNumber,
  numberingStart,
  numberingEnd,
  totalMatches,
  lastPage,
  setQueryInProgress,
}) => {
  const classes = useStyles();

  const [jumpToPageInputValue, setJumpToPageInputValue] = useState("");

  const { handleSubmit, getValues, control, errors, reset } = useForm();

  useEffect(() => {
    reset({
      groupIDs: Array(userAccessibleGroups.length).fill(true),
      startDate: null,
      endDate: null,
    });
  }, [reset, userAccessibleGroups]);

  const dispatch = useDispatch();

  let formState = getValues({ nest: true });

  const validateGroups = () => {
    formState = getValues({ nest: true });
    return formState.groupIDs.filter((value) => Boolean(value)).length >= 1;
  };

  const validateDates = () => {
    formState = getValues({ nest: true });
    if (!!formState.startDate && !!formState.endDate) {
      return formState.startDate <= formState.endDate;
    }
    return true;
  };

  const onSubmit = async (data) => {
    setQueryInProgress(true);
    const groupIDs = userAccessibleGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter((ID, idx) => data.groupIDs[idx]);
    data.groupIDs = selectedGroupIDs;
    // Convert dates to ISO for parsing on back-end
    if (data.startDate) {
      data.startDate = data.startDate.toISOString();
    }
    if (data.endDate) {
      data.endDate = data.endDate.toISOString();
    }
    await dispatch(candidatesActions.fetchCandidates(data));
    setQueryInProgress(false);
  };

  const handleClickNextPage = async () => {
    const formData = getValues({ nest: true });
    onSubmit({ ...formData, pageNumber: pageNumber + 1 });
  };

  const handleClickPreviousPage = async () => {
    const formData = getValues({ nest: true });
    onSubmit({ ...formData, pageNumber: pageNumber - 1 });
  };

  const handleJumpToPageInputChange = (e) => {
    setJumpToPageInputValue(e.target.value);
  };

  const handleClickJumpToPage = async () => {
    const formData = getValues({ nest: true });
    onSubmit({ ...formData, pageNumber: jumpToPageInputValue });
  };

  return (
    <Paper variant="outlined">
      <div className={classes.filterListContainer}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <div>
            {(errors.startDate || errors.endDate) && (
              <FormValidationError message="Invalid date range." />
            )}
            <Controller
              as={
                <KeyboardDatePicker
                  format="YYYY-MM-DD"
                  value={formState.startDate}
                  emptyLabel="Start Date"
                />
              }
              rules={{ validate: validateDates }}
              name="startDate"
              control={control}
            />
            <Controller
              as={
                <KeyboardDatePicker
                  format="YYYY-MM-DD"
                  value={formState.endDate}
                  emptyLabel="End Date"
                />
              }
              rules={{ validate: validateDates }}
              name="endDate"
              control={control}
              onChange={([selected]) => selected}
            />
          </div>
          <div>
            <FormControlLabel
              control={
                <Controller
                  as={Checkbox}
                  name="unsavedOnly"
                  control={control}
                  defaultValue={false}
                />
              }
              label="Show only unsaved candidates"
            />
          </div>
          <div>
            <Responsive
              element={FoldBox}
              title="Program Selection"
              mobileProps={{ folded: true }}
            >
              {errors.groupIDs && (
                <FormValidationError message="Select at least one group." />
              )}
              {userAccessibleGroups.map((group, idx) => (
                <FormControlLabel
                  key={group.id}
                  control={
                    <Controller
                      as={Checkbox}
                      name={`groupIDs[${idx}]`}
                      control={control}
                      rules={{ validate: validateGroups }}
                      defaultValue
                    />
                  }
                  label={group.name}
                />
              ))}
            </Responsive>
          </div>
          <div className={classes.searchButton}>
            <Button
              variant="contained"
              type="submit"
              endIcon={<SearchIcon />}
              color="primary"
            >
              Search
            </Button>
          </div>
        </form>
        <div className={classes.pages}>
          <div>
            <Button
              variant="contained"
              onClick={handleClickPreviousPage}
              disabled={pageNumber === 1}
              size="small"
            >
              Previous Page
            </Button>
          </div>
          <div>
            <i>
              Displaying&nbsp;
              {numberingStart}-{numberingEnd}
              &nbsp; of&nbsp;
              {totalMatches}
              &nbsp; candidates.
            </i>
          </div>
          <div>
            <Button
              variant="contained"
              onClick={handleClickNextPage}
              disabled={lastPage}
              size="small"
            >
              Next Page
            </Button>
          </div>
        </div>
        <div className={classes.jumpToPage}>
          <TextField
            label="Jump to Page Number"
            type="number"
            onChange={handleJumpToPageInputChange}
            value={jumpToPageInputValue}
            name="jumpToPageInputField"
          />
          <Button
            variant="contained"
            onClick={handleClickJumpToPage}
            size="small"
          >
            Jump to Page
          </Button>
        </div>
        <br />
        <br />
      </div>
    </Paper>
  );
};
FilterCandidateList.propTypes = {
  userAccessibleGroups: PropTypes.arrayOf(PropTypes.object).isRequired,
  pageNumber: PropTypes.number.isRequired,
  numberingStart: PropTypes.number.isRequired,
  numberingEnd: PropTypes.number.isRequired,
  totalMatches: PropTypes.number.isRequired,
  lastPage: PropTypes.bool.isRequired,
  setQueryInProgress: PropTypes.func.isRequired,
};

export default FilterCandidateList;
