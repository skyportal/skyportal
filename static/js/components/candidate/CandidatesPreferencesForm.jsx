import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";
import PropTypes from "prop-types";

import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import Input from "@mui/material/Input";
import InputLabel from "@mui/material/InputLabel";
import TextField from "@mui/material/TextField";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import SaveIcon from "@mui/icons-material/Save";
import Switch from "@mui/material/Switch";

import makeStyles from "@mui/styles/makeStyles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Button from "../Button";

import * as candidatesActions from "../../ducks/candidate/candidates";
import * as profileActions from "../../ducks/profile";
import Responsive from "../Responsive";
import FoldBox from "../FoldBox";
import FormValidationError from "../FormValidationError";
import ClassificationSelect from "../classification/ClassificationSelect";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
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

const CandidatesPreferencesForm = ({
  userAccessibleGroups,
  availableAnnotationsInfo,
  addOrEdit,
  editingProfile,
  closeDialog,
  selectedScanningProfile,
  setSelectedScanningProfile,
}) => {
  const classes = useStyles();
  const preferences = useSelector((state) => state.profile.preferences);

  const dispatch = useDispatch();
  const [selectedClassifications, setSelectedClassifications] = useState([]);
  const [classificationsWith, setClassificationsWith] = useState(true);
  const [selectedAnnotationOrigin, setSelectedAnnotationOrigin] = useState();

  const {
    handleSubmit,
    getValues,
    control,
    reset,

    formState: { errors },
  } = useForm();

  useEffect(() => {
    if (addOrEdit === "Add") {
      reset({
        groupIDs: Array(userAccessibleGroups.length).fill(false),
      });
    } else if (addOrEdit === "Edit") {
      const currentOptions = { ...editingProfile };
      // Translated selected group IDs to group IDs form indices
      const groupIds = Array(userAccessibleGroups.length).fill(false);
      userAccessibleGroups
        ?.map((g) => g.id)
        ?.forEach((groupId, idx) => {
          groupIds[idx] = currentOptions.groupIDs.includes(groupId);
        });
      currentOptions.groupIDs = groupIds;
      reset(currentOptions);
    }
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reset, userAccessibleGroups]);

  // Set initial form values in the redux state
  useEffect(() => {
    dispatch(
      candidatesActions.setFilterFormData({
        savedStatus: "all",
      }),
    );
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
  }, [dispatch]);

  let formState = getValues();

  const validateName = () => {
    formState = getValues();
    const otherProfiles = preferences.scanningProfiles
      ?.filter((profile) => profile.name !== editingProfile?.name)
      ?.map((profile) => profile.name);
    return (
      formState.name.length > 0 && !otherProfiles?.includes(formState.name)
    );
  };

  const validateGroups = () => {
    formState = getValues();
    return formState.groupIDs?.filter((value) => Boolean(value)).length >= 1;
  };

  const validateSorting = () => {
    formState = getValues();
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

  const onSubmit = async (formData) => {
    const groupIDs = userAccessibleGroups?.map((g) => g.id);
    const selectedGroupIDs = groupIDs?.filter(
      (ID, idx) => formData.groupIDs[idx],
    );
    const data = {
      groupIDs: selectedGroupIDs,
      name: formData.name,
      savedStatus: formData.savedStatus,
    };

    if (addOrEdit === "Add") {
      data.default = true;
    } else if (addOrEdit === "Edit") {
      data.default = editingProfile?.default;
    }

    // decide if to show rejected candidates
    if (formData.rejectedStatus) {
      data.rejectedStatus = formData.rejectedStatus;
    }
    // Convert dates to ISO for parsing on back-end
    if (formData.timeRange) {
      data.timeRange = formData.timeRange;
    }
    if (selectedClassifications.length > 0) {
      data.classifications = selectedClassifications;
      data.classificationsWith = classificationsWith;
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

    const currentProfiles = preferences.scanningProfiles || [];
    if (addOrEdit === "Add") {
      // Add new profile as the default in the preferences
      currentProfiles.forEach((profile) => {
        profile.default = false;
      });
      currentProfiles.push(data);
    } else if (addOrEdit === "Edit") {
      // Update profile
      const profileIndex = currentProfiles.findIndex(
        (profile) => profile.name === editingProfile?.name,
      );
      if (profileIndex !== -1) {
        currentProfiles[profileIndex] = data;
      }
    }

    const prefs = {
      scanningProfiles: currentProfiles,
    };
    dispatch(profileActions.updateUserPreferences(prefs));

    if (addOrEdit === "Edit") {
      // If we just edited the selected profile, let the
      // parent component know we updated some fields
      if (selectedScanningProfile?.name === data.name) {
        setSelectedScanningProfile(data);
      }
      closeDialog();
    } else if (addOrEdit === "Add") {
      // New profiles are set to default/loaded immediately
      setSelectedScanningProfile(data);
      closeDialog();
    }
  };

  return (
    <div className={classes.filterListContainer}>
      <Typography variant="h6">
        {addOrEdit === "Add"
          ? "Add a New Scanning Profile"
          : "Edit a Scanning Profile"}
      </Typography>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className={classes.formRow}>
          {errors.name && (
            <FormValidationError message="Profile name must be unique and at least 1 character" />
          )}
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                id="name"
                label="Name"
                data-testid="profile-name"
                value={value}
                InputProps={{ "data-testid": "name" }}
                InputLabelProps={{
                  shrink: true,
                }}
                onChange={(event) => onChange(event.target.value)}
              />
            )}
            name="name"
            control={control}
            defaultValue=""
            rules={{ validate: validateName }}
          />
        </div>
        <div className={classes.formRow}>
          <Controller
            render={({ field: { onChange, value } }) => (
              <TextField
                id="time-range"
                label="Time range (hours before now)"
                type="number"
                value={value}
                inputProps={{ step: 1 }}
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
            Show only candidates which passed a filter from the selected
            groups...
          </InputLabel>
          <Controller
            labelId="savedStatusSelectLabel"
            name="savedStatus"
            control={control}
            input={<Input data-testid="profileSavedStatusSelect" />}
            defaultValue="all"
            render={({ field: { onChange, value } }) => (
              <Select
                labelId="savedStatusSelectLabel"
                onChange={onChange}
                value={value}
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
        <div className={classes.formRow}>
          <ClassificationSelect
            selectedClassifications={selectedClassifications}
            setSelectedClassifications={setSelectedClassifications}
            showShortcuts
          />
        </div>
        <div className={classes.formRow}>
          {/* select between including candidates with the selected classifications, or without */}
          <InputLabel id="profile-classifications-with-select-label">
            {classificationsWith === false ? "without" : "with"} the selected
            classifications
          </InputLabel>
          <Switch
            checked={classificationsWith}
            onChange={() => setClassificationsWith(!classificationsWith)}
            color="primary"
            inputProps={{ "aria-label": "primary checkbox" }}
          />
        </div>
        <div className={classes.formRow}>
          <InputLabel id="profile-redshift-select-label">Redshift</InputLabel>
          <div className={classes.redshiftField}>
            <Controller
              render={({ field: { onChange, value } }) => (
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
              render={({ field: { onChange, value } }) => (
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
            Show/Hide rejected candidates
          </InputLabel>
          <Controller
            labelId="profileRejectedCandidatesSelect"
            name="rejectedStatus"
            control={control}
            input={<Input data-testid="profileRejectedStatusSelect" />}
            defaultValue="show"
            render={({ field: { onChange, value } }) => (
              <Select
                labelId="profileRejectedCandidatesSelect"
                onChange={onChange}
                value={value}
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
        <div
          className={`${classes.formRow} ${classes.annotationSorting}`}
          data-testid="annotation-sorting-accordion"
        >
          {errors.sortingOrigin && (
            <FormValidationError message="All sorting fields must be left empty or all filled out" />
          )}
          <Responsive element={FoldBox} title="Annotation Sorting" folded>
            <InputLabel id="profile-sorting-select-label">
              Annotation Origin
            </InputLabel>
            <Controller
              labelId="profile-sorting-select-label"
              name="sortingOrigin"
              control={control}
              render={({ field: { onChange, value } }) => (
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
              defaultValue=""
            />
            <InputLabel id="profile-sorting-select-key-label">
              Annotation Key
            </InputLabel>
            <Controller
              labelId="profile-sorting-select-key-label"
              name="sortingKey"
              control={control}
              input={<Input data-testid="profileAnnotationSortingKeySelect" />}
              defaultValue=""
              render={({ field: { onChange, value } }) => (
                <Select
                  onChange={onChange}
                  value={value}
                  data-testid="profileAnnotationSortingKeySelect"
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
                      ),
                    )
                  ) : (
                    <div />
                  )}
                </Select>
              )}
            />
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
              render={({ field: { onChange, value } }) => (
                <Select
                  onChange={onChange}
                  value={value}
                  data-testid="profileAnnotationSortingOrderSelect"
                >
                  <MenuItem key="none" value="">
                    None
                  </MenuItem>
                  <MenuItem key="desc" value="desc">
                    Descending
                  </MenuItem>
                  <MenuItem key="asc" value="asc">
                    Ascending
                  </MenuItem>
                </Select>
              )}
            />
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
            {userAccessibleGroups?.map((group, idx) => (
              <FormControlLabel
                key={group.id}
                control={
                  <Controller
                    render={({ field: { onChange, value } }) => (
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
            primary
            type="submit"
            endIcon={<SaveIcon />}
            data-testid="saveScanningProfileButton"
          >
            Save
          </Button>
        </div>
      </form>
    </div>
  );
};

CandidatesPreferencesForm.propTypes = {
  userAccessibleGroups: PropTypes.arrayOf(PropTypes.shape({})),
  availableAnnotationsInfo: PropTypes.shape({}),
  addOrEdit: PropTypes.string.isRequired,
  // Args below required for editing
  editingProfile: PropTypes.shape({
    name: PropTypes.string,
    groupIDs: PropTypes.arrayOf(PropTypes.number),
    default: PropTypes.bool,
    selected: PropTypes.bool,
  }),
  closeDialog: PropTypes.func,
  selectedScanningProfile: PropTypes.shape({ name: PropTypes.string }),
  setSelectedScanningProfile: PropTypes.func,
};

CandidatesPreferencesForm.defaultProps = {
  userAccessibleGroups: [],
  availableAnnotationsInfo: null,
  editingProfile: null,
  closeDialog: null,
  selectedScanningProfile: null,
  setSelectedScanningProfile: null,
};

export default CandidatesPreferencesForm;
