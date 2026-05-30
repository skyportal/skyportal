import React, { useMemo, useState } from "react";

import Checkbox from "@mui/material/Checkbox";
import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";

import { makeStyles } from "tss-react/mui";
import { GridToolbarContainer } from "@mui/x-data-grid";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import StyledDataGrid from "../StyledDataGrid";
import * as profileActions from "../../ducks/profile";

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

const useStyles = makeStyles()((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  chip: {
    margin: theme.spacing(0.5),
  },
  actionButtons: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

interface ScanningProfilesListProps {
  selectedScanningProfile?: any;
  setSelectedScanningProfile: (...a: any[]) => void;
  userAccessibleGroups?: any[];
  availableAnnotationsInfo?: any;
  classifications?: string[];
}

const ScanningProfilesList = ({
  selectedScanningProfile = null,
  setSelectedScanningProfile,
  userAccessibleGroups = [],
  availableAnnotationsInfo = {},
  classifications = [],
}: ScanningProfilesListProps) => {
  const { classes } = useStyles();
  const profiles = useAppSelector(
    (state) => (state as any).profile.preferences.scanningProfiles,
  );

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [profileToEdit, setProfileToEdit] = useState<any>();

  const dispatch = useAppDispatch();

  // Memoized so the toolbar (and its "new scanning profile" button) keeps a
  // stable identity across the re-render that happens when the profiles list
  // loads; otherwise MUI remounts it and the button reference a test just
  // clicked goes stale before the dialog opens.
  const CustomToolbar = useMemo(
    () =>
      function ScanningProfilesToolbar() {
        return (
          <GridToolbarContainer>
            <IconButton
              name="new_scanning_profile"
              onClick={() => setNewDialogOpen(true)}
            >
              <AddIcon />
            </IconButton>
          </GridToolbarContainer>
        );
      },
    [],
  );

  const handleLoadedChange = (checked: boolean, dataIndex: number) => {
    if (checked) {
      setSelectedScanningProfile(profiles[dataIndex]);
    } else {
      setSelectedScanningProfile(undefined);
    }
  };

  // Profiles are user-preference objects without a stable id, so we key rows on
  // their array index (sort is disabled, so order is stable). dataIndex below
  // is that index, preserving the index-based test ids and splice semantics.
  const renderLoaded = (params: any) => {
    const dataIndex = params.row.__rowid;
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

  const deleteProfile = (dataIndex: number) => {
    profiles.splice(dataIndex, 1);
    const prefs = {
      scanningProfiles: profiles,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const editProfile = (profile: any) => {
    setProfileToEdit(profile);
    setEditDialogOpen(true);
  };

  const handleDefaultChange = (checked: boolean, dataIndex: number) => {
    const updatedProfiles = profiles.map((profile: any, i: number) => ({
      ...profile,
      default: checked && i === dataIndex,
    }));
    dispatch(
      profileActions.updateUserPreferences({
        scanningProfiles: updatedProfiles,
      }),
    );
  };

  const renderDefault = (params: any) => {
    const dataIndex = params.row.__rowid;
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

  const renderTimeRange = (params: any) => {
    const profile = params.row;
    return profile?.timeRange ? `${profile.timeRange}hrs` : "";
  };

  const renderClassifications = (params: any) => {
    const profile = params.row;
    return profile?.classifications ? (
      <div>
        <p>
          {" "}
          {profile?.classificationsWith === false
            ? "Without any of:"
            : "With any of:"}{" "}
        </p>
        {profile.classifications.map((classification: string) => (
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

  const renderGroups = (params: any) => {
    const profile = params.row;
    return profile?.groupIDs ? (
      <div>
        {profile.groupIDs.map((groupID: any) => {
          const groupName = userAccessibleGroups?.find(
            (group) => group.id === groupID,
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

  const renderSavedStatus = (params: any) => {
    const profile = params.row;
    const option = savedStatusSelectOptions.find(
      (selectOption) => selectOption.value === profile?.savedStatus,
    );
    return option?.label || "";
  };

  const renderRedshift = (params: any) => {
    const profile = params.row;
    return `Min: ${profile?.redshiftMinimum || "N/A"}, Max: ${
      profile?.redshiftMaximum || "N/A"
    }`;
  };

  const renderSorting = (params: any) => {
    const profile = params.row;
    return profile?.sortingOrigin
      ? `${profile.sortingOrigin}: ${profile.sortingKey}, ${profile.sortingOrder}`
      : "";
  };

  const renderRejectedStatus = (params: any) => {
    const dataIndex = params.row.__rowid;
    const profile = params.row;
    return profile?.rejectedStatus === "show" ? (
      <CheckIcon key={`${dataIndex}RejectedStatus`} color="primary" />
    ) : (
      <ClearIcon key={`${dataIndex}RejectedStatus`} color="secondary" />
    );
  };

  const renderActions = (params: any) => {
    const dataIndex = params.row.__rowid;
    return (
      <div className={classes.actionButtons}>
        <IconButton
          key={`edit_${dataIndex}`}
          id={`edit_button_${dataIndex}`}
          onClick={() => editProfile(profiles[dataIndex])}
        >
          <EditIcon />
        </IconButton>
        <IconButton
          id={`delete_button_${dataIndex}`}
          onClick={() => deleteProfile(dataIndex)}
        >
          <DeleteIcon />
        </IconButton>
      </div>
    );
  };

  const columns: any[] = [
    {
      field: "loaded",
      headerName: "Currently Loaded",
      width: 140,
      sortable: false,
      renderCell: renderLoaded,
    },
    {
      field: "default",
      headerName: "Default",
      width: 90,
      sortable: false,
      renderCell: renderDefault,
    },
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 120,
      sortable: false,
    },
    {
      field: "timeRange",
      headerName: "Hours Before Now",
      flex: 1,
      minWidth: 140,
      sortable: false,
      renderCell: renderTimeRange,
    },
    {
      field: "groupIDs",
      headerName: "Selected Programs",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: renderGroups,
    },
    {
      field: "savedStatus",
      headerName: "Candidate Saved Status",
      flex: 1,
      minWidth: 180,
      sortable: false,
      renderCell: renderSavedStatus,
    },
    {
      field: "redshiftMinimum",
      headerName: "Redshift Range",
      flex: 1,
      minWidth: 140,
      sortable: false,
      renderCell: renderRedshift,
    },
    {
      field: "sortingOrigin",
      headerName: "Annotation Sorting",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: renderSorting,
    },
    {
      field: "rejectedStatus",
      headerName: "Show Rejected",
      width: 120,
      sortable: false,
      renderCell: renderRejectedStatus,
    },
    {
      field: "classifications",
      headerName: "Classifications",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: renderClassifications,
    },
    {
      field: "manage",
      headerName: " ",
      width: 100,
      sortable: false,
      filterable: false,
      renderCell: renderActions,
    },
  ];

  const rows = (profiles || []).map((profile: any, index: number) => ({
    ...profile,
    __rowid: index,
  }));

  return (
    <div>
      <Paper className={classes.container}>
        <Typography variant="h6" sx={{ p: 1 }}>
          Scanning Profiles
        </Typography>
        <StyledDataGrid
          autoHeight
          rows={rows}
          columns={columns}
          getRowId={(row: any) => row.__rowid}
          disableColumnFilter
          slots={{ toolbar: CustomToolbar }}
          showToolbar
        />
      </Paper>
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)}>
        <DialogContent>
          <CandidatesPreferencesForm
            {...({
              userAccessibleGroups,
              availableAnnotationsInfo,
              classifications,
              addOrEdit: "Edit",
              editingProfile: profileToEdit,
              closeDialog: () => setEditDialogOpen(false),
              selectedScanningProfile,
              setSelectedScanningProfile,
            } as any)}
          />
        </DialogContent>
      </Dialog>
      <Dialog open={newDialogOpen} onClose={() => setNewDialogOpen(false)}>
        <DialogContent>
          <CandidatesPreferencesForm
            {...({
              userAccessibleGroups,
              availableAnnotationsInfo,
              classifications,
              addOrEdit: "Add",
              setSelectedScanningProfile,
              closeDialog: () => setNewDialogOpen(false),
            } as any)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ScanningProfilesList;
