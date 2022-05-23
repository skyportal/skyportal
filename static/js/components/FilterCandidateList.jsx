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
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import TextField from "@material-ui/core/TextField";
import Tooltip from "@material-ui/core/Tooltip";
import { Typography } from "@material-ui/core";
import { makeStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as candidatesActions from "../ducks/candidates";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";
import CandidatesPreferences from "./CandidatesPreferences";
import FormValidationError from "./FormValidationError";
import { allowedClasses } from "./ClassificationForm";
import ClassificationSelect from "./ClassificationSelect";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  filterListContainer: {
    padding: "1rem",
    display: "flex",
    flexFlow: "column nowrap",
  },
  buttonsRow: {
    marginTop: "1rem",
    display: "flex",
    flexFlow: "row wrap",
    "& > div": {
      marginRight: "1rem",
    },
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
  annotationSorting: {
    "& label": {
      marginTop: "1rem",
    },
  },
}));

const rejectedStatusSelectOptions = [
  { value: "hide", label: "Hide rejected candidates" },
  { value: "show", label: "Show rejected candidates" },
];

const savedStatusSelectOptions = [
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

  const availableAnnotationsInfo = useSelector(
    (state) => state.candidates.annotationsInfo
  );
  const dispatch = useDispatch();
  useEffect(() => {
    // Grab the available annotation fields for filtering
    if (!availableAnnotationsInfo) {
      dispatch(candidatesActions.fetchAnnotationsInfo());
    }
  }, [dispatch, availableAnnotationsInfo]);

  const { scanningProfiles } = useSelector(
    (state) => state.profile.preferences
  );

  const defaultScanningProfile = scanningProfiles?.find(
    (profile) => profile.default
  );
  const [selectedScanningProfile, setSelectedScanningProfile] = useState(
    defaultScanningProfile
  );

  useEffect(() => {
    // Once the default profile is fully fetched, set it to the selected.
    //
    // This effect can also trigger on an edit action dispatched by
    // CandidatesPreferencesForm.jsx, where the default profile may not
    // necessarily change, but is replaced by a copy of itself (since the
    // entirety of the preferences.scanningProfiles array in the Redux store
    // is replaced by the profileActions.updateUserPreferences() call)
    // To make sure we don't override the currently loaded profile in this
    // scenario (as it may be different from the default), we assign
    // the selectedScanningProfile if it exists already or the default
    // otherwise (indicating the first render of the page)
    setSelectedScanningProfile(
      selectedScanningProfile || defaultScanningProfile
    );

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [defaultScanningProfile]);

  const defaultStartDate = new Date();
  let defaultEndDate = null;
  if (selectedScanningProfile?.timeRange) {
    defaultEndDate = new Date();
    defaultStartDate.setHours(
      defaultStartDate.getHours() -
        parseInt(selectedScanningProfile.timeRange, 10)
    );
  } else {
    defaultStartDate.setDate(defaultStartDate.getDate() - 1);
  }

  // Get unique classification names, in alphabetical order
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  let classifications = [];
  latestTaxonomyList?.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy)?.map(
      (option) => option.class
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();

  const [selectedClassifications, setSelectedClassifications] = useState(
    selectedScanningProfile?.classifications || []
  );
  const [selectedAnnotationOrigin, setSelectedAnnotationOrigin] = useState(
    selectedScanningProfile?.sortingOrigin
  );

  const { handleSubmit, getValues, control, errors, reset, setValue } = useForm(
    {
      startDate: defaultStartDate,
      endDate: defaultEndDate,
    }
  );

  useEffect(() => {
    const selectedGroupIDs = Array(userAccessibleGroups.length).fill(false);
    const groupIDs = userAccessibleGroups?.map((g) => g.id);
    groupIDs?.forEach((ID, i) => {
      selectedGroupIDs[i] = selectedScanningProfile?.groupIDs.includes(ID);
    });

    const resetFormFields = async () => {
      // Wait for the selected annotation origin state to update before setting
      // the new default form fields, so that the sortingKey options list can
      // update
      await setSelectedAnnotationOrigin(selectedScanningProfile?.sortingOrigin);

      reset({
        groupIDs: selectedGroupIDs,
        startDate: defaultStartDate,
        endDate: defaultEndDate,
        classifications: selectedScanningProfile?.classifications || [],
        redshiftMinimum: selectedScanningProfile?.redshiftMinimum || "",
        redshiftMaximum: selectedScanningProfile?.redshiftMaximum || "",
        rejectedStatus: selectedScanningProfile?.rejectedStatus || "hide",
        savedStatus: selectedScanningProfile?.savedStatus || "all",
        sortingOrigin: selectedScanningProfile?.sortingOrigin || "",
        sortingKey: selectedScanningProfile?.sortingKey || "",
        sortingOrder: selectedScanningProfile?.sortingOrder || "",
      });
    };

    resetFormFields();
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reset, selectedScanningProfile, userAccessibleGroups]);

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
    return formState.groupIDs?.filter((value) => Boolean(value)).length >= 1;
  };

  const validateDates = () => {
    formState = getValues({ nest: true });
    if (!!formState.startDate && !!formState.endDate) {
      return formState.startDate <= formState.endDate;
    }
    return true;
  };

  const validateSorting = () => {
    formState = getValues({ nest: true });
    return (
      // All left empty
      formState.sortingOrigin === "" ||
      // Or all filled out
      (formState.sortingOrigin !== "" &&
        formState.sortingKey !== "" &&
        formState.sortingOrder !== "")
    );
  };

  const onSubmit = async (formData) => {
    setQueryInProgress(true);
    const groupIDs = userAccessibleGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs?.filter(
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
    if (selectedClassifications.length > 0) {
      data.classifications = selectedClassifications;
    }
    if (formData.redshiftMinimum) {
      data.minRedshift = formData.redshiftMinimum;
    }
    if (formData.redshiftMaximum) {
      data.maxRedshift = formData.redshiftMaximum;
    }
    if (formData.sortingOrigin) {
      data.sortingOrigin = formData.sortingOrigin;
      data.sortingKey = formData.sortingKey;
      data.sortingOrder = formData.sortingOrder;
    }

    // Submit a new search for candidates
    if (annotationFilterList) {
      data.annotationFilterList = annotationFilterList;
    }
    setFilterGroups(
      userAccessibleGroups?.filter((g) => selectedGroupIDs.includes(g.id))
    );
    const fetchParams = { ...data };

    // Clear annotation sort params, if a default sort is not defined
    if (selectedScanningProfile?.sortingOrigin === undefined) {
      await dispatch(
        candidatesActions.setCandidatesAnnotationSortOptions(null)
      );
      setSortOrder(null);
    } else {
      fetchParams.sortByAnnotationOrigin =
        selectedScanningProfile.sortingOrigin;
      fetchParams.sortByAnnotationKey = selectedScanningProfile.sortingKey;
      fetchParams.sortByAnnotationOrder = selectedScanningProfile.sortingOrder;
    }

    // Save form-specific data, formatted for the API query
    await dispatch(candidatesActions.setFilterFormData(data));

    await dispatch(
      candidatesActions.fetchCandidates({
        pageNumber: 1,
        numPerPage,
        ...fetchParams,
      })
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
              defaultValue={selectedScanningProfile?.savedStatus || "all"}
            >
              {savedStatusSelectOptions?.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Controller>
          </div>
          <ClassificationSelect
            selectedClassifications={selectedClassifications}
            setSelectedClassifications={setSelectedClassifications}
            showShortcuts
          />
          <div className={classes.formRow}>
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
                defaultValue={selectedScanningProfile?.redshiftMinimum || ""}
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
                defaultValue={selectedScanningProfile?.redshiftMaximum || ""}
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
              defaultValue={selectedScanningProfile?.rejectedStatus || "hide"}
            >
              {rejectedStatusSelectOptions?.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Controller>
          </div>
          <div className={`${classes.formRow} ${classes.annotationSorting}`}>
            {errors.sortingOrigin && (
              <FormValidationError message="All sorting fields must be left empty or all filled out" />
            )}
            <Responsive
              element={FoldBox}
              title="Annotation Sorting"
              mobileProps={{ folded: true }}
            >
              <InputLabel id="sorting-select-label">
                Annotation Origin
              </InputLabel>
              <Controller
                labelId="sorting-select-label"
                name="sortingOrigin"
                control={control}
                render={({ onChange, value }) => (
                  <Select
                    id="annotationSortingOriginSelect"
                    value={value}
                    onChange={(event) => {
                      setSelectedAnnotationOrigin(event.target.value);
                      setValue("sortingKey", "");
                      onChange(event.target.value);
                    }}
                    input={
                      <Input data-testid="annotationSortingOriginSelect" />
                    }
                  >
                    {availableAnnotationsInfo ? (
                      [""]
                        .concat(Object.keys(availableAnnotationsInfo))
                        .map((option) => (
                          <MenuItem key={option} value={option}>
                            {option === "" ? "None" : option}
                          </MenuItem>
                        ))
                    ) : (
                      <div />
                    )}
                  </Select>
                )}
                rules={{ validate: validateSorting }}
                defaultValue={selectedAnnotationOrigin || ""}
              />
              {selectedAnnotationOrigin ? (
                <>
                  <InputLabel id="sorting-select-key-label">
                    Annotation Key
                  </InputLabel>
                  <Controller
                    labelId="sorting-select-key-label"
                    as={Select}
                    name="sortingKey"
                    control={control}
                    input={<Input data-testid="annotationSortingKeySelect" />}
                    defaultValue={selectedScanningProfile?.sortingKey || ""}
                  >
                    {availableAnnotationsInfo ? (
                      availableAnnotationsInfo[selectedAnnotationOrigin]?.map(
                        (option) => (
                          <MenuItem
                            key={Object.keys(option)[0]}
                            value={Object.keys(option)[0]}
                          >
                            {Object.keys(option)[0]}
                          </MenuItem>
                        )
                      )
                    ) : (
                      <div />
                    )}
                  </Controller>
                  <InputLabel id="sorting-select-order-label">
                    Annotation Sort Order
                  </InputLabel>
                  <Controller
                    labelId="sorting-select-order-label"
                    as={Select}
                    name="sortingOrder"
                    control={control}
                    input={<Input data-testid="annotationSortingOrderSelect" />}
                    defaultValue={selectedScanningProfile?.sortingOrder || ""}
                  >
                    <MenuItem key="desc" value="desc">
                      Descending
                    </MenuItem>
                    <MenuItem key="asc" value="asc">
                      Ascending
                    </MenuItem>
                  </Controller>
                </>
              ) : (
                <div />
              )}
            </Responsive>
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
                            const selectedGroupIDs = groupIDs?.filter(
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
          <div className={classes.formRow}>
            <Typography variant="subtitle2">
              Selected scanning profile:&nbsp;
              {selectedScanningProfile
                ? selectedScanningProfile.name || "No name"
                : "None"}
            </Typography>
            <Typography variant="subtitle2">
              Click <q>Manage Scanning Profiles</q> to select a new profile.
            </Typography>
          </div>
          <div className={classes.buttonsRow}>
            <CandidatesPreferences
              selectedScanningProfile={selectedScanningProfile}
              setSelectedScanningProfile={setSelectedScanningProfile}
            />
            <div>
              <Tooltip title="Search results are cached between pagination requests, and are re-computed each time this Search button is clicked">
                <Button
                  variant="contained"
                  type="submit"
                  endIcon={<SearchIcon />}
                  color="primary"
                >
                  Search
                </Button>
              </Tooltip>
            </div>
          </div>
        </form>
        <br />
      </div>
    </Paper>
  );
};
FilterCandidateList.propTypes = {
  userAccessibleGroups: PropTypes.arrayOf(
    PropTypes.shape({
      single_user_group: PropTypes.bool.isRequired,
      created_at: PropTypes.string.isRequired,
      id: PropTypes.number.isRequired,
      modified: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      nickname: PropTypes.string,
      private: PropTypes.bool.isRequired,
      description: PropTypes.string,
    })
  ).isRequired,
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
