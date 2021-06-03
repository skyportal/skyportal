import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import PropTypes from "prop-types";

import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import IconButton from "@material-ui/core/IconButton";
import Typography from "@material-ui/core/Typography";
import CloseIcon from "@material-ui/icons/Close";
import Button from "@material-ui/core/Button";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import Toolbar from "@material-ui/core/Toolbar";
import Tooltip from "@material-ui/core/Tooltip";
import Input from "@material-ui/core/Input";
import InputLabel from "@material-ui/core/InputLabel";
import Chip from "@material-ui/core/Chip";
import TextField from "@material-ui/core/TextField";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import Checkbox from "@material-ui/core/Checkbox";
import SaveIcon from "@material-ui/icons/Save";
import Grid from "@material-ui/core/Grid";
import Paper from "@material-ui/core/Paper";
import Slide from "@material-ui/core/Slide";
import { makeStyles, useTheme } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as candidatesActions from "../ducks/candidates";
import * as profileActions from "../ducks/profile";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";
import FormValidationError from "./FormValidationError";
import { allowedClasses } from "./ClassificationForm";
import ScanningProfilesList from "./ScanningProfilesList";

dayjs.extend(utc);

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

const useStyles = makeStyles((theme) => ({
  filterListContainer: {
    padding: "1rem",
    display: "flex",
    flexFlow: "column nowrap",
  },
  formRow: {
    margin: "1rem 0",
    "& > div": {
      width: "100%",
    },
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
    "& div": {
      width: "100%",
    },
  },
  saveButton: {
    marginTop: "1rem",
  },
  dialogContent: {
    backgroundColor: theme.palette.background.default,
  },
  header: {
    justifyContent: "space-between",
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

// eslint-disable-next-line react/display-name
const Transition = React.forwardRef((props, ref) => (
  // eslint-disable-next-line react/jsx-props-no-spreading
  <Slide direction="up" ref={ref} {...props} />
));

const CandidatesPreferences = ({
  selectedScanningProfile,
  setSelectedScanningProfile,
}) => {
  const preferences = useSelector((state) => state.profile.preferences);
  const availableAnnotationsInfo = useSelector(
    (state) => state.candidates.annotationsInfo
  );
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();

  useEffect(() => {
    // Grab the available annotation fields for filtering
    if (!availableAnnotationsInfo) {
      dispatch(candidatesActions.fetchAnnotationsInfo());
    }
  }, [dispatch, availableAnnotationsInfo]);

  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible
  );

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
  const [selectedAnnotationOrigin, setSelectedAnnotationOrigin] = useState();

  const { handleSubmit, getValues, control, errors, reset } = useForm();

  useEffect(() => {
    reset({
      groupIDs: Array(userAccessibleGroups.length).fill(false),
    });
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reset, userAccessibleGroups]);

  // Set initial form values in the redux state
  useEffect(() => {
    dispatch(
      candidatesActions.setFilterFormData({
        savedStatus: "all",
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

  const validateSorting = () => {
    formState = getValues({ nest: true });
    return (
      // All left empty
      (formState.sortingOrigin === "" &&
        formState.sortingKey === "" &&
        formState.sortingOrder === "") ||
      // Or all filled out
      (formState.sortingOrigin !== "" &&
        formState.sortingKey !== "" &&
        formState.sortingOrder !== "")
    );
  };

  const [addDialogOpen, setAddDialogOpen] = useState(false);

  const onSubmit = async (formData) => {
    const groupIDs = userAccessibleGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter(
      (ID, idx) => formData.groupIDs[idx]
    );
    const data = {
      id: Math.random().toString(36).substr(2, 5), // Assign a random ID to the profile
      groupIDs: selectedGroupIDs,
      savedStatus: formData.savedStatus,
      default: true,
      selected: true,
    };
    // decide if to show rejected candidates
    if (formData.rejectedStatus) {
      data.rejectedStatus = formData.rejectedStatus;
    }
    // Convert dates to ISO for parsing on back-end
    if (formData.timeRange) {
      data.timeRange = formData.timeRange;
    }
    if (formData.classifications.length > 0) {
      data.classifications = formData.classifications;
    }
    if (formData.redshiftMinimum) {
      data.redshiftMinimum = formData.redshiftMinimum;
    }
    if (formData.redshiftMaximum) {
      data.redshiftMaximum = formData.redshiftMaximum;
    }
    if (formData.sortingOrigin) {
      data.sortingOrigin = formData.sortingOrigin;
      data.sortingKey = formData.sortingKey;
      data.sortingOrder = formData.sortingOrder;
    }

    // Add new profile as the default in the preferences
    const currentProfiles = preferences.scanningProfiles || [];
    currentProfiles.forEach((profile) => {
      profile.default = false;
      profile.selected = false;
    });
    currentProfiles.push(data);
    const prefs = {
      scanningProfiles: currentProfiles,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div>
      <div>
        <Tooltip title="Save and load pre-set search options">
          <Button
            variant="contained"
            data-testid="manageScanningProfilesButton"
            onClick={() => {
              setAddDialogOpen(true);
            }}
          >
            Manage scanning profiles
          </Button>
        </Tooltip>
      </div>
      <Dialog
        open={addDialogOpen}
        fullScreen
        onClose={() => {
          setAddDialogOpen(false);
        }}
        TransitionComponent={Transition}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <Toolbar className={classes.header}>
          <Typography variant="h6">Scanning Profiles</Typography>
          <IconButton
            edge="start"
            color="inherit"
            data-testid="closeScanningProfilesButton"
            onClick={() => {
              setAddDialogOpen(false);
            }}
            aria-label="close"
          >
            <CloseIcon />
          </IconButton>
        </Toolbar>
        <DialogContent className={classes.dialogContent}>
          <Grid container spacing={2}>
            <Grid item md={7} sm={12}>
              <ScanningProfilesList
                selectedScanningProfile={selectedScanningProfile}
                setSelectedScanningProfile={setSelectedScanningProfile}
              />
            </Grid>
            <Grid item md={5} sm={12}>
              <Paper>
                <div className={classes.filterListContainer}>
                  <Typography variant="h6">
                    Add a New Scanning Profile
                  </Typography>
                  <form onSubmit={handleSubmit(onSubmit)}>
                    <div className={classes.formRow}>
                      <Controller
                        render={({ onChange, value }) => (
                          <TextField
                            id="time-range"
                            label="Time range (hours before now)"
                            type="number"
                            value={value}
                            inputProps={{ step: 1 }}
                            // eslint-disable-next-line react/jsx-no-duplicate-props
                            InputProps={{ "data-testid": "timeRange" }}
                            InputLabelProps={{
                              shrink: true,
                            }}
                            onChange={(event) => onChange(event.target.value)}
                          />
                        )}
                        name="timeRange"
                        control={control}
                        defaultValue="24"
                      />
                    </div>
                    <div className={classes.savedStatusSelect}>
                      <InputLabel id="profileSavedStatusSelectLabel">
                        Show only candidates which passed a filter from the
                        selected groups...
                      </InputLabel>
                      <Controller
                        labelId="savedStatusSelectLabel"
                        as={Select}
                        name="savedStatus"
                        control={control}
                        input={<Input data-testid="profileSavedStatusSelect" />}
                        defaultValue="all"
                      >
                        {savedStatusSelectOptions.map((option) => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </Controller>
                    </div>
                    <div className={classes.formRow}>
                      <InputLabel id="profile-classifications-select-label">
                        Classifications
                      </InputLabel>
                      <Controller
                        labelId="profile-classifications-select-label"
                        render={({ onChange, value }) => (
                          <Select
                            multiple
                            value={value}
                            onChange={(event) => {
                              setSelectedClassifications(event.target.value);
                              onChange(event.target.value);
                            }}
                            input={
                              <Input data-testid="profile-classifications-select" />
                            }
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
                      <InputLabel id="profile-redshift-select-label">
                        Redshift
                      </InputLabel>
                      <div className={classes.redshiftField}>
                        <Controller
                          render={({ onChange, value }) => (
                            <TextField
                              data-testid="profile-minimum-redshift"
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
                          labelId="profile-redshift-select-label"
                          control={control}
                          defaultValue=""
                        />
                      </div>
                      <div className={classes.redshiftField}>
                        <Controller
                          render={({ onChange, value }) => (
                            <TextField
                              data-testid="profile-maximum-redshift"
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
                    <div className={classes.formRow}>
                      <InputLabel id="profileRejectedCandidatesLabel">
                        Show/hide rejected candidates
                      </InputLabel>
                      <Controller
                        labelId="profileRejectedCandidatesLabel"
                        as={Select}
                        name="rejectedStatus"
                        control={control}
                        input={
                          <Input data-testid="profileRejectedStatusSelect" />
                        }
                        defaultValue="hide"
                      >
                        {rejectedStatusSelectOptions.map((option) => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </Controller>
                    </div>
                    <div
                      className={`${classes.formRow} ${classes.annotationSorting}`}
                    >
                      {errors.sortingOrigin && (
                        <FormValidationError message="All sorting fields must be left empty or all filled out" />
                      )}
                      <Responsive
                        element={FoldBox}
                        title="Annotation Sorting"
                        mobileProps={{ folded: true }}
                      >
                        <InputLabel id="profile-sorting-select-label">
                          Annotation Origin
                        </InputLabel>
                        <Controller
                          labelId="profile-sorting-select-label"
                          name="sortingOrigin"
                          control={control}
                          render={({ onChange, value }) => (
                            <Select
                              id="profileAnnotationSortingOriginSelect"
                              value={value}
                              onChange={(event) => {
                                setSelectedAnnotationOrigin(event.target.value);
                                onChange(event.target.value);
                              }}
                              input={
                                <Input data-testid="profileAnnotationSortingOriginSelect" />
                              }
                            >
                              {availableAnnotationsInfo ? (
                                Object.keys(availableAnnotationsInfo).map(
                                  (option) => (
                                    <MenuItem key={option} value={option}>
                                      {option}
                                    </MenuItem>
                                  )
                                )
                              ) : (
                                <div />
                              )}
                            </Select>
                          )}
                          rules={{ validate: validateSorting }}
                          defaultValue=""
                        />
                        <InputLabel id="profile-sorting-select-key-label">
                          Annotation Key
                        </InputLabel>
                        <Controller
                          labelId="profile-sorting-select-key-label"
                          as={Select}
                          name="sortingKey"
                          control={control}
                          input={
                            <Input data-testid="profileAnnotationSortingKeySelect" />
                          }
                          defaultValue=""
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
                        </Controller>
                        <InputLabel id="profile-sorting-select-order-label">
                          Annotation Sort Order
                        </InputLabel>
                        <Controller
                          labelId="profile-sorting-select-order-label"
                          as={Select}
                          name="sortingOrder"
                          control={control}
                          input={
                            <Input data-testid="profileAnnotationSortingOrderSelect" />
                          }
                          defaultValue=""
                        >
                          <MenuItem key="desc" value="desc">
                            descending
                          </MenuItem>
                          <MenuItem key="asc" value="asc">
                            ascending
                          </MenuItem>
                        </Controller>
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
                                    }}
                                    checked={value}
                                    data-testid={`profileFilteringFormGroupCheckbox-${group.id}`}
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
                    <div className={classes.saveButton}>
                      <Button
                        variant="contained"
                        type="submit"
                        endIcon={<SaveIcon />}
                        data-testid="saveScanningProfileButton"
                        color="primary"
                      >
                        Save
                      </Button>
                    </div>
                  </form>
                </div>
              </Paper>
            </Grid>
          </Grid>
        </DialogContent>
      </Dialog>
    </div>
  );
};

CandidatesPreferences.propTypes = {
  selectedScanningProfile: PropTypes.shape({}),
  setSelectedScanningProfile: PropTypes.func.isRequired,
};
CandidatesPreferences.defaultProps = {
  selectedScanningProfile: null,
};
export default CandidatesPreferences;
