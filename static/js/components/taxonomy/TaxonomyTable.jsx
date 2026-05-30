import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import { makeStyles } from "tss-react/mui";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ReactJson from "react-json-view";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";

import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import ModifyTaxonomy from "./ModifyTaxonomy";
import NewTaxonomy from "./NewTaxonomy";
import * as taxonomyActions from "../../ducks/taxonomies";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

// Map each DataGrid column `field` to the field name the server expects for
// sorting. Columns absent from this map are not server-sortable.
const SERVER_SORT_FIELD = {
  name: "name",
  id: "id",
  isLatest: "isLatest",
  provenance: "provenance",
  version: "version",
};

const useStyles = makeStyles()((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
    taxonomyDelete: {
      cursor: "pointer",
      fontSize: "2em",
      position: "absolute",
      padding: 0,
      right: 0,
      top: 0,
    },
    taxonomyDeleteDisabled: {
      opacity: 0,
    },
  },
}));

const TaxonomyTable = ({
  taxonomies,
  paginateCallback,
  totalMatches,
  deletePermission,
  sortingCallback,
}) => {
  const { classes } = useStyles();

  const dispatch = useDispatch();

  const [rowsPerPage, setRowsPerPage] = useState(100);
  const [sortModel, setSortModel] = useState([]);

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [taxonomyToViewEditDelete, setTaxonomyToViewEditDelete] =
    useState(null);
  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openDetailsDialog = (id) => {
    setDetailsDialogOpen(true);
    setTaxonomyToViewEditDelete(id);
  };
  const closeDetailsDialog = () => {
    setDetailsDialogOpen(false);
    setTaxonomyToViewEditDelete(null);
  };

  const openEditDialog = (id) => {
    setEditDialogOpen(true);
    setTaxonomyToViewEditDelete(id);
  };
  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setTaxonomyToViewEditDelete(null);
  };

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setTaxonomyToViewEditDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setTaxonomyToViewEditDelete(null);
  };

  const deleteTaxonomy = () => {
    dispatch(taxonomyActions.deleteTaxonomy(taxonomyToViewEditDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Taxonomy deleted"));
          closeDeleteDialog();
        }
      },
    );
  };

  const renderName = (params) => {
    const taxonomy = params.row;
    return <div>{taxonomy ? taxonomy.name : ""}</div>;
  };

  const renderID = (params) => {
    const taxonomy = params.row;
    return <div>{taxonomy ? taxonomy.id : ""}</div>;
  };

  const renderIsLatest = (params) => {
    const taxonomy = params.row;
    return <div>{taxonomy ? taxonomy.isLatest.toString() : ""}</div>;
  };

  const renderProvenance = (params) => {
    const taxonomy = params.row;
    return <div>{taxonomy ? taxonomy.provenance : ""}</div>;
  };

  const renderVersion = (params) => {
    const taxonomy = params.row;
    return <div>{taxonomy ? taxonomy.version : ""}</div>;
  };

  const renderGroups = (params) => {
    const taxonomy = params.row;
    const groupNames = [];
    taxonomy?.groups?.forEach((group) => {
      groupNames.push(group.name);
    });
    return <div>{groupNames.length > 0 ? groupNames.join("\n") : ""}</div>;
  };

  const renderDetails = (params) => {
    const taxonomy = params.row;
    return (
      <IconButton
        key={`details_${taxonomy.id}`}
        id={`details_button_${taxonomy.id}`}
        onClick={() => openDetailsDialog(taxonomy.id)}
      >
        <HistoryEduIcon />
      </IconButton>
    );
  };

  const renderManage = (params) => {
    if (!deletePermission) {
      return null;
    }
    const taxonomy = params.row;
    return (
      <div className={classes.taxonomyManage}>
        <Button
          key={`edit_${taxonomy.id}`}
          id={`edit_button_${taxonomy.id}`}
          onClick={() => openEditDialog(taxonomy.id)}
          disabled={!deletePermission}
        >
          <EditIcon />
        </Button>
        <Button
          id={`delete_button_${taxonomy.id}`}
          onClick={() => openDeleteDialog(taxonomy.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const currentSortOrder = () =>
    sortModel.length
      ? {
          name: SERVER_SORT_FIELD[sortModel[0].field] || sortModel[0].field,
          direction: sortModel[0].sort,
        }
      : {};

  const handlePaginationModelChange = (model) => {
    setRowsPerPage(model.pageSize);
    paginateCallback(model.page + 1, model.pageSize, currentSortOrder());
  };

  const handleSortModelChange = (model) => {
    setSortModel(model);
    if (!model.length) {
      paginateCallback(1, rowsPerPage, {});
      return;
    }
    const { field, sort } = model[0];
    sortingCallback({
      name: SERVER_SORT_FIELD[field] || field,
      direction: sort,
    });
  };

  const columns = [
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 120,
      renderCell: renderName,
    },
    {
      field: "id",
      headerName: "ID",
      flex: 1,
      minWidth: 80,
      renderCell: renderID,
    },
    {
      field: "isLatest",
      headerName: "isLatest",
      flex: 1,
      minWidth: 90,
      renderCell: renderIsLatest,
    },
    {
      field: "provenance",
      headerName: "Provenance",
      flex: 1,
      minWidth: 120,
      renderCell: renderProvenance,
    },
    {
      field: "version",
      headerName: "Version",
      flex: 1,
      minWidth: 90,
      renderCell: renderVersion,
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
    {
      field: "manage",
      headerName: " ",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: renderManage,
    },
  ];

  const CustomToolbar = function TaxonomyTableToolbar() {
    return (
      <GridToolbarContainer>
        <GridToolbarColumnsButton />
        <IconButton
          name="new_taxonomy"
          onClick={() => {
            openNewDialog();
          }}
        >
          <AddIcon />
        </IconButton>
      </GridToolbarContainer>
    );
  };

  return (
    <div>
      <Paper className={classes.container}>
        <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
          Taxonomies
        </Typography>
        <Box sx={{ width: "100%" }}>
          <StyledDataGrid
            autoHeight
            rows={taxonomies}
            columns={columns}
            getRowId={(row) => row.id}
            paginationMode="server"
            sortingMode="server"
            rowCount={totalMatches}
            paginationModel={{ page: 0, pageSize: rowsPerPage }}
            onPaginationModelChange={handlePaginationModelChange}
            sortModel={sortModel}
            onSortModelChange={handleSortModelChange}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            disableColumnFilter
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
      </Paper>
      <Dialog open={newDialogOpen} onClose={closeNewDialog} maxWidth="md">
        <DialogTitle>New Taxonomy</DialogTitle>
        <DialogContent dividers>
          <NewTaxonomy onClose={closeNewDialog} />
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
          <ModifyTaxonomy
            taxonomy_id={taxonomyToViewEditDelete}
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
    </div>
  );
};

TaxonomyTable.propTypes = {
  taxonomies: PropTypes.arrayOf(PropTypes.any).isRequired,
  paginateCallback: PropTypes.func.isRequired,
  sortingCallback: PropTypes.func,
  totalMatches: PropTypes.number,
  deletePermission: PropTypes.bool.isRequired,
};

TaxonomyTable.defaultProps = {
  totalMatches: 0,
  sortingCallback: null,
};

export default TaxonomyTable;
