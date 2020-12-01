import React, { useEffect } from "react";
import { useDispatch } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import PropTypes from "prop-types";

import FormControlLabel from "@material-ui/core/FormControlLabel";
import Checkbox from "@material-ui/core/Checkbox";
import Button from "@material-ui/core/Button";
import { KeyboardDateTimePicker } from "@material-ui/pickers";
import Paper from "@material-ui/core/Paper";
import SearchIcon from "@material-ui/icons/Search";
import { makeStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as candidatesActions from "../ducks/candidates";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";
import FormValidationError from "./FormValidationError";

dayjs.extend(utc);

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
  setQueryInProgress,
  setFilterGroups,
  numPerPage,
}) => {
  const classes = useStyles();

  const defaultStartDate = new Date();
  defaultStartDate.setDate(defaultStartDate.getDate() - 1);
  const defaultEndDate = new Date();

  const { handleSubmit, getValues, control, errors, reset } = useForm({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
  });

  useEffect(() => {
    reset({
      groupIDs: Array(userAccessibleGroups.length).fill(false),
      startDate: defaultStartDate,
      endDate: defaultEndDate,
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

  const onSubmit = async (formData) => {
    setQueryInProgress(true);
    const groupIDs = userAccessibleGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter(
      (ID, idx) => formData.groupIDs[idx]
    );

    const data = {
      groupIDs: selectedGroupIDs,
      unsavedOnly: formData.unsavedOnly,
    };
    // Convert dates to ISO for parsing on back-end
    if (formData.startDate) {
      data.startDate = formData.startDate.toISOString();
    }
    if (formData.endDate) {
      data.endDate = formData.endDate.toISOString();
    }
    setFilterGroups(
      userAccessibleGroups.filter((g) => selectedGroupIDs.includes(g.id))
    );
    // Save form-specific data, formatted for the API query
    await dispatch(candidatesActions.setFilterFormData(data));

    await dispatch(
      candidatesActions.fetchCandidates({ pageNumber: 1, numPerPage, ...data })
    );
    setQueryInProgress(false);
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
              render={({ onChange, value }) => (
                <KeyboardDateTimePicker
                  value={dayjs.utc(value)}
                  onChange={(e, date) => onChange(dayjs.utc(date))}
                  label="Start (UTC)"
                  format="YYYY/MM/DD HH:mm"
                  ampm={false}
                  showTodayButton={false}
                />
              )}
              rules={{ validate: validateDates }}
              name="startDate"
              control={control}
            />
            &nbsp;
            <Controller
              render={({ onChange, value }) => (
                <KeyboardDateTimePicker
                  value={dayjs.utc(value)}
                  onChange={(e, date) => onChange(dayjs.utc(date))}
                  label="End (UTC)"
                  format="YYYY/MM/DD HH:mm"
                  ampm={false}
                  showTodayButton={false}
                />
              )}
              rules={{ validate: validateDates }}
              name="endDate"
              control={control}
            />
          </div>
          <div>
            <FormControlLabel
              control={
                <Controller
                  render={({ onChange, value }) => (
                    <Checkbox
                      onChange={(event) => onChange(event.target.checked)}
                      checked={value}
                      data-testid="unsavedOnlyCheckbox"
                    />
                  )}
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
                      render={({ onChange, value }) => (
                        <Checkbox
                          onChange={(event) => onChange(event.target.checked)}
                          checked={value}
                          data-testid={`filteringFormGroupCheckbox-${group.id}`}
                        />
                      )}
                      name={`groupIDs[${idx}]`}
                      control={control}
                      rules={{ validate: validateGroups }}
                      defaultValue={false}
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
        <br />
        <br />
      </div>
    </Paper>
  );
};
FilterCandidateList.propTypes = {
  userAccessibleGroups: PropTypes.arrayOf(PropTypes.object).isRequired,
  setQueryInProgress: PropTypes.func.isRequired,
  setFilterGroups: PropTypes.func.isRequired,
  numPerPage: PropTypes.number.isRequired,
};

export default FilterCandidateList;
