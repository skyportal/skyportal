import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import Paper from "@mui/material/Paper";
import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarExport,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useDeleteDefaultSurveyEfficiencyMutation } from "../../ducks/default_survey_efficiencies";
import StyledDataGrid from "../StyledDataGrid";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewDefaultSurveyEfficiency from "./NewDefaultSurveyEfficiency";

const useStyles = makeStyles()(() => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
}));

// Map each DataGrid column `field` to the field name the server expects for
// sorting. Columns absent from this map fall through to the field itself.
const SERVER_SORT_FIELD: Record<string, string> = {
  defaultSurveyEfficiency: "defaultSurveyEfficiency",
  modelName: "modelName",
};

interface DefaultSurveyEfficiencyTableProps {
  default_survey_efficiencies: any[];
  paginateCallback: (...args: any[]) => void;
  sortingCallback?: ((...args: any[]) => void) | null;
  totalMatches?: number;
  deletePermission?: boolean;
}

const DefaultSurveyEfficiencyTable = ({
  default_survey_efficiencies,
  paginateCallback,
  totalMatches = 0,
  sortingCallback = null,
  deletePermission = false,
}: DefaultSurveyEfficiencyTableProps) => {
  const { classes } = useStyles();

  const dispatch = useAppDispatch();
  const [deleteDefaultSurveyEfficiencyMutation] =
    useDeleteDefaultSurveyEfficiencyMutation();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [defaultSurveyEfficiencyToDelete, setDefaultSurveyEfficiencyToDelete] =
    useState<any>(null);
  const [sortModel, setSortModel] = useState<any[]>([]);

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

  const handleSortModelChange = (model: any) => {
    setSortModel(model);
    if (!model.length) {
      paginateCallback(1, 100, {});
      return;
    }
    const { field, sort } = model[0];
    sortingCallback?.({
      name: SERVER_SORT_FIELD[field] || field,
      direction: sort,
    });
  };

  const renderSurveyEfficiencyTitle = (params: any) => (
    <div>{params.row.default_observationplan_request.default_plan_name}</div>
  );

  const renderModelName = (params: any) => (
    <div>{params.row ? params.row.payload.modelName : ""}</div>
  );

  const renderMaxPhase = (params: any) => (
    <div>{params.row ? params.row.payload.maximumPhase : ""}</div>
  );

  const renderMinPhase = (params: any) => (
    <div>{params.row ? params.row.payload.minimumPhase : ""}</div>
  );

  const renderNumDetections = (params: any) => (
    <div>{params.row ? params.row.payload.numberDetections : ""}</div>
  );

  const renderNumInjections = (params: any) => (
    <div>{params.row ? params.row.payload.numberInjections : ""}</div>
  );

  const renderDetectionThreshold = (params: any) => (
    <div>{params.row ? params.row.payload.detectionThreshold : ""}</div>
  );

  const renderLocCumprob = (params: any) => (
    <div>{params.row ? params.row.payload.localizationCumprob : ""}</div>
  );

  const renderInjectionParameters = (params: any) => (
    <div>
      {params.row ? params.row.payload.optionalInjectionParameters : ""}
    </div>
  );

  const renderDelete = (params: any) => {
    if (!deletePermission) {
      return null;
    }
    return (
      <div>
        <Button
          id="delete_button"
          classes={{
            root: (classes as any).defaultSurveyEfficiencyDelete,
            disabled: (classes as any).defaultSurveyEfficiencyDeleteDisabled,
          }}
          onClick={() => openDeleteDialog(params.row.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
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
      renderCell: renderSurveyEfficiencyTitle,
    },
    {
      field: "modelName",
      headerName: "Model Name",
      flex: 1,
      minWidth: 130,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.payload?.modelName || "",
      renderCell: renderModelName,
    },
    {
      field: "numInjections",
      headerName: "Number of Injections",
      flex: 1,
      minWidth: 160,
      sortable: false,
      filterable: false,
      renderCell: renderNumInjections,
    },
    {
      field: "maxPhase",
      headerName: "Maximum Phase (days)",
      flex: 1,
      minWidth: 170,
      sortable: false,
      filterable: false,
      renderCell: renderMaxPhase,
    },
    {
      field: "minPhase",
      headerName: "Minimum Phase (days)",
      flex: 1,
      minWidth: 170,
      sortable: false,
      filterable: false,
      renderCell: renderMinPhase,
    },
    {
      field: "numDetections",
      headerName: "Number of Detections",
      flex: 1,
      minWidth: 170,
      sortable: false,
      filterable: false,
      renderCell: renderNumDetections,
    },
    {
      field: "detectionThreshold",
      headerName: "Detection Threshold (sigma)",
      flex: 1,
      minWidth: 200,
      sortable: false,
      filterable: false,
      renderCell: renderDetectionThreshold,
    },
    {
      field: "cumProb",
      headerName: "Cumulative Probability",
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      renderCell: renderLocCumprob,
    },
    {
      field: "injectionParameters",
      headerName: "Optional Injection Parameters",
      flex: 1,
      minWidth: 210,
      sortable: false,
      filterable: false,
      renderCell: renderInjectionParameters,
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
    <GridToolbarContainer>
      <GridToolbarColumnsButton />
      <GridToolbarExport />
      <IconButton
        name="new_default_survey_efficiency"
        size="small"
        onClick={() => {
          openNewDialog();
        }}
      >
        <AddIcon />
      </IconButton>
    </GridToolbarContainer>
  );

  return (
    <div>
      <Paper className={classes.container}>
        <Typography variant="h6" style={{ padding: "0.5rem" }}>
          Default Survey Efficiencies
        </Typography>
        <Box sx={{ width: "100%" }}>
          <StyledDataGrid
            autoHeight
            rows={default_survey_efficiencies || []}
            columns={columns}
            getRowId={(row: any) => row.id}
            rowCount={totalMatches}
            sortingMode="server"
            sortModel={sortModel}
            onSortModelChange={handleSortModelChange}
            hideFooter
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
      </Paper>
      {newDialogOpen && (
        <Dialog open={newDialogOpen} onClose={closeNewDialog} maxWidth="md">
          <DialogTitle>New Default Survey Efficiency</DialogTitle>
          <DialogContent dividers>
            <NewDefaultSurveyEfficiency onClose={closeNewDialog} />
          </DialogContent>
        </Dialog>
      )}
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
