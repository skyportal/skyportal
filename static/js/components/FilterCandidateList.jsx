import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import PropTypes from "prop-types";

import FormControlLabel from "@material-ui/core/FormControlLabel";
import Checkbox from "@material-ui/core/Checkbox";
import Button from "@material-ui/core/Button";
import { KeyboardDateTimePicker } from "@material-ui/pickers";
import Paper from "@material-ui/core/Paper";
import SearchIcon from "@material-ui/icons/Search";
import Input from "@material-ui/core/Input";
import InputLabel from "@material-ui/core/InputLabel";
import Chip from "@material-ui/core/Chip";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import TextField from "@material-ui/core/TextField";
import { makeStyles, useTheme } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as candidatesActions from "../ducks/candidates";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";
import FormValidationError from "./FormValidationError";
import { allowedClasses } from "./ClassificationForm";

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
  formRow: {
    margin: "1rem 0",
  },
  redshiftField: {
    display: "inline-block",
    marginRight: "0.5rem",
  },
}));

function getStyles(classification, selectedClassifications, theme) {
  return {
    fontWeight:
      selectedClassifications.indexOf(classification) === -1
        ? theme.typography.fontWeightRegular
        : theme.typography.fontWeightMedium,
  };
}

const FilterCandidateList = ({
  userAccessibleGroups,
  setQueryInProgress,
  setFilterGroups,
  numPerPage,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  const defaultStartDate = new Date();
  defaultStartDate.setDate(defaultStartDate.getDate() - 1);
  const defaultEndDate = new Date();

  const ITEM_HEIGHT = 48;
  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5,
        width: 250,
      },
    },
  };

  // Get unique classification names, in alphabetical order
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList.filter((t) => t.isLatest);
  let classifications = [];
  latestTaxonomyList.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy).map(
      (option) => option.class
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = classifications
    .filter(
      (classification, index) =>
        classifications.indexOf(classification) === index
    )
    .sort();

  const [selectedClassifications, setSelectedClassifications] = useState([]);

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
    if (formData.classifications.length > 0) {
      data.classifications = formData.classifications;
    }
    if (formData.redshiftMinimum && formData.redshiftMaximum) {
      data.redshiftRange = `(${formData.redshiftMinimum},${formData.redshiftMaximum})`;
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
                  data-testid="startDatePicker"
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
                  data-testid="endDatePicker"
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
          <div className={classes.formRow}>
            <InputLabel id="classifications-select-label">
              Classifications
            </InputLabel>
            <Controller
              render={({ onChange, value }) => (
                <Select
                  labelId="classifications-select-label"
                  id="classifications-select"
                  multiple
                  value={value}
                  onChange={(event) => {
                    setSelectedClassifications(event.target.value);
                    onChange(event.target.value);
                  }}
                  input={<Input id="classifications-select" />}
                  renderValue={(selected) => (
                    <div className={classes.chips}>
                      {selected.map((classification) => (
                        <Chip
                          key={classification}
                          label={classification}
                          className={classes.chip}
                        />
                      ))}
                    </div>
                  )}
                  MenuProps={MenuProps}
                >
                  {classifications.map((classification) => (
                    <MenuItem
                      key={classification}
                      value={classification}
                      style={getStyles(
                        classification,
                        selectedClassifications,
                        theme
                      )}
                    >
                      {classification}
                    </MenuItem>
                  ))}
                </Select>
              )}
              name="classifications"
              control={control}
              defaultValue={[]}
            />
          </div>
          <div className={classes.formRow}>
            <InputLabel id="redshift-select-label">Redshift</InputLabel>
            <div className={classes.redshiftField}>
              <Controller
                render={({ onChange, value }) => (
                  <TextField
                    id="minimum-redshift"
                    labelId="classifications-select-label"
                    label="Minimum"
                    type="number"
                    value={value}
                    inputProps={{ step: 0.001 }}
                    size="small"
                    margin="dense"
                    InputLabelProps={{
                      shrink: true,
                    }}
                    onChange={(event) => onChange(event.target.value)}
                  />
                )}
                name="redshiftMinimum"
                control={control}
                defaultValue=""
              />
            </div>
            <div className={classes.redshiftField}>
              <Controller
                render={({ onChange, value }) => (
                  <TextField
                    id="maximum-redshift"
                    label="Maximum"
                    type="number"
                    value={value}
                    inputProps={{ step: 0.001 }}
                    size="small"
                    margin="dense"
                    InputLabelProps={{
                      shrink: true,
                    }}
                    onChange={(event) => onChange(event.target.value)}
                  />
                )}
                name="redshiftMaximum"
                control={control}
                defaultValue=""
              />
            </div>
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
