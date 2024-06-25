import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";
import PropTypes from "prop-types";

import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import IconButton from "@mui/material/IconButton";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import Paper from "@mui/material/Paper";
import SearchIcon from "@mui/icons-material/Search";
import Input from "@mui/material/Input";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
import Tooltip from "@mui/material/Tooltip";
import Grid from "@mui/material/Grid";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as candidatesActions from "../../ducks/candidates";
import * as gcnEventsActions from "../../ducks/gcnEvents";
import CandidatesPreferences from "./CandidatesPreferences";
import FormValidationError from "../FormValidationError";
import { allowedClasses } from "../classification/ClassificationForm";
import ClassificationSelect from "../classification/ClassificationSelect";
import Button from "../Button";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  filterListContainer: {
    padding: "1rem 1rem 0 1rem",
    display: "flex",
    flexFlow: "column nowrap",
  },
  headerRow: {
    display: "flex",
    flexFlow: "row wrap",
    columnGap: "1rem",
    marginBottom: "0.5rem",
    alignItems: "center",
    justifyContent: "space-between",
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
  gcnGrid: {
    marginTop: "0.5rem",
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gridColumnGap: "0.75rem",
    gridRowGap: "1rem",
  },
  redshiftField: {
    display: "inline-block",
    marginRight: "0.5rem",
  },
  savedStatusSelect: {
    margin: 0,
    "& input": {
      fontSize: "1rem",
    },
  },
  annotationSorting: {
    paddingTop: "0.5rem",
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: "0.5rem",
  },
  redshiftFiltering: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.5rem",
  },
  savedFiltering: {
    paddingTop: "1rem",
    display: "grid",
    [theme.breakpoints.down("sm")]: {
      gridTemplateColumns: "1fr",
    },
    [theme.breakpoints.up("md")]: {
      gridTemplateColumns: "2fr 1fr",
    },
    gap: "0.5rem",
  },
  rejectCandidatesSelect: {
    display: "flex",
    alignItems: "center",
    [theme.breakpoints.down("sm")]: {
      paddingTop: 0,
    },
    [theme.breakpoints.up("md")]: {
      paddingTop: "1.5rem",
    },
  },
  timeRange: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.5rem",
  },
  title: {
    fontSize: "1.1rem",
  },
  body: {
    fontSize: "1rem",
    lineHeight: "1.1rem",
  },
  groupOptions: {
    paddingTop: "0.5rem",
    display: "flex",
    flexFlow: "row wrap",
    alignItems: "flex-start",
    columnGap: "2rem",
    rowGap: "1rem",
  },
  simplePadding: {
    padding: "1rem",
  },
  reset: {
    // hide on small screens
    [theme.breakpoints.down("lg")]: {
      display: "none",
    },
    [theme.breakpoints.up("lg")]: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    },
  },
}));

const savedStatusSelectOptions = [
  { value: "all", label: "regardless of saved status" },
  { value: "savedToAllSelected", label: "saved to all selected groups" },
  {
    value: "savedToAnySelected",
    label: "saved to at least one of the selected groups",
  },
  {
    value: "savedToAnyAccessible",
    label: "saved to at least one group I have access to",
  },
  {
    value: "notSavedToAnyAccessible",
    label: "not saved to any of group I have access to",
  },
  {
    value: "notSavedToAnySelected",
    label: "not saved to any of the selected groups",
  },
  {
    value: "notSavedToAllSelected",
    label: "not saved to all of the selected groups",
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
    (state) => state.candidates.annotationsInfo,
  );
  const dispatch = useDispatch();

  const { scanningProfiles, useAMPM } = useSelector(
    (state) => state.profile.preferences,
  );

  const defaultScanningProfile = scanningProfiles?.find(
    (profile) => profile.default,
  );
  const [selectedScanningProfile, setSelectedScanningProfile] = useState(
    defaultScanningProfile,
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
      selectedScanningProfile || defaultScanningProfile,
    );

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [defaultScanningProfile]);

  const defaultStartDate = new Date();
  let defaultEndDate = null;
  if (selectedScanningProfile?.timeRange) {
    defaultEndDate = new Date();
    defaultStartDate.setHours(
      defaultStartDate.getHours() -
        parseInt(selectedScanningProfile.timeRange, 10),
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
      (option) => option.class,
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();

  const [selectedClassifications, setSelectedClassifications] = useState(
    selectedScanningProfile?.classifications || [],
  );

  const gcnEvents = useSelector((state) => state.gcnEvents);

  const gcnEventsLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  gcnEvents?.events.forEach((gcnEvent) => {
    gcnEventsLookUp[gcnEvent.id] = gcnEvent;
  });

  const [selectedGcnEventId, setSelectedGcnEventId] = useState(null);

  const [filterGroupsInput, setFilterGroupsInput] = useState("");

  const [filterGroupOptions, setFilterGroupOptions] = useState([]);

  const [showAllGroups, setShowAllGroups] = useState(true);

  const [annotationSortingKeyOptions, setAnnotationSortingKeyOptions] =
    useState([]);

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

  const resetFormFields = (startDate, endDate, scanningProfile) => {
    if (scanningProfile?.groupIDs && userAccessibleGroups.length > 0) {
      setFilterGroups(
        userAccessibleGroups.filter((group) =>
          selectedScanningProfile.groupIDs.includes(group.id),
        ),
      );
    }
    setSelectedGcnEventId("");
    setSelectedClassifications(scanningProfile?.classifications || []);
    if (availableAnnotationsInfo) {
      const newOptions = scanningProfile?.sortingOrigin
        ? (availableAnnotationsInfo[scanningProfile?.sortingOrigin] || [])
            .map((annotation) => Object.keys(annotation || {}))
            .flat()
        : [];
      setAnnotationSortingKeyOptions(newOptions);
    }
    reset({
      startDate,
      endDate,
      groupIDs: scanningProfile?.groupIDs || [],
      classifications: scanningProfile?.classifications || [],
      redshiftMinimum: scanningProfile?.redshiftMinimum || "",
      redshiftMaximum: scanningProfile?.redshiftMaximum || "",
      rejectedStatus: scanningProfile?.rejectedStatus || "hide",
      savedStatus: scanningProfile?.savedStatus || "all",
      sortingOrigin: scanningProfile?.sortingOrigin || "",
      sortingKey: scanningProfile?.sortingKey || "",
      sortingOrder: scanningProfile?.sortingOrder || "",
      gcneventid: "",
      localizationid: "",
      firstDetectionAfter: "",
      lastDetectionBefore: "",
      numberDetections: "",
      localizationCumprob: "",
    });
  };

  useEffect(() => {
    resetFormFields(defaultStartDate, defaultEndDate, selectedScanningProfile);
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    reset,
    selectedScanningProfile,
    userAccessibleGroups,
    availableAnnotationsInfo,
  ]);

  // Set initial form values in the redux state
  useEffect(() => {
    dispatch(
      candidatesActions.setFilterFormData({
        // savedStatus: "all",
        startDate: defaultStartDate.toISOString(),
      }),
    );
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  useEffect(() => {
    // when the search bar for groups is updated, update the list of groups
    if (filterGroupsInput) {
      setFilterGroupOptions(
        userAccessibleGroups.filter((group) =>
          group.name.toLowerCase().includes(filterGroupsInput.toLowerCase()),
        ),
      );
    } else {
      // if the bar is empty show all groups
      setFilterGroupOptions(userAccessibleGroups);
    }
  }, [filterGroupsInput, userAccessibleGroups]);

  let formState = getValues();

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
      formState.sortingOrigin === null ||
      // Or all filled out
      (formState.sortingOrigin !== null &&
        formState.sortingKey !== null &&
        formState.sortingOrder !== null)
    );
  };

  const onSubmit = async (formData) => {
    setQueryInProgress(true);
    const data = {
      groupIDs: formData.groupIDs,
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
        (l) => l.id === formData.localizationid,
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
      if (formData.requireDetections === false) {
        data.requireDetections = false;
      }
      if (formData.excludeForcedPhotometry) {
        data.excludeForcedPhotometry = formData.excludeForcedPhotometry;
      }
    }
    if (formData.sortingOrigin) {
      data.sortByAnnotationOrigin = formData.sortingOrigin;
      data.sortByAnnotationKey = formData.sortingKey;
      data.sortByAnnotationOrder = formData.sortingOrder;
    } else {
      // Clear annotation sort params, if a default sort is not defined
      await dispatch(
        candidatesActions.setCandidatesAnnotationSortOptions(null),
      );
      setSortOrder(null);
    }

    // Submit a new search for candidates
    if (annotationFilterList) {
      data.annotationFilterList = annotationFilterList;
    }
    setFilterGroups(
      userAccessibleGroups?.filter((g) => data.groupIDs.includes(g.id)),
    );
    const fetchParams = { ...data };

    if (data.sortByAnnotationOrigin) {
      setSortOrder(data.sortByAnnotationOrder);
      await dispatch(
        candidatesActions.setCandidatesAnnotationSortOptions({
          key: data.sortByAnnotationKey,
          origin: data.sortByAnnotationOrigin,
          order: data.sortByAnnotationOrder,
        }),
      );
    }

    // Save form-specific data, formatted for the API query
    await dispatch(candidatesActions.setFilterFormData(data));

    await dispatch(
      candidatesActions.fetchCandidates({
        pageNumber: 1,
        numPerPage,
        ...fetchParams,
      }),
    );
    setQueryInProgress(false);
  };

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className={classes.headerRow}>
          <Typography variant="h5">
            <b>Scan candidates for sources</b>
          </Typography>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              columnGap: "0.75rem",
            }}
          >
            <Tooltip
              title="Reset all filters and search parameters to default (or selected profile)"
              className={classes.reset}
            >
              <IconButton
                onClick={() => {
                  resetFormFields(
                    defaultStartDate,
                    defaultEndDate,
                    selectedScanningProfile,
                  );
                }}
              >
                <RestartAltIcon />
              </IconButton>
            </Tooltip>
            <CandidatesPreferences
              selectedScanningProfile={selectedScanningProfile}
              setSelectedScanningProfile={setSelectedScanningProfile}
            />
            <Tooltip title="Search results are cached between pagination requests, and are re-computed each time this Search button is clicked">
              <div>
                <Button primary type="submit" endIcon={<SearchIcon />}>
                  Search
                </Button>
              </div>
            </Tooltip>
          </div>
        </div>
        <Grid container columnSpacing={{ xs: 0, lg: 1.5 }} rowSpacing={1.5}>
          <Grid item xs={12} lg={6}>
            <Paper
              variant="outlined"
              className={classes.simplePadding}
              style={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div className={classes.formRow} style={{ marginTop: 0 }}>
                <Typography variant="h6" className={classes.title}>
                  Selected scanning profile:&nbsp;
                  {selectedScanningProfile
                    ? selectedScanningProfile.name || "No name"
                    : "None"}
                </Typography>
                <Typography variant="subtitle2">
                  <i>
                    Click <q>Manage Scanning Profiles</q> to select a new
                    profile.
                  </i>
                </Typography>
              </div>
              <div>
                {(errors.startDate || errors.endDate) && (
                  <FormValidationError message="Invalid date range." />
                )}
                <div className={classes.timeRange}>
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <LocalizationProvider dateAdapter={AdapterDateFns}>
                        <DateTimePicker
                          value={value}
                          onChange={(newValue) => onChange(newValue)}
                          label="Start (Local Time)"
                          showTodayButton={false}
                          ampm={useAMPM}
                          slotProps={{ textField: { variant: "outlined" } }}
                        />
                      </LocalizationProvider>
                    )}
                    rules={{ validate: validateDates }}
                    name="startDate"
                    control={control}
                    defaultValue={defaultStartDate}
                  />
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <LocalizationProvider dateAdapter={AdapterDateFns}>
                        <DateTimePicker
                          value={value}
                          onChange={(newValue) => onChange(newValue)}
                          label="End (Local Time)"
                          showTodayButton={false}
                          ampm={useAMPM}
                          slotProps={{ textField: { variant: "outlined" } }}
                        />
                      </LocalizationProvider>
                    )}
                    rules={{ validate: validateDates }}
                    name="endDate"
                    control={control}
                    defaultValue={defaultEndDate}
                  />
                </div>
              </div>
              <div className={classes.savedFiltering}>
                <div className={classes.savedStatusSelect}>
                  <Typography variant="h6" className={classes.title}>
                    Show candidates...
                  </Typography>
                  <Controller
                    labelId="savedStatusSelectLabel"
                    name="savedStatus"
                    control={control}
                    input={<Input data-testid="savedStatusSelect" />}
                    render={({ field: { onChange } }) => (
                      <Select
                        key={
                          selectedScanningProfile?.savedStatus
                            ? "notLoadedYet"
                            : "loaded"
                        }
                        onChange={onChange}
                        defaultValue={
                          selectedScanningProfile?.savedStatus || "all"
                        }
                        data-testid="savedStatusSelect"
                        style={{ minWidth: "100%" }}
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
                <div className={classes.rejectCandidatesSelect}>
                  <Controller
                    labelId="rejectedCandidatesLabel"
                    name="rejectedStatus"
                    control={control}
                    defaultValue={
                      selectedScanningProfile?.rejectedStatus || "hide"
                    }
                    render={({ field: { onChange, value } }) => (
                      <Switch
                        checked={value === "show"}
                        onChange={(event) =>
                          onChange(event.target.checked ? "show" : "hide")
                        }
                        inputProps={{ "aria-label": "controlled" }}
                        data-testid="rejectedStatusSelect"
                      />
                    )}
                  />
                  <InputLabel id="rejectedCandidatesLabel">
                    Hide Rejected
                  </InputLabel>
                </div>
              </div>
              <div
                className={classes.formRow}
                style={{
                  marginTop: 0,
                  marginBottom: 0,
                  paddingTop: "1rem",
                  display: "flex",
                  flexDirection: "column",
                  height: "100%",
                }}
              >
                <div style={{ display: "flex", alignItems: "center" }}>
                  <Typography variant="h6" className={classes.title}>
                    Program Selection
                  </Typography>
                  {/* we want an eye (show/hide) icon to quickly show/hide the groups that are not selected */}
                  <Tooltip title="Show/Hide unselected groups, useful to only see selected groups">
                    <IconButton
                      onClick={() => setShowAllGroups(!showAllGroups)}
                      size="small"
                      style={{ marginLeft: "0.25rem" }}
                    >
                      {showAllGroups ? (
                        <VisibilityIcon />
                      ) : (
                        <VisibilityOffIcon />
                      )}
                    </IconButton>
                  </Tooltip>
                  {getValues().groupIDs?.length === 0 && (
                    <FormValidationError message="Select at least one group." />
                  )}
                </div>
                <Paper
                  variant="outlined"
                  className={classes.simplePadding}
                  style={{ height: "100%" }}
                >
                  <TextField
                    label="Search"
                    variant="outlined"
                    style={{ minWidth: "100%", marginBottom: "0.5rem" }}
                    size="small"
                    onChange={(event) =>
                      setFilterGroupsInput(event.target.value)
                    }
                  />
                  <div
                    style={{
                      height: "10rem",
                      overflowY: "auto",
                    }}
                  >
                    <div className={classes.groupOptions}>
                      {filterGroupOptions.map((group) => (
                        // if the group.id is not in getValues().groupIDs, then we want to hide it
                        <div
                          key={group.id}
                          style={{
                            display:
                              !showAllGroups &&
                              !getValues().groupIDs.includes(group.id)
                                ? "none"
                                : "flex",
                            alignItems: "center",
                            justifyContent: "flex-start",
                          }}
                        >
                          <Checkbox
                            key={`filteringFormGroupCheckbox-${group.id}`}
                            onChange={(event) => {
                              const selectedGroupIDs = getValues().groupIDs;
                              if (
                                selectedGroupIDs.includes(group.id) &&
                                !event.target.checked
                              ) {
                                const newSelectedGroupIDs =
                                  selectedGroupIDs.filter(
                                    (id) => id !== group.id,
                                  );
                                setFilterGroups(
                                  userAccessibleGroups.filter((g) =>
                                    newSelectedGroupIDs.includes(g.id),
                                  ),
                                );
                                reset({
                                  ...getValues(),
                                  groupIDs: newSelectedGroupIDs,
                                });
                              } else if (
                                !selectedGroupIDs.includes(group.id) &&
                                event.target.checked
                              ) {
                                const newSelectedGroupIDs = [
                                  ...selectedGroupIDs,
                                  group.id,
                                ];
                                setFilterGroups(
                                  userAccessibleGroups.filter((g) =>
                                    newSelectedGroupIDs.includes(g.id),
                                  ),
                                );
                                reset({
                                  ...getValues(),
                                  groupIDs: newSelectedGroupIDs,
                                });
                              }
                            }}
                            checked={getValues().groupIDs.includes(group.id)}
                            data-testid={`filteringFormGroupCheckbox-${group.id}`}
                            style={{
                              margin: 0,
                              padding: 0,
                              marginRight: "0.2rem",
                            }}
                          />
                          <Typography
                            variant="body1"
                            className={classes.body}
                            key={`filteringFormGroupLabel-${group.id}`}
                          >
                            {group.name}
                          </Typography>
                        </div>
                      ))}
                    </div>
                  </div>
                </Paper>
              </div>
            </Paper>
          </Grid>
          <Grid item xs={12} lg={6}>
            <Paper variant="outlined" className={classes.simplePadding}>
              <div className={classes.formRow} style={{ marginTop: 0 }}>
                <Typography
                  variant="h6"
                  className={classes.title}
                  style={{ marginBottom: "0.5rem" }}
                >
                  Classification(s)
                </Typography>
                <ClassificationSelect
                  selectedClassifications={selectedClassifications}
                  setSelectedClassifications={setSelectedClassifications}
                  showShortcuts
                />
              </div>
              <div className={classes.formRow}>
                <Typography variant="h6" className={classes.title}>
                  Redshift
                </Typography>
                <div className={classes.redshiftFiltering}>
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <TextField
                        id="minimum-redshift"
                        label="Minimum"
                        type="number"
                        inputProps={{ step: 0.001 }}
                        margin="dense"
                        style={{ minWidth: "100%" }}
                        onChange={(event) => onChange(event.target.value)}
                        value={value}
                        InputLabelProps={{
                          shrink: true,
                        }}
                      />
                    )}
                    name="redshiftMinimum"
                    labelId="redshift-select-label"
                    control={control}
                  />
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <TextField
                        id="maximum-redshift"
                        label="Maximum"
                        type="number"
                        inputProps={{ step: 0.001 }}
                        margin="dense"
                        style={{ minWidth: "100%" }}
                        onChange={(event) => onChange(event.target.value)}
                        value={value}
                        InputLabelProps={{
                          shrink: true,
                        }}
                      />
                    )}
                    name="redshiftMaximum"
                    control={control}
                  />
                </div>
              </div>
              <div className={classes.formRow} style={{ marginBottom: 0 }}>
                <Typography variant="h6" className={classes.title}>
                  GCN Events
                </Typography>
                <div className={classes.gcnGrid}>
                  <Controller
                    render={() => (
                      <Autocomplete
                        id="gcn-event-filtering"
                        options={gcnEvents?.events || []}
                        getOptionLabel={(option) =>
                          `${option?.dateobs}${
                            option?.aliases?.length > 0
                              ? ` (${option?.aliases})`
                              : ""
                          }` || ""
                        }
                        className={classes.select}
                        // eslint-disable-next-line no-shadow
                        onInputChange={(event, value) => {
                          if (
                            ((event?.type === "change" ||
                              event?.type === "clear") &&
                              value !== null &&
                              value !== "") ||
                            (event?.type === "click" && value === "")
                          ) {
                            dispatch(
                              gcnEventsActions.fetchGcnEvents({
                                partialdateobs: value,
                              }),
                            );
                          }
                        }}
                        onChange={(event, newValue) => {
                          if (newValue !== null) {
                            reset({
                              ...getValues(),
                              gcneventid: newValue.id === -1 ? "" : newValue.id,
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
                    render={({ field: { onChange } }) => (
                      <TextField
                        id="cumprob"
                        label="Cumulative Probability"
                        type="number"
                        inputProps={{ step: 0.01, min: 0, max: 1 }}
                        onChange={(event) => onChange(event.target.value)}
                        defaultValue={0.95}
                      />
                    )}
                    name="localizationCumprob"
                    control={control}
                  />
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <TextField
                        type="text"
                        value={value || " "}
                        onChange={(event) => onChange(event.target.value)}
                        label="First Detection After (UTC)"
                      />
                    )}
                    name="firstDetectionAfter"
                    control={control}
                  />
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <TextField
                        type="text"
                        value={value || " "}
                        onChange={(event) => onChange(event.target.value)}
                        label="Last Detection Before (UTC)"
                      />
                    )}
                    name="lastDetectionBefore"
                    control={control}
                  />
                  <Controller
                    render={({ field: { onChange } }) => (
                      <TextField
                        id="minNbDect"
                        label="Minimum Number of Detections"
                        type="number"
                        inputProps={{ step: 1, min: 1 }}
                        onChange={(event) => onChange(event.target.value)}
                        defaultValue={1}
                      />
                    )}
                    name="numberDetections"
                    control={control}
                  />
                </div>
                <Tooltip title="If unchecked, ignore all constraints on detections.">
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
                        name="requireDetections"
                        control={control}
                        defaultValue
                      />
                    }
                    label="Require detections"
                  />
                </Tooltip>
                <Tooltip title="If checked, do not account for forced photometry when applying detections constraints">
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
                        defaultValue={false}
                      />
                    }
                    label="Ignore Forced Photometry"
                  />
                </Tooltip>
              </div>
              <div
                className={classes.formRow}
                style={{ marginTop: "0.5rem", marginBottom: 0 }}
              >
                <Typography variant="h6" className={classes.title}>
                  Annotation Sorting
                </Typography>
                {errors.sortingOrigin && (
                  <FormValidationError message="All sorting fields must be left empty or all filled out" />
                )}
                <div className={classes.annotationSorting}>
                  <div style={{ minWidth: "100%" }}>
                    <Controller
                      labelId="sorting-select-label"
                      name="sortingOrigin"
                      control={control}
                      input={
                        <Input data-testid="annotationSortingOriginSelect" />
                      }
                      defaultValue={
                        selectedScanningProfile?.sortingOrigin || null
                      }
                      render={({ field: { onChange, value } }) => (
                        <Autocomplete
                          id="annotationSortingOriginSelect"
                          options={Object.keys(availableAnnotationsInfo || [])}
                          style={{ minWidth: "100%" }}
                          value={value}
                          onChange={(event, newValue) => {
                            if (newValue === null) {
                              reset({
                                ...getValues(),
                                sortingOrigin: newValue,
                                sortingKey: null,
                                sortingOrder: null,
                              });
                              setAnnotationSortingKeyOptions([]);
                            } else {
                              onChange(newValue);
                              const newOptions = (
                                availableAnnotationsInfo[newValue] || []
                              )
                                .map((annotation) =>
                                  Object.keys(annotation || {}),
                                )
                                .flat();
                              setAnnotationSortingKeyOptions(newOptions);
                            }
                          }}
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              label="Origin"
                              variant="outlined"
                            />
                          )}
                        />
                      )}
                      rules={{ validate: validateSorting }}
                    />
                  </div>
                  <div style={{ minWidth: "100%" }}>
                    <Controller
                      labelId="sorting-select-key-label"
                      name="sortingKey"
                      control={control}
                      input={<Input data-testid="annotationSortingKeySelect" />}
                      defaultValue={selectedScanningProfile?.sortingKey || ""}
                      render={({ field: { onChange, value } }) => (
                        <Autocomplete
                          id="annotationSortingKeySelect"
                          options={annotationSortingKeyOptions}
                          style={{ minWidth: "100%" }}
                          value={value}
                          onChange={(event, newValue) => {
                            if (newValue === null) {
                              reset({
                                ...getValues(),
                                sortingKey: newValue,
                                sortingOrder: null,
                              });
                            } else if (getValues().sortingOrder === null) {
                              reset({
                                ...getValues(),
                                sortingKey: newValue,
                                sortingOrder: "asc",
                              });
                            } else {
                              onChange(newValue);
                            }
                          }}
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              label="Key"
                              variant="outlined"
                            />
                          )}
                        />
                      )}
                      rules={{ validate: validateSorting }}
                    />
                  </div>
                  <div style={{ minWidth: "100%" }}>
                    <Controller
                      labelId="sorting-select-order-label"
                      name="sortingOrder"
                      control={control}
                      input={
                        <Input data-testid="annotationSortingOrderSelect" />
                      }
                      defaultValue={
                        selectedScanningProfile?.sortingOrder || "asc"
                      }
                      render={({ field: { onChange, value } }) => (
                        <Autocomplete
                          id="annotationSortingOrderSelect"
                          options={["asc", "desc"]}
                          style={{ minWidth: "100%" }}
                          value={value}
                          getOptionLabel={(option) => {
                            if (option === "asc") {
                              return "Ascending";
                            }
                            if (option === "desc") {
                              return "Descending";
                            }
                            return "None";
                          }}
                          onChange={(event, newValue) => {
                            onChange(newValue);
                          }}
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              label="Order"
                              variant="outlined"
                            />
                          )}
                        />
                      )}
                    />
                  </div>
                </div>
              </div>
            </Paper>
          </Grid>
        </Grid>
      </form>
    </div>
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
    }),
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
