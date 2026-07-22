import { useState } from "react";
import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useDeleteDefaultSurveyEfficiencyMutation } from "../../ducks/default_survey_efficiencies";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewDefaultSurveyEfficiency from "./NewDefaultSurveyEfficiency";
import { useIsReadOnly } from "../../ducks/profile";

interface DefaultSurveyEfficiencyTableProps {
  default_survey_efficiencies: any[];
  deletePermission?: boolean;
}

const DefaultSurveyEfficiencyTable = ({
  default_survey_efficiencies,
  deletePermission = false,
}: DefaultSurveyEfficiencyTableProps) => {
  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const [deleteDefaultSurveyEfficiencyMutation] =
    useDeleteDefaultSurveyEfficiencyMutation();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [defaultSurveyEfficiencyToDelete, setDefaultSurveyEfficiencyToDelete] =
    useState<any>(null);

  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openDeleteDialog = (id: any) => {
    setDeleteDialogOpen(true);
    setDefaultSurveyEfficiencyToDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setDefaultSurveyEfficiencyToDelete(null);
  };

  const deleteDefaultSurveyEfficiency = () => {
    deleteDefaultSurveyEfficiencyMutation(defaultSurveyEfficiencyToDelete)
      .unwrap()
      .then(() => {
        dispatch(showNotification("Default survey efficiency deleted"));
        closeDeleteDialog();
      })
      .catch(() => {
        // error notification handled by the base query
      });
  };

  const renderDelete = (params: any) => {
    if (!deletePermission) return null;
    return (
      <IconButton color="error" onClick={() => openDeleteDialog(params.row.id)}>
        <DeleteIcon />
      </IconButton>
    );
  };

  const columns: any[] = [
    {
      field: "defaultSurveyEfficiency",
      headerName: "Default Plan",
      flex: 1,
      minWidth: 160,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        row.default_observationplan_request?.default_plan_name || "",
    },
    {
      field: "modelName",
      headerName: "Model Name",
      flex: 1,
      minWidth: 130,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.payload?.modelName || "",
    },
    {
      field: "numInjections",
      headerName: "Number of Injections",
      flex: 1,
      minWidth: 160,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.payload?.numberInjections,
    },
    {
      field: "maxPhase",
      headerName: "Maximum Phase (days)",
      flex: 1,
      minWidth: 170,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.payload?.maximumPhase,
    },
    {
      field: "minPhase",
      headerName: "Minimum Phase (days)",
      flex: 1,
      minWidth: 170,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.payload?.minimumPhase,
    },
    {
      field: "numDetections",
      headerName: "Number of Detections",
      flex: 1,
      minWidth: 170,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.payload?.numberDetections,
    },
    {
      field: "detectionThreshold",
      headerName: "Detection Threshold (sigma)",
      flex: 1,
      minWidth: 200,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.payload?.detectionThreshold,
    },
    {
      field: "cumProb",
      headerName: "Cumulative Probability",
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.payload?.localizationCumprob,
    },
    {
      field: "injectionParameters",
      headerName: "Optional Injection Parameters",
      flex: 1,
      minWidth: 210,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        row.payload?.optionalInjectionParameters,
    },
    {
      field: "delete",
      headerName: " ",
      width: 90,
      sortable: false,
      filterable: false,
      renderCell: renderDelete,
    },
  ];

  const CustomToolbar = () => (
    <DataGridToolbar
      showQuickFilter={false}
      title="Default Survey Efficiencies"
    >
      {!isReadOnly && (
        <IconButton size="small" onClick={() => openNewDialog()}>
          <AddIcon />
        </IconButton>
      )}
    </DataGridToolbar>
  );

  return (
    <div>
      <StyledDataGrid
        autoHeight
        rows={default_survey_efficiencies || []}
        columns={columns}
        getRowId={(row: any) => row.id}
        hideFooter
        slots={{ toolbar: CustomToolbar }}
        showToolbar
      />
      <Dialog open={newDialogOpen} onClose={closeNewDialog} maxWidth="md">
        <DialogTitle>New Default Survey Efficiency</DialogTitle>
        <DialogContent dividers>
          <NewDefaultSurveyEfficiency onClose={closeNewDialog} />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteDefaultSurveyEfficiency}
        dialogOpen={deleteDialogOpen}
        closeDialog={closeDeleteDialog}
        resourceName="default survey efficiency"
      />
    </div>
  );
};

export default DefaultSurveyEfficiencyTable;
