import { useState } from "react";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { GridColDef } from "@mui/x-data-grid";

import ExpandableCell from "../ExpandableCell";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import { useGetGroupsQuery } from "../../ducks/groups";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
  useIsReadOnly,
} from "../../ducks/profile";
import CandidatesPreferencesForm from "./CandidatesPreferencesForm";
import { savedStatusSelectOptions } from "./scanFormFields";

const ScanningProfilesToolbar = ({
  onAdd,
  onClose,
}: {
  onAdd?: () => void;
  onClose: () => void;
}) => (
  <DataGridToolbar
    title="Scanning Profiles"
    showExport={false}
    showColumns={false}
    showQuickFilter={false}
    onClose={onClose}
    closeTestId="closeScanningProfilesButton"
  >
    {onAdd && (
      <Tooltip title="New scanning profile">
        <IconButton name="new_scanning_profile" onClick={onAdd}>
          <AddIcon />
        </IconButton>
      </Tooltip>
    )}
  </DataGridToolbar>
);

const chips = (labels: (string | undefined)[]) => (
  <ExpandableCell
    items={labels.map((label, index) => (
      <Chip key={index} size="small" label={label} />
    ))}
  />
);

const redshiftRange = ({ redshiftMinimum: min, redshiftMaximum: max }: any) =>
  min && max ? `${min} to ${max}` : min ? `≥ ${min}` : max ? `≤ ${max}` : "";

interface ScanningProfilesListProps {
  selectedScanningProfile?: any;
  setSelectedScanningProfile: (...a: any[]) => void;
  onClose: () => void;
}

const ScanningProfilesList = ({
  selectedScanningProfile,
  setSelectedScanningProfile,
  onClose,
}: ScanningProfilesListProps) => {
  const isReadOnly = useIsReadOnly();
  const profiles: any[] =
    (useGetProfileQuery().data?.preferences as any)?.scanningProfiles ?? [];
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  const [formOpen, setFormOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<any>(null);

  const openForm = (profile: any) => {
    setEditingProfile(profile);
    setFormOpen(true);
  };
  const closeForm = () => setFormOpen(false);
  const updateProfiles = (scanningProfiles: any[]) =>
    updateUserPreferences({ scanningProfiles });
  const deleteProfile = (row: any) => {
    updateProfiles(profiles.filter((_profile, i) => i !== row.id));
    if (selectedScanningProfile?.name === row.name)
      setSelectedScanningProfile(null);
  };

  const columns: GridColDef[] = [
    {
      field: "default",
      headerName: "Default",
      width: 80,
      renderCell: ({ row }) => (
        <Checkbox
          size="small"
          checked={row.default}
          onChange={(event) =>
            updateProfiles(
              profiles.map((profile, index) => ({
                ...profile,
                default: event.target.checked && index === row.id,
              })),
            )
          }
        />
      ),
    },
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 140,
      renderCell: ({ row }) => (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {row.name}
          {selectedScanningProfile?.name === row.name && (
            <Chip size="small" color="primary" label="loaded" />
          )}
        </Box>
      ),
    },
    {
      field: "timeRange",
      headerName: "Time range",
      width: 100,
      renderCell: ({ value }) => (value ? `${value}h` : ""),
    },
    {
      field: "groupIDs",
      headerName: "Groups",
      flex: 1.5,
      minWidth: 150,
      renderCell: ({ value }) =>
        chips(value.map((id: number) => groups.find((g) => g.id === id)?.name)),
    },
    {
      field: "savedStatus",
      headerName: "Saved status",
      flex: 1.5,
      minWidth: 160,
      renderCell: ({ value, row }) => {
        const label =
          savedStatusSelectOptions.find((option) => option.value === value)
            ?.label ?? "";
        const savedGroups = (row.savedGroupIDs ?? [])
          .map((id: number) => groups.find((g) => g.id === id)?.name)
          .filter(Boolean);
        return savedGroups.length
          ? `${label} (${savedGroups.join(", ")})`
          : label;
      },
    },
    {
      field: "rejectedStatus",
      headerName: "Rejected",
      width: 90,
      renderCell: ({ value }) => (value === "hide" ? "hidden" : "shown"),
    },
    {
      field: "redshift",
      headerName: "Redshift",
      width: 110,
      renderCell: ({ row }) => redshiftRange(row),
    },
    {
      field: "classifications",
      headerName: "Classifications",
      flex: 1,
      minWidth: 150,
      renderCell: ({ row }) =>
        row.classifications && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            {row.classificationsWith === false ? "Without" : "With"}
            {chips(row.classifications)}
          </Box>
        ),
    },
    {
      field: "sortingOrigin",
      headerName: "Sorting",
      flex: 1,
      minWidth: 140,
      renderCell: ({ row }) =>
        row.sortingOrigin
          ? `${row.sortingOrigin}: ${row.sortingKey}, ${row.sortingOrder}`
          : "",
    },
    {
      field: "manage",
      headerName: "",
      width: 100,
      renderCell: ({ row }) =>
        !isReadOnly && (
          <Box sx={{ display: "flex", alignItems: "center", height: "100%" }}>
            <Tooltip title="Edit">
              <IconButton
                size="small"
                onClick={() => openForm(profiles[row.id])}
              >
                <EditIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete">
              <IconButton
                size="small"
                color="error"
                onClick={() => deleteProfile(row)}
              >
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          </Box>
        ),
    },
  ];

  return (
    <>
      <StyledDataGrid
        autoHeight
        rows={profiles.map((profile, id) => ({ ...profile, id }))}
        columns={columns}
        getRowHeight={() => "auto"}
        sx={{ "& .MuiDataGrid-cell": { py: 0.5 } }}
        disableColumnFilter
        disableColumnSorting
        slots={{ toolbar: ScanningProfilesToolbar }}
        slotProps={{
          toolbar: {
            onAdd: isReadOnly ? undefined : () => openForm(null),
            onClose,
          },
        }}
        showToolbar
      />
      <Dialog open={formOpen} onClose={closeForm} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingProfile ? "Edit scanning profile" : "New scanning profile"}
        </DialogTitle>
        <DialogContent>
          <CandidatesPreferencesForm
            editingProfile={editingProfile}
            onClose={closeForm}
            selectedScanningProfile={selectedScanningProfile}
            setSelectedScanningProfile={setSelectedScanningProfile}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ScanningProfilesList;
