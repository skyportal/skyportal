import React from "react";
import { useSelector, useDispatch } from "react-redux";

import Button from "@material-ui/core/Button";
import Checkbox from "@material-ui/core/Checkbox";
import Paper from "@material-ui/core/Paper";
import Chip from "@material-ui/core/Chip";
import CheckIcon from "@material-ui/icons/Check";
import ClearIcon from "@material-ui/icons/Clear";
import {
  makeStyles,
  createMuiTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";

import MUIDataTable from "mui-datatables";

import { savedStatusSelectOptions } from "./FilterCandidateList";
import * as profileActions from "../ducks/profile";

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  chip: {
    margin: theme.spacing(0.5),
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

const ScanningProfilesList = () => {
  const classes = useStyles();
  const theme = useTheme();
  const profiles = useSelector(
    (state) => state.profile.preferences.scanningProfiles
  );
  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible
  );

  const dispatch = useDispatch();
  if (!profiles) {
    return <div />;
  }

  const deleteProfile = (dataIndex) => {
    profiles.splice(dataIndex, 1);
    const prefs = {
      scanningProfiles: profiles,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
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
    return profile ? (
      <div>
        {profile.classifications?.map((classification) => (
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
    return profile ? (
      <div>
        {profile.groupIDs?.map((groupID) => {
          const groupName = userAccessibleGroups?.find(
            (group) => group.id === groupID
          )?.name;
          return (
            <Chip
              size="small"
              key={groupName}
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

  const renderRejectedStatus = (dataIndex) => {
    const profile = profiles[dataIndex];
    return profile?.rejectedStatus === "show" ? (
      <CheckIcon
        size="small"
        key={`${profile?.id}_rejected_status`}
        color="primary"
      />
    ) : (
      <ClearIcon
        size="small"
        key={`${profile?.id}_rejected_status`}
        color="secondary"
      />
    );
  };

  const renderDelete = (dataIndex) => (
    <Button
      variant="contained"
      size="small"
      onClick={() => deleteProfile(dataIndex)}
    >
      Delete
    </Button>
  );

  const columns = [
    {
      name: "default",
      label: "Default?",
      options: {
        customBodyRenderLite: renderDefault,
      },
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
      label: "Redshift Minimum",
    },
    {
      name: "redshiftMaximum",
      label: "Redshift Maximum",
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
      name: "delete",
      label: "Delete",
      options: {
        customBodyRenderLite: renderDelete,
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
          <MUIDataTable data={profiles} options={options} columns={columns} />
        </MuiThemeProvider>
      </Paper>
    </div>
  );
};

export default ScanningProfilesList;
