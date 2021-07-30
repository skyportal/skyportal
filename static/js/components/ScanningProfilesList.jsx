import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import Button from "@material-ui/core/Button";
import Checkbox from "@material-ui/core/Checkbox";
import Paper from "@material-ui/core/Paper";
import Chip from "@material-ui/core/Chip";
import CheckIcon from "@material-ui/icons/Check";
import ClearIcon from "@material-ui/icons/Clear";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import {
  makeStyles,
  createMuiTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";

import MUIDataTable from "mui-datatables";
import * as profileActions from "../ducks/profile";

import CandidatesPreferencesForm from "./CandidatesPreferencesForm";

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
  container: {
    width: "100%",
    overflow: "scroll",
  },
  chip: {
    margin: theme.spacing(0.5),
  },
  actionButtons: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-evenly",
    "& > button": {
      margin: "0.25rem 0",
    },
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createMuiTheme({
    palette: theme.palette,
    overrides: {
      MUIDataTablePagination: {
        toolbar: {
          flexFlow: "row wrap",
          justifyContent: "flex-end",
          padding: "0.5rem 1rem 0",
          [theme.breakpoints.up("sm")]: {
            // Cancel out small screen styling and replace
            padding: "0px",
            paddingRight: "2px",
            flexFlow: "row nowrap",
          },
        },
        tableCellContainer: {
          padding: "1rem",
        },
        selectRoot: {
          marginRight: "0.5rem",
          [theme.breakpoints.up("sm")]: {
            marginLeft: "0",
            marginRight: "2rem",
          },
        },
      },
    },
  });

const ScanningProfilesList = ({
  selectedScanningProfile,
  setSelectedScanningProfile,
  userAccessibleGroups,
  availableAnnotationsInfo,
  classifications,
}) => {
  const classes = useStyles();
  const theme = useTheme();
  const profiles = useSelector(
    (state) => state.profile.preferences.scanningProfiles
  );

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [profileToEdit, setProfileToEdit] = useState();

  const dispatch = useDispatch();

  const handleLoadedChange = (checked, dataIndex) => {
    if (checked) {
      setSelectedScanningProfile(profiles[dataIndex]);
    } else {
      setSelectedScanningProfile(undefined);
    }
  };

  const renderLoaded = (dataIndex) => {
    const profile = profiles[dataIndex];
    return profile ? (
      <div>
        <Checkbox
          checked={selectedScanningProfile?.name === profile.name}
          key={`loaded_${dataIndex}`}
          data-testid={`loaded_${dataIndex}`}
          onChange={(event) =>
            handleLoadedChange(event.target.checked, dataIndex)
          }
          inputProps={{ "aria-label": "primary checkbox" }}
        />
      </div>
    ) : (
      <div />
    );
  };

  const deleteProfile = (dataIndex) => {
    profiles.splice(dataIndex, 1);
    const prefs = {
      scanningProfiles: profiles,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const editProfile = (profile) => {
    setProfileToEdit(profile);
    setEditDialogOpen(true);
  };

  const handleDefaultChange = (checked, dataIndex) => {
    if (checked) {
      // If setting new default, unset the old default first
      profiles.forEach((profile) => {
        profile.default = false;
      });
      profiles[dataIndex].default = true;
    } else {
      // If unchecking, just set default to false
      profiles[dataIndex].default = false;
    }
    const prefs = {
      scanningProfiles: profiles,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const renderDefault = (dataIndex) => {
    const profile = profiles[dataIndex];
    return profile ? (
      <div>
        <Checkbox
          checked={profile.default}
          key={`default${dataIndex}`}
          onChange={(event) =>
            handleDefaultChange(event.target.checked, dataIndex)
          }
          inputProps={{ "aria-label": "primary checkbox" }}
        />
      </div>
    ) : (
      <div />
    );
  };

  const renderTimeRange = (dataIndex) => {
    const profile = profiles[dataIndex];
    return profile?.timeRange ? `${profile.timeRange}hrs` : "";
  };

  const renderClassifications = (dataIndex) => {
    const profile = profiles[dataIndex];
    return profile?.classifications ? (
      <div>
        {profile.classifications.map((classification) => (
          <Chip
            size="small"
            key={classification}
            label={classification}
            color="primary"
            className={classes.chip}
          />
        ))}
      </div>
    ) : (
      <div />
    );
  };

  const renderGroups = (dataIndex) => {
    const profile = profiles[dataIndex];
    return profile?.groupIDs ? (
      <div>
        {profile.groupIDs.map((groupID) => {
          const groupName = userAccessibleGroups?.find(
            (group) => group.id === groupID
          )?.name;
          return (
            <Chip
              size="small"
              key={`group${groupID}`}
              label={groupName}
              color="primary"
              className={classes.chip}
            />
          );
        })}
      </div>
    ) : (
      <div />
    );
  };

  const renderSavedStatus = (dataIndex) => {
    const profile = profiles[dataIndex];
    const option = savedStatusSelectOptions.find(
      (selectOption) => selectOption.value === profile?.savedStatus
    );
    return option?.label || "";
  };

  const renderRedshift = (dataIndex) => {
    const profile = profiles[dataIndex];
    return `Min: ${profile?.redshiftMinimum || "N/A"}, Max: ${
      profile?.redshiftMaximum || "N/A"
    }`;
  };

  const renderSorting = (dataIndex) => {
    const profile = profiles[dataIndex];
    return profile?.sortingOrigin
      ? `${profile.sortingOrigin}: ${profile.sortingKey}, ${profile.sortingOrder}`
      : "";
  };

  const renderRejectedStatus = (dataIndex) => {
    const profile = profiles[dataIndex];
    return profile?.rejectedStatus === "show" ? (
      <CheckIcon
        size="small"
        key={`${dataIndex}RejectedStatus`}
        color="primary"
      />
    ) : (
      <ClearIcon
        size="small"
        key={`${dataIndex}RejectedStatus`}
        color="secondary"
      />
    );
  };

  const renderActions = (dataIndex) => (
    <div className={classes.actionButtons}>
      <Button
        variant="contained"
        size="small"
        onClick={() => deleteProfile(dataIndex)}
      >
        Delete
      </Button>
      <Button
        variant="contained"
        size="small"
        onClick={() => editProfile(profiles[dataIndex])}
      >
        Edit
      </Button>
    </div>
  );

  const columns = [
    {
      name: "loaded",
      label: "Currently Loaded",
      options: {
        customBodyRenderLite: renderLoaded,
      },
    },
    {
      name: "default",
      label: "Default",
      options: {
        customBodyRenderLite: renderDefault,
      },
    },
    {
      name: "name",
      label: "Name",
    },
    {
      name: "timeRange",
      label: "Hours Before Now",
      options: {
        customBodyRenderLite: renderTimeRange,
      },
    },
    {
      name: "groupIDs",
      label: "Selected Programs",
      options: {
        customBodyRenderLite: renderGroups,
      },
    },
    {
      name: "savedStatus",
      label: "Candidate Saved Status",
      options: {
        customBodyRenderLite: renderSavedStatus,
      },
    },
    {
      name: "redshiftMinimum",
      label: "Redshift Range",
      options: {
        customBodyRenderLite: renderRedshift,
      },
    },
    {
      name: "sortingOrigin",
      label: "Annotation Sorting",
      options: {
        customBodyRenderLite: renderSorting,
      },
    },
    {
      name: "rejectedStatus",
      label: "Show Rejected",
      options: {
        customBodyRenderLite: renderRejectedStatus,
      },
    },
    {
      name: "classifications",
      label: "Classifications",
      options: {
        customBodyRenderLite: renderClassifications,
      },
    },
    {
      name: "edit",
      label: "Edit",
      options: {
        customBodyRenderLite: renderActions,
      },
    },
  ];

  const options = {
    filter: false,
    sort: false,
    print: false,
    download: false,
    search: false,
    selectableRows: "none",
    elevation: 0,
  };

  return (
    <div>
      <Paper className={classes.container}>
        <MuiThemeProvider theme={getMuiTheme(theme)}>
          <MUIDataTable
            data={profiles}
            options={options}
            columns={columns}
            title="Saved Scanning Profiles"
          />
        </MuiThemeProvider>
      </Paper>
      <Dialog
        open={editDialogOpen}
        onClose={() => {
          setEditDialogOpen(false);
        }}
      >
        <DialogContent className={classes.dialogContent}>
          <CandidatesPreferencesForm
            userAccessibleGroups={userAccessibleGroups}
            availableAnnotationsInfo={availableAnnotationsInfo}
            classifications={classifications}
            addOrEdit="Edit"
            editingProfile={profileToEdit}
            closeDialog={() => setEditDialogOpen(false)}
            selectedScanningProfile={selectedScanningProfile}
            setSelectedScanningProfile={setSelectedScanningProfile}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

ScanningProfilesList.propTypes = {
  selectedScanningProfile: PropTypes.shape({ name: PropTypes.string }),
  setSelectedScanningProfile: PropTypes.func.isRequired,
  userAccessibleGroups: PropTypes.arrayOf(PropTypes.shape({})),
  availableAnnotationsInfo: PropTypes.shape({}),
  classifications: PropTypes.arrayOf(PropTypes.string),
};
ScanningProfilesList.defaultProps = {
  userAccessibleGroups: [],
  availableAnnotationsInfo: {},
  classifications: [],
  selectedScanningProfile: null,
};
export default ScanningProfilesList;
