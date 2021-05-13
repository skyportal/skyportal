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
  savedStatusSelect: {
    margin: "1rem 0",
    "& input": {
      fontSize: "1rem",
    },
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

export const rejectedStatusSelectOptions = [
  { value: "hide", label: "Hide rejected candidates" },
  { value: "show", label: "Show rejected candidates" },
];

export const savedStatusSelectOptions = [
  { value: "all", label: "regardless of saved status" },
  { value: "savedToAllSelected", label: "and is saved to all selected groups" },
  {
    value: "savedToAnySelected",
    label: "and is saved to at least one of the selected groups",
  },
  {
    value: "savedToAnyAccessible",
    label: "and is saved to at least one group I have access to",
  },
  {
    value: "notSavedToAnyAccessible",
    label: "and is not saved to any of group I have access to",
  },
  {
    value: "notSavedToAnySelected",
    label: "and is not saved to any of the selected groups",
  },
  {
    value: "notSavedToAllSelected",
    label: "and is not saved to all of the selected groups",
  },
];

const FilterCandidateList = ({
  userAccessibleGroups,
  setQueryInProgress,
  setFilterGroups,
  numPerPage,
  annotationFilterList,
  setSortOrder,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  const { scanningProfiles } = useSelector(
    (state) => state.profile.preferences
  );

  const defaultScanningProfile = scanningProfiles?.find(
    (profile) => profile.default
  );

  const defaultStartDate = new Date();
  let defaultEndDate = null;
  if (defaultScanningProfile?.timeRange) {
    defaultEndDate = new Date();
    defaultStartDate.setHours(
      defaultStartDate.getHours() -
        parseInt(defaultScanningProfile.timeRange, 10)
    );
  } else {
    defaultStartDate.setDate(defaultStartDate.getDate() - 1);
  }

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
  classifications = Array.from(new Set(classifications)).sort();

  const [selectedClassifications, setSelectedClassifications] = useState([]);

  const { handleSubmit, getValues, control, errors, reset } = useForm({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
  });

  useEffect(() => {
    const selectedGroupIDs = Array(userAccessibleGroups.length).fill(false);
    const groupIDs = userAccessibleGroups.map((g) => g.id);
    groupIDs.forEach((ID, i) => {
      selectedGroupIDs[i] = defaultScanningProfile?.groupIDs.includes(ID);
    });
    reset({
      groupIDs: selectedGroupIDs,
      startDate: defaultStartDate,
      endDate: defaultEndDate,
    });
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reset, defaultScanningProfile, userAccessibleGroups]);

  const dispatch = useDispatch();
  // Set initial form values in the redux state
  useEffect(() => {
    dispatch(
      candidatesActions.setFilterFormData({
        savedStatus: "all",
        startDate: defaultStartDate.toISOString(),
      })
    );
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

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

  const validateRedshifts = () => {
    formState = getValues({ nest: true });
    // Need both ends of the range
    return (
      formState.redshiftMinimum !== null &&
      formState.redshiftMaximum !== null &&
      parseFloat(formState.redshiftMaximum) >
        parseFloat(formState.redshiftMinimum)
    );
  };

  const onSubmit = async (formData) => {
    setQueryInProgress(true);
    const groupIDs = userAccessibleGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter(
      (ID, idx) => formData.groupIDs[idx]
    );
    const data = {
      groupIDs: selectedGroupIDs,
      savedStatus: formData.savedStatus,
    };
    // decide if to show rejected candidates
    if (formData.rejectedStatus === "hide") {
      data.listNameReject = "rejected_candidates";
    }
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
    if (annotationFilterList) {
      data.annotationFilterList = annotationFilterList;
    }
    setFilterGroups(
      userAccessibleGroups.filter((g) => selectedGroupIDs.includes(g.id))
    );

    // Clear annotation sort params
    await dispatch(candidatesActions.setCandidatesAnnotationSortOptions(null));
    setSortOrder(null);

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
                  value={value ? dayjs.utc(value) : null}
                  onChange={(e, date) =>
                    date ? onChange(dayjs.utc(date)) : onChange(date)
                  }
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
              defaultValue={defaultStartDate}
            />
            &nbsp;
            <Controller
              render={({ onChange, value }) => (
                <KeyboardDateTimePicker
                  value={value ? dayjs.utc(value) : null}
                  onChange={(e, date) =>
                    date ? onChange(dayjs.utc(date)) : onChange(date)
                  }
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
              defaultValue={defaultEndDate}
            />
          </div>
          <div className={classes.savedStatusSelect}>
            <InputLabel id="savedStatusSelectLabel">
              Show only candidates which passed a filter from the selected
              groups...
            </InputLabel>
            <Controller
              labelId="savedStatusSelectLabel"
              as={Select}
              name="savedStatus"
              control={control}
              input={<Input data-testid="savedStatusSelect" />}
              defaultValue={defaultScanningProfile?.savedStatus || "all"}
            >
              {savedStatusSelectOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Controller>
          </div>
          <div className={classes.formRow}>
            <InputLabel id="classifications-select-label">
              Classifications
            </InputLabel>
            <Controller
              labelId="classifications-select-label"
              render={({ onChange, value }) => (
                <Select
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
              defaultValue={defaultScanningProfile?.classifications || []}
            />
          </div>
          <div className={classes.formRow}>
            {errors.redshiftMinimum && (
              <FormValidationError message="Both redshift minimum/maximum must be defined, with maximum > minimum" />
            )}
            <InputLabel id="redshift-select-label">Redshift</InputLabel>
            <div className={classes.redshiftField}>
              <Controller
                render={({ onChange, value }) => (
                  <TextField
                    id="minimum-redshift"
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
                labelId="redshift-select-label"
                control={control}
                rules={{ validate: validateRedshifts }}
                defaultValue={defaultScanningProfile?.redshiftMinimum || ""}
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
                defaultValue={defaultScanningProfile?.redshiftMaximum || ""}
              />
            </div>
          </div>
          <div className={classes.formRow}>
            <InputLabel id="rejectedCandidatesLabel">
              Show/hide rejected candidates
            </InputLabel>
            <Controller
              labelId="rejectedCandidatesLabel"
              as={Select}
              name="rejectedStatus"
              control={control}
              input={<Input data-testid="rejectedStatusSelect" />}
              defaultValue={defaultScanningProfile?.rejectedStatus || "hide"}
            >
              {rejectedStatusSelectOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Controller>
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
                          onChange={(event) => {
                            onChange(event.target.checked);
                            // Let parent component know program selection has changed
                            const groupIDs = userAccessibleGroups.map(
                              (g) => g.id
                            );
                            const selectedGroupIDs = groupIDs.filter(
                              (ID, i) => getValues({ nest: true }).groupIDs[i]
                            );
                            setFilterGroups(
                              userAccessibleGroups.filter((g) =>
                                selectedGroupIDs.includes(g.id)
                              )
                            );
                          }}
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
  setSortOrder: PropTypes.func.isRequired,
  annotationFilterList: PropTypes.string,
};
FilterCandidateList.defaultProps = {
  annotationFilterList: null,
};

export default FilterCandidateList;
