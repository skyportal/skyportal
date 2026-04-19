import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ReactJson from "react-json-view";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";

import { showNotification } from "baselayer/components/Notifications";

import MUIDataTable from "mui-datatables";
import * as taxonomyActions from "../../ducks/taxonomies";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import TaxonomyForm from "./TaxonomyForm";
import Button from "../Button";
import Chip from "@mui/material/Chip";

const TaxonomyTable = ({
  taxonomies,
  paginateCallback,
  totalMatches,
  managePermission,
  sortingCallback,
}) => {
  const dispatch = useDispatch();
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [showHierarchy, setShowHierarchy] = useState(null);
  const [editTaxonomy, setEditTaxonomy] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [taxonomyToViewEditDelete, setTaxonomyToViewEditDelete] =
    useState(null);

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

  const renderGroups = (dataIndex) => {
    return taxonomies[dataIndex]?.groups?.map((g) => (
      <Chip key={g.id} label={g.name} />
    ));
  };

  const renderDetails = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];
    return (
      <IconButton onClick={() => setShowHierarchy(taxonomy.hierarchy)}>
        <HistoryEduIcon />
      </IconButton>
    );
  };

  const renderManage = (dataIndex) => {
    if (!managePermission) return null;

    const taxonomy = taxonomies[dataIndex];
    return (
      <div>
        <Button
          onClick={() => {
            setEditTaxonomy(taxonomy.id);
            setFormDialogOpen(true);
          }}
        >
          <EditIcon />
        </Button>
        <Button
          onClick={() => {
            setDeleteDialogOpen(true);
            setTaxonomyToViewEditDelete(taxonomy.id);
          }}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const handleTableChange = (action, tableState) => {
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        paginateCallback(
          tableState.page + 1,
          tableState.rowsPerPage,
          tableState.sortOrder,
        );
        break;
      case "sort":
        if (tableState.sortOrder.direction === "none") {
          paginateCallback(1, tableState.rowsPerPage, {});
        } else {
          sortingCallback(tableState.sortOrder);
        }
        break;
      default:
    }
  };

  const columns = [
    {
      name: "name",
      label: "Name",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "id",
      label: "ID",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "isLatest",
      label: "Is Latest",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: (dataIndex) =>
          taxonomies[dataIndex]?.isLatest ? "Yes" : "No",
      },
    },
    {
      name: "provenance",
      label: "Provenance",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "version",
      label: "Version",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
      },
    },
    {
      name: "groups",
      label: "Groups",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderGroups,
      },
    },
    {
      name: "details",
      label: "Hierarchy",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderDetails,
      },
    },
    {
      name: "manage",
      label: " ",
      options: {
        customBodyRenderLite: renderManage,
      },
    },
  ];

  const options = {
    search: false,
    selectableRows: "none",
    elevation: 1,
    onTableChange: handleTableChange,
    jumpToPage: true,
    serverSide: true,
    pagination: false,
    count: totalMatches,
    filter: true,
    sort: true,
    customToolbar: () => (
      <IconButton name="new_taxonomy" onClick={() => setFormDialogOpen(true)}>
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div>
      <MUIDataTable
        title="Taxonomies"
        data={taxonomies}
        options={options}
        columns={columns}
      />
      <Dialog
        open={formDialogOpen}
        onClose={() => {
          setFormDialogOpen(false);
          setEditTaxonomy(null);
        }}
        maxWidth="md"
      >
        <DialogTitle>{editTaxonomy ? "Edit" : "New"} Taxonomy</DialogTitle>
        <DialogContent dividers>
          <TaxonomyForm
            onClose={() => {
              setFormDialogOpen(false);
              setEditTaxonomy(null);
            }}
            taxonomyId={editTaxonomy}
          />
        </DialogContent>
      </Dialog>
      <Dialog
        open={showHierarchy !== null}
        onClose={() => setShowHierarchy(null)}
        maxWidth="lg"
      >
        <DialogTitle>Taxonomy Content</DialogTitle>
        <DialogContent dividers>
          <ReactJson
            src={showHierarchy || {}}
            name={false}
            displayDataTypes={false}
            displayObjectSize={false}
            enableClipboard={false}
            collapsed={false}
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
  taxonomies: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      version: PropTypes.string,
      provenance: PropTypes.string,
      isLatest: PropTypes.bool,
      hierarchy: PropTypes.shape({}),
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number.isRequired,
          name: PropTypes.string.isRequired,
        }),
      ),
    }),
  ).isRequired,
  paginateCallback: PropTypes.func.isRequired,
  sortingCallback: PropTypes.func,
  totalMatches: PropTypes.number,
  managePermission: PropTypes.bool.isRequired,
};

TaxonomyTable.defaultProps = {
  totalMatches: 0,
  sortingCallback: null,
};

export default TaxonomyTable;
