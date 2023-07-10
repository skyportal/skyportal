import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import PropTypes from "prop-types";

import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import Paper from "@mui/material/Paper";
import SearchIcon from "@mui/icons-material/Search";
import Input from "@mui/material/Input";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
import Tooltip from "@mui/material/Tooltip";
import { Typography } from "@mui/material";
import makeStyles from "@mui/styles/makeStyles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as candidatesActions from "../ducks/candidates";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";
import CandidatesPreferences from "./CandidatesPreferences";
import FormValidationError from "./FormValidationError";
import { allowedClasses } from "./ClassificationForm";
import ClassificationSelect from "./ClassificationSelect";
import Button from "./Button";

import * as gcnEventsActions from "../ducks/gcnEvents";

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
  gcnFormRow: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gridGap: "0.5rem",
    marginTop: "1rem",
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

  const { scanningProfiles, useAMPM } = useSelector(
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

  const gcnEvents = useSelector((state) => state.gcnEvents);

  const gcnEventsLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  gcnEvents?.events.forEach((gcnEvent) => {
    gcnEventsLookUp[gcnEvent.id] = gcnEvent;
  });

  const [selectedGcnEventId, setSelectedGcnEventId] = useState(null);

  useEffect(() => {
    dispatch(gcnEventsActions.fetchGcnEvents());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const {
    handleSubmit,
    getValues,
    control,
    reset,
    formState: { errors },
  } = useForm({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
  });

  useEffect(() => {
    // set the default values for the firstDetectionAfter and lastDetectionBefore

    let defaultFirstDetectionAfter = " ";
    let defaultLastDetectionBefore = " ";
    if (selectedGcnEventId && selectedGcnEventId !== "") {
      defaultFirstDetectionAfter = dayjs
        .utc(gcnEventsLookUp[selectedGcnEventId]?.dateobs)
        .format("YYYY-MM-DD HH:mm:ss");
      defaultLastDetectionBefore = dayjs
        .utc(gcnEventsLookUp[selectedGcnEventId]?.dateobs)
        .add(7, "day")
        .format("YYYY-MM-DD HH:mm:ss");
    }
    const newFormData = {
      ...getValues(),
      firstDetectionAfter: defaultFirstDetectionAfter,
      lastDetectionBefore: defaultLastDetectionBefore,
    };
    if (!selectedGcnEventId) {
      delete newFormData.firstDetectionAfter;
      delete newFormData.lastDetectionBefore;
      delete newFormData.numberDetections;
      delete newFormData.localizationCumprob;
    } else {
      newFormData.numberDetections = 1;
      newFormData.localizationCumprob = 0.95;
    }

    reset(newFormData);
  }, [selectedGcnEventId]);

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
        // savedStatus: "all",
        startDate: defaultStartDate.toISOString(),
      })
    );
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  let formState = getValues();

  const validateGroups = () => {
    formState = getValues();
    return formState.groupIDs?.filter((value) => Boolean(value)).length >= 1;
  };

  const validateDates = () => {
    formState = getValues();
    if (!!formState.startDate && !!formState.endDate) {
      return formState.startDate <= formState.endDate;
    }
    return true;
  };

  const validateSorting = () => {
    formState = getValues();
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
    if (formData.gcneventid !== "" || formData.localizationid !== "") {
      // data.gcneventid = formData.gcneventid;
      // data.localizationid = formData.localizationid;
      data.localizationDateobs = gcnEventsLookUp[formData.gcneventid]?.dateobs;
      data.localizationName = gcnEventsLookUp[
        formData.gcneventid
      ]?.localizations?.filter(
        (l) => l.id === formData.localizationid
      )[0]?.localization_name;
      if (formData.localizationCumprob) {
        data.localizationCumprob = formData.localizationCumprob;
      }
      if (formData.firstDetectionAfter) {
        data.firstDetectionAfter = formData.firstDetectionAfter;
      }
      if (formData.lastDetectionBefore) {
        data.lastDetectionBefore = formData.lastDetectionBefore;
      }
      if (formData.numberDetections) {
        data.numberDetections = formData.numberDetections;
      }
      if (formData.excludeForcedPhotometry) {
        data.excludeForcedPhotometry = formData.excludeForcedPhotometry;
      }
    }
    if (formData.sortingOrigin) {
      data.sortByAnnotationOrigin = formData.sortingOrigin;
      data.sortByAnnotationKey = formData.sortingKey;
      data.sortByAnnotationOrder = formData.sortingOrder;
    } else if (selectedScanningProfile?.sortingOrigin === undefined) {
      // Clear annotation sort params, if a default sort is not defined
      await dispatch(
        candidatesActions.setCandidatesAnnotationSortOptions(null)
      );
      setSortOrder(null);
    } else {
      data.sortByAnnotationOrigin = selectedScanningProfile.sortingOrigin;
      data.sortByAnnotationKey = selectedScanningProfile.sortingKey;
      data.sortByAnnotationOrder = selectedScanningProfile.sortingOrder;
    }

    // Submit a new search for candidates
    if (annotationFilterList) {
      data.annotationFilterList = annotationFilterList;
    }
    setFilterGroups(
      userAccessibleGroups?.filter((g) => selectedGroupIDs.includes(g.id))
    );
    const fetchParams = { ...data };

    if (data.sortByAnnotationOrigin) {
      setSortOrder(data.sortByAnnotationOrder);
      await dispatch(
        candidatesActions.setCandidatesAnnotationSortOptions({
          key: data.sortByAnnotationKey,
          origin: data.sortByAnnotationOrigin,
          order: data.sortByAnnotationOrder,
        })
      );
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
              render={({ field: { onChange, value } }) => (
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <DateTimePicker
                    value={value}
                    onChange={(newValue) => onChange(newValue)}
                    label="Start (Local Time)"
                    showTodayButton={false}
                    ampm={useAMPM}
                    renderInput={(params) => (
                      /* eslint-disable-next-line react/jsx-props-no-spreading */
                      <TextField id="startDatePicker" {...params} />
                    )}
                  />
                </LocalizationProvider>
              )}
              rules={{ validate: validateDates }}
              name="startDate"
              control={control}
              defaultValue={defaultStartDate}
            />
            &nbsp;
            <Controller
              render={({ field: { onChange, value } }) => (
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <DateTimePicker
                    value={value}
                    onChange={(newValue) => onChange(newValue)}
                    label="End (Local Time)"
                    showTodayButton={false}
                    ampm={useAMPM}
                    renderInput={(props) => (
                      /* eslint-disable-next-line react/jsx-props-no-spreading */
                      <TextField id="endDatePicker" {...props} />
                    )}
                  />
                </LocalizationProvider>
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
              name="savedStatus"
              control={control}
              input={<Input data-testid="savedStatusSelect" />}
              render={({ field: { onChange, value } }) => (
                <Select
                  key={
                    selectedScanningProfile?.savedStatus
                      ? "notLoadedYet"
                      : "loaded"
                  }
                  onChange={onChange}
                  value={value}
                  defaultValue={selectedScanningProfile?.savedStatus || "all"}
                  data-testid="savedStatusSelect"
                >
                  {savedStatusSelectOptions?.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              )}
            />
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
                render={({ field: { onChange, value } }) => (
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
                    defaultValue={
                      selectedScanningProfile?.redshiftMinimum || ""
                    }
                  />
                )}
                name="redshiftMinimum"
                labelId="redshift-select-label"
                control={control}
              />
            </div>
            <div className={classes.redshiftField}>
              <Controller
                render={({ field: { onChange, value } }) => (
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
                    defaultValue={
                      selectedScanningProfile?.redshiftMaximum || ""
                    }
                  />
                )}
                name="redshiftMaximum"
                control={control}
              />
            </div>
          </div>
          <div className={classes.formRow}>
            <InputLabel id="rejectedCandidatesLabel">
              Show/hide rejected candidates
            </InputLabel>
            <Controller
              labelId="rejectedCandidatesLabel"
              name="rejectedStatus"
              control={control}
              input={<Input data-testid="rejectedStatusSelect" />}
              render={({ field: { onChange, value } }) => (
                <Select
                  defaultValue={
                    selectedScanningProfile?.rejectedStatus || "hide"
                  }
                  onChange={onChange}
                  value={value}
                  data-testid="rejectedStatusSelect"
                >
                  {rejectedStatusSelectOptions?.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              )}
            />
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
                input={<Input data-testid="annotationSortingOriginSelect" />}
                render={({ field: { onChange, value } }) => (
                  <Select
                    id="annotationSortingOriginSelect"
                    key={
                      selectedScanningProfile?.sortingOrigin
                        ? "notLoadedYet"
                        : "loaded"
                    }
                    value={value}
                    onChange={(event) => {
                      setSelectedAnnotationOrigin(event.target.value);
                      onChange(event.target.value);
                    }}
                    defaultValue={selectedScanningProfile?.sortingOrigin || ""}
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
              />
              {selectedAnnotationOrigin ? (
                <>
                  <InputLabel id="sorting-select-key-label">
                    Annotation Key
                  </InputLabel>
                  <Controller
                    labelId="sorting-select-key-label"
                    name="sortingKey"
                    control={control}
                    input={<Input data-testid="annotationSortingKeySelect" />}
                    render={({ field: { onChange, value } }) => (
                      <Select
                        id="annotationSortingKeySelect"
                        defaultValue={selectedScanningProfile?.sortingKey || ""}
                        onChange={onChange}
                        value={value}
                      >
                        {availableAnnotationsInfo ? (
                          availableAnnotationsInfo[
                            selectedAnnotationOrigin
                          ]?.map((option) => (
                            <MenuItem
                              key={Object.keys(option)[0]}
                              value={Object.keys(option)[0]}
                            >
                              {Object.keys(option)[0]}
                            </MenuItem>
                          ))
                        ) : (
                          <div />
                        )}
                      </Select>
                    )}
                  />
                  <InputLabel id="sorting-select-order-label">
                    Annotation Sort Order
                  </InputLabel>
                  <Controller
                    labelId="sorting-select-order-label"
                    name="sortingOrder"
                    control={control}
                    input={<Input data-testid="annotationSortingOrderSelect" />}
                    render={({ field: { onChange, value } }) => (
                      <Select
                        id="annotationSortingOrderSelect"
                        defaultValue={
                          selectedScanningProfile?.sortingOrder || ""
                        }
                        onChange={onChange}
                        value={value}
                      >
                        <MenuItem key="desc" value="desc">
                          Descending
                        </MenuItem>
                        <MenuItem key="asc" value="asc">
                          Ascending
                        </MenuItem>
                      </Select>
                    )}
                  />
                </>
              ) : (
                <div />
              )}
            </Responsive>
          </div>
          <div>
            <Responsive element={FoldBox} title="GCN Filtering" folded>
              {gcnEvents?.events ? (
                <>
                  <div className={classes.gcnFormRow}>
                    <Controller
                      render={({ field: { value } }) => (
                        <Autocomplete
                          id="gcn-event-filtering"
                          options={gcnEvents?.events}
                          value={
                            gcnEvents?.events.find(
                              (option) => option.id === value
                            ) || null
                          }
                          getOptionLabel={(option) =>
                            `${option?.dateobs} ${
                              option?.aliases?.length > 0
                                ? `(${option?.aliases})`
                                : ""
                            }` || ""
                          }
                          className={classes.select}
                          // eslint-disable-next-line no-shadow
                          onInputChange={(event, value) => {
                            if (
                              event?.type === "change" &&
                              value !== null &&
                              value !== ""
                            ) {
                              dispatch(
                                gcnEventsActions.fetchGcnEvents({
                                  partialdateobs: value,
                                })
                              );
                            }
                          }}
                          onChange={(event, newValue) => {
                            if (newValue !== null) {
                              reset({
                                ...getValues(),
                                gcneventid:
                                  newValue.id === -1 ? "" : newValue.id,
                                localizationid:
                                  newValue.id === -1
                                    ? ""
                                    : gcnEventsLookUp[newValue.id]
                                        ?.localizations[0]?.id || "",
                              });
                              setSelectedGcnEventId(newValue.id);
                            } else {
                              reset({
                                ...getValues(),
                                gcneventid: "",
                                localizationid: "",
                              });
                              setSelectedGcnEventId("");
                            }
                          }}
                          renderInput={(params) => (
                            <TextField {...params} label="Dateobs/Name" />
                          )}
                        />
                      )}
                      name="gcneventid"
                      control={control}
                      defaultValue=""
                    />
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <Select
                          inputProps={{
                            MenuProps: { disableScrollLock: true },
                          }}
                          labelId="localizationSelectLabel"
                          value={value || ""}
                          onChange={(event) => {
                            onChange(event.target.value);
                          }}
                          className={classes.select}
                          disabled={!selectedGcnEventId}
                        >
                          {gcnEventsLookUp[
                            selectedGcnEventId
                          ]?.localizations?.map((localization) => (
                            <MenuItem
                              value={localization.id}
                              key={localization.id}
                              className={classes.selectItem}
                            >
                              {`${localization.localization_name}`}
                            </MenuItem>
                          ))}
                        </Select>
                      )}
                      name="localizationid"
                      control={control}
                      defaultValue=""
                    />
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <TextField
                          id="cumprob"
                          label="Cumulative Probability"
                          type="number"
                          value={value}
                          inputProps={{ step: 0.01, min: 0, max: 1 }}
                          onChange={(event) => onChange(event.target.value)}
                          defaultValue={0.95}
                        />
                      )}
                      name="localizationCumprob"
                      control={control}
                    />
                  </div>
                  <div className={classes.gcnFormRow}>
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <TextField
                          type="text"
                          value={value}
                          onChange={(event) => onChange(event.target.value)}
                          label="First Detection After (UTC)"
                          defaultValue=" "
                        />
                      )}
                      name="firstDetectionAfter"
                      control={control}
                    />
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <TextField
                          type="text"
                          value={value}
                          onChange={(event) => onChange(event.target.value)}
                          label="Last Detection Before (UTC)"
                          defaultValue=" "
                        />
                      )}
                      name="lastDetectionBefore"
                      control={control}
                    />
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <TextField
                          id="minNbDect"
                          label="Minimum Number of Detections"
                          type="number"
                          value={value}
                          inputProps={{ step: 1, min: 0 }}
                          onChange={(event) => onChange(event.target.value)}
                          defaultValue={1}
                        />
                      )}
                      name="numberDetections"
                      control={control}
                    />
                  </div>
                  <div className={classes.gcnFormRow}>
                    <FormControlLabel
                      control={
                        <Controller
                          render={({ field: { onChange, value } }) => (
                            <Checkbox
                              onChange={(event) => {
                                onChange(event.target.checked);
                              }}
                              checked={value}
                            />
                          )}
                          name="excludeForcedPhotometry"
                          control={control}
                          defaultValue
                        />
                      }
                      label="Exclude Forced Photometry"
                    />
                  </div>
                </>
              ) : (
                <p> Loading events</p>
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
                      render={({ field: { onChange, value } }) => (
                        <Checkbox
                          onChange={(event) => {
                            onChange(event.target.checked);
                            // Let parent component know program selection has changed
                            const groupIDs = userAccessibleGroups.map(
                              (g) => g.id
                            );
                            const selectedGroupIDs = groupIDs?.filter(
                              (ID, i) => getValues().groupIDs[i]
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
                <Button primary type="submit" endIcon={<SearchIcon />}>
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
