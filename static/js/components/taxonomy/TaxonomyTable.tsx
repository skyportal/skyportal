import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ReactJson from "react-json-view";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { useDeleteTaxonomyMutation } from "../../ducks/taxonomies";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import TaxonomyForm from "./TaxonomyForm";
import { useIsReadOnly } from "../../ducks/profile";
import Chip from "@mui/material/Chip";

interface TaxonomyTableProps {
  taxonomies: any[];
  managePermission: boolean;
  deletePermission: boolean;
}

const TaxonomyTable = ({
  taxonomies,
  managePermission,
  deletePermission,
}: TaxonomyTableProps) => {
  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const [deleteTaxonomyMutation] = useDeleteTaxonomyMutation();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [taxonomyToViewEditDelete, setTaxonomyToViewEditDelete] =
    useState<any>(null);
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openDetailsDialog = (id: any) => {
    setDetailsDialogOpen(true);
    setTaxonomyToViewEditDelete(id);
  };
  const closeDetailsDialog = () => {
    setDetailsDialogOpen(false);
    setTaxonomyToViewEditDelete(null);
  };
  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setTaxonomyToViewEditDelete(null);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setTaxonomyToViewEditDelete(null);
  };

  const deleteTaxonomy = async () => {
    try {
      await deleteTaxonomyMutation(taxonomyToViewEditDelete).unwrap();
      dispatch(showNotification("Taxonomy deleted"));
      closeDeleteDialog();
    } catch {
      // error notification handled by the base query
    }
  };

  const renderBool = (params: any) =>
    params.value ? (
      <Chip label="Yes" color="primary" size="small" />
    ) : (
      <Chip label="No" size="small" />
    );

  const renderGroups = (params: any) =>
    params.value?.map((group: any) => (
      <Chip key={group.id} label={group.name} />
    ));

  const renderDetails = (params: any) => {
    const taxonomy = params.row;
    return (
      <IconButton onClick={() => openDetailsDialog(taxonomy.id)}>
        <HistoryEduIcon />
      </IconButton>
    );
  };

  const renderManage = (params: any) => {
    const taxonomy = params.row;
    return (
      <Box style={{ display: "flex" }}>
        {managePermission && (
          <IconButton
            onClick={() => {
              setEditDialogOpen(true);
              setTaxonomyToViewEditDelete(taxonomy.id);
            }}
          >
            <EditIcon />
          </IconButton>
        )}
        {deletePermission && (
          <IconButton
            color="error"
            onClick={() => {
              setDeleteDialogOpen(true);
              setTaxonomyToViewEditDelete(taxonomy.id);
            }}
          >
            <DeleteIcon />
          </IconButton>
        )}
      </Box>
    );
  };

  const columns: any[] = [
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 120,
    },
    {
      field: "id",
      headerName: "ID",
      flex: 1,
      minWidth: 80,
    },
    {
      field: "isLatest",
      headerName: "isLatest",
      flex: 1,
      minWidth: 90,
      renderCell: renderBool,
    },
    {
      field: "provenance",
      headerName: "Provenance",
      flex: 1,
      minWidth: 120,
    },
    {
      field: "version",
      headerName: "Version",
      flex: 1,
      minWidth: 90,
    },
    {
      field: "groups",
      headerName: "Groups",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: renderGroups,
    },
    {
      field: "details",
      headerName: "Hierarchy",
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
      renderCell: renderDetails,
    },
    (managePermission || deletePermission) && {
      field: "manage",
      headerName: " ",
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: renderManage,
    },
  ].filter(Boolean);

  const CustomToolbar = function TaxonomyTableToolbar() {
    return (
      <DataGridToolbar title="Taxonomies">
        {managePermission && !isReadOnly && (
          <IconButton
            name="new_taxonomy"
            onClick={() => setNewDialogOpen(true)}
          >
            <AddIcon />
          </IconButton>
        )}
      </DataGridToolbar>
    );
  };

  return (
    <Box sx={{ width: "100%" }}>
      <StyledDataGrid
        autoHeight
        rows={taxonomies}
        columns={columns}
        getRowId={(row: any) => row.id}
        disableColumnFilter
        slots={{ toolbar: CustomToolbar }}
        showToolbar
      />
      <Dialog open={newDialogOpen} onClose={closeNewDialog} maxWidth="md">
        <DialogTitle>New Taxonomy</DialogTitle>
        <DialogContent dividers>
          <TaxonomyForm onClose={closeNewDialog} />
        </DialogContent>
      </Dialog>
      <Dialog
        open={detailsDialogOpen && taxonomyToViewEditDelete}
        onClose={closeDetailsDialog}
        maxWidth="lg"
      >
        <DialogTitle>Taxonomy Content</DialogTitle>
        <DialogContent dividers>
          <ReactJson
            src={taxonomies[taxonomyToViewEditDelete]?.hierarchy || {}}
            name={false}
            displayDataTypes={false}
            displayObjectSize={false}
            enableClipboard={false}
            collapsed={false}
          />
        </DialogContent>
      </Dialog>
      <Dialog
        open={editDialogOpen && taxonomyToViewEditDelete !== null}
        onClose={closeEditDialog}
        maxWidth="md"
      >
        <DialogTitle>Edit Taxonomy</DialogTitle>
        <DialogContent dividers>
          <TaxonomyForm
            taxonomyId={taxonomyToViewEditDelete}
            onClose={closeEditDialog}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteTaxonomy}
        dialogOpen={deleteDialogOpen && taxonomyToViewEditDelete}
        closeDialog={closeDeleteDialog}
        resourceName="taxonomy"
      />
    </Box>
  );
};

export default TaxonomyTable;
