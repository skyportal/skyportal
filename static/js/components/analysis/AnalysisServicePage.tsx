import { useEffect, useMemo, useState } from "react";

import { makeStyles } from "tss-react/mui";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";
import CircularProgress from "@mui/material/CircularProgress";
import ReactJson from "react-json-view";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";

import { showNotification } from "baselayer/components/Notifications";
import { useAppSelector, useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewAnalysisService from "./NewAnalysisService";

import * as analysisServicesActions from "../../ducks/analysis_services";

const useStyles = makeStyles()((theme) => ({
  root: {
    width: "100%",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
  },
  analysisServiceDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  analysisServiceManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

export function analysisServiceTitle(analysisService: any) {
  if (!analysisService?.display_name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${analysisService?.display_name}`;

  return result;
}

export function analysisServiceInfo(analysisService: any) {
  if (!analysisService?.url) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const share_groups: any[] = [];
  analysisService.groups.forEach((share_group: any) => {
    share_groups.push(share_group.name);
  });

  let result = `Description: ${analysisService.description} / URL: ${analysisService.url}`;

  if (share_groups.length > 0) {
    result += "\r\n(";
    result += `Default Share Groups: ${share_groups.join(", ")}`;
    result += ")";
  }

  return result;
}

interface AnalysisServiceListProps {
  analysisServices: any[];
  deletePermission: boolean;
}

const AnalysisServiceList = ({
  analysisServices,
  deletePermission,
}: AnalysisServiceListProps) => {
  const dispatch = useAppDispatch();
  const { classes } = useStyles();
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [analysisServiceToViewDelete, setAnalysisServiceToViewDelete] =
    useState<any>(null);
  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openDetailsDialog = (id: any) => {
    setDetailsDialogOpen(true);
    setAnalysisServiceToViewDelete(id);
  };
  const closeDetailsDialog = () => {
    setDetailsDialogOpen(false);
    setAnalysisServiceToViewDelete(null);
  };

  const openDeleteDialog = (id: any) => {
    setDeleteDialogOpen(true);
    setAnalysisServiceToViewDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setAnalysisServiceToViewDelete(null);
  };

  const deleteAnalysisService = () => {
    dispatch(
      analysisServicesActions.deleteAnalysisService(
        analysisServiceToViewDelete,
      ),
    ).then((result: any) => {
      if (result.status === "success") {
        dispatch(showNotification("AnalysisService deleted"));
        closeDeleteDialog();
      }
    });
  };

  const renderContact = (params: any) => {
    const analysis_service = params.row;
    if (!analysis_service.contact_name) {
      return null;
    }
    let contactText = analysis_service.contact_name;
    if (analysis_service.contact_email) {
      contactText += ` (${analysis_service.contact_email})`;
    }
    return (
      <div>
        <Typography variant="body2">{contactText}</Typography>
      </div>
    );
  };

  const renderShareGroups = (params: any) => {
    const analysis_service = params.row;

    const group_names = (analysis_service?.groups || []).map(
      (group: any) => group.name,
    );

    return <div>{group_names.length > 0 ? group_names.join(", ") : ""}</div>;
  };

  const renderDetails = (params: any) => {
    const analysis_service = params.row;
    return (
      <IconButton
        key={`details_${analysis_service.id}`}
        id={`details_button_${analysis_service.id}`}
        onClick={() => openDetailsDialog(analysis_service.id)}
      >
        <HistoryEduIcon />
      </IconButton>
    );
  };

  const renderManage = (params: any) => {
    const analysis_service = params.row;
    if (!deletePermission) {
      return null;
    }
    return (
      <div className={classes.analysisServiceManage}>
        <Button
          id={`delete_button_${analysis_service.id}`}
          onClick={() => openDeleteDialog(analysis_service.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const columns: any[] = [
    {
      field: "display_name",
      headerName: "Name",
      flex: 1,
      minWidth: 140,
      filterable: false,
    },
    {
      field: "description",
      headerName: "Description",
      flex: 1,
      minWidth: 160,
      filterable: false,
      sortable: false,
    },
    {
      field: "version",
      headerName: "Version",
      flex: 1,
      minWidth: 100,
      filterable: false,
      sortable: false,
    },
    {
      field: "url",
      headerName: "URL",
      flex: 1,
      minWidth: 160,
      filterable: false,
      sortable: false,
    },
    {
      field: "contact",
      headerName: "Contact",
      flex: 1,
      minWidth: 160,
      filterable: false,
      sortable: false,
      renderCell: renderContact,
    },
    {
      field: "default_share_group",
      headerName: "Default Share Groups",
      flex: 1,
      minWidth: 180,
      filterable: false,
      sortable: false,
      renderCell: renderShareGroups,
    },
    {
      field: "details",
      headerName: "Details",
      flex: 1,
      minWidth: 100,
      filterable: false,
      sortable: false,
      renderCell: renderDetails,
    },
  ];

  if (deletePermission) {
    columns.push({
      field: "manage",
      headerName: " ",
      flex: 1,
      minWidth: 80,
      filterable: false,
      sortable: false,
      renderCell: renderManage,
    });
  }

  // Memoized so the toolbar (and its "new analysis service" button) keeps a
  // stable identity across the re-render that happens when the analysis
  // services list finishes loading; otherwise MUI remounts it and any element
  // reference a test is interacting with goes stale.
  const CustomToolbar = useMemo(
    () =>
      function AnalysisServiceToolbar() {
        return (
          <GridToolbarContainer>
            <GridToolbarColumnsButton />
            {deletePermission && (
              <IconButton
                name="new_analysis_service"
                onClick={() => {
                  openNewDialog();
                }}
              >
                <AddIcon />
              </IconButton>
            )}
          </GridToolbarContainer>
        );
      },

    [deletePermission],
  );

  return (
    <div className={classes.root}>
      <Paper>
        <Typography variant="h6">Analysis Services</Typography>
        <StyledDataGrid
          autoHeight
          rows={analysisServices || []}
          columns={columns}
          getRowId={(row: any) => row.id}
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } },
          }}
          pageSizeOptions={[10, 25, 50, 100]}
          slots={{ toolbar: CustomToolbar }}
          showToolbar
        />
        <Dialog open={newDialogOpen} onClose={closeNewDialog} maxWidth="md">
          <DialogTitle>New Analysis Service</DialogTitle>
          <DialogContent dividers>
            <NewAnalysisService onClose={closeNewDialog} />
          </DialogContent>
        </Dialog>
        <Dialog
          open={Boolean(detailsDialogOpen && analysisServiceToViewDelete)}
          onClose={closeDetailsDialog}
          maxWidth="lg"
        >
          <DialogTitle>Analysis Service Details</DialogTitle>
          <DialogContent dividers>
            <ReactJson
              src={
                (analysisServices || []).find(
                  (analysisService: any) =>
                    analysisService?.id === analysisServiceToViewDelete,
                ) || {}
              }
              name={false}
              displayDataTypes={false}
              displayObjectSize={false}
              enableClipboard={false}
              collapsed={false}
            />
          </DialogContent>
        </Dialog>
        <ConfirmDeletionDialog
          deleteFunction={deleteAnalysisService}
          dialogOpen={Boolean(deleteDialogOpen && analysisServiceToViewDelete)}
          closeDialog={closeDeleteDialog}
          resourceName="analysis service"
        />
      </Paper>
    </div>
  );
};

const AnalysisServicePage = () => {
  const { analysisServiceList } = useAppSelector(
    (state) => (state as any).analysis_services,
  );

  const currentUser = useAppSelector((state) => state.profile);
  const dispatch = useAppDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage Analysis Services");

  useEffect(() => {
    const getAnalysisServices = async () => {
      await dispatch(analysisServicesActions.fetchAnalysisServices());
    };

    getAnalysisServices();
  }, []);

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <AnalysisServiceList
          analysisServices={analysisServiceList || []}
          deletePermission={permission}
        />
      </Grid>
    </Grid>
  );
};

export default AnalysisServicePage;
