import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
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
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import ModifyTaxonomy from "./ModifyTaxonomy";
import NewTaxonomy from "./NewTaxonomy";
import * as taxonomyActions from "../../ducks/taxonomies";

const useStyles = makeStyles((theme) => ({
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

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTablePagination: {
        styleOverrides: {
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
    },
  });

const TaxonomyTable = ({
  taxonomies,
  paginateCallback,
  totalMatches,
  deletePermission,
  sortingCallback,
  hideTitle = false,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  const dispatch = useDispatch();

  const [setRowsPerPage] = useState(100);

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

  const renderName = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];

    return <div>{taxonomy ? taxonomy.name : ""}</div>;
  };

  const renderID = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];

    return <div>{taxonomy ? taxonomy.id : ""}</div>;
  };

  const renderIsLatest = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];

    return <div>{taxonomy ? taxonomy.isLatest.toString() : ""}</div>;
  };

  const renderProvenance = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];

    return <div>{taxonomy ? taxonomy.provenance : ""}</div>;
  };

  const renderVersion = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];

    return <div>{taxonomy ? taxonomy.version : ""}</div>;
  };

  const renderGroups = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];

    const groupNames = [];
    taxonomy?.groups?.forEach((group) => {
      groupNames.push(group.name);
    });
    return <div>{groupNames.length > 0 ? groupNames.join("\n") : ""}</div>;
  };

  const renderDetails = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];
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

  const renderManage = (dataIndex) => {
    if (!deletePermission) {
      return null;
    }
    const taxonomy = taxonomies[dataIndex];
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
          key={`delete_${taxonomy.id}`}
          id={`delete_button_${taxonomy.id}`}
          onClick={() => openDeleteDialog(taxonomy.id)}
          disabled={!deletePermission}
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
        setRowsPerPage(tableState.rowsPerPage);
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
        customBodyRenderLite: renderName,
      },
    },
    {
      name: "id",
      label: "ID",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderID,
      },
    },
    {
      name: "isLatest",
      label: "isLatest",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderIsLatest,
      },
    },
    {
      name: "provenance",
      label: "Provenance",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderProvenance,
      },
    },
    {
      name: "version",
      label: "Version",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderVersion,
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
    elevation: 0,
    onTableChange: handleTableChange,
    jumpToPage: true,
    serverSide: true,
    pagination: false,
    count: totalMatches,
    filter: true,
    sort: true,
    customToolbar: () => (
      <IconButton
        name="new_taxonomy"
        onClick={() => {
          openNewDialog();
        }}
      >
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div>
      <Paper className={classes.container}>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              title={hideTitle === true ? "" : "Taxonomies"}
              data={taxonomies}
              options={options}
              columns={columns}
            />
          </ThemeProvider>
        </StyledEngineProvider>
      </Paper>
      <Dialog
        open={newDialogOpen}
        onClose={closeNewDialog}
        style={{ position: "fixed" }}
        maxWidth="md"
      >
        <DialogTitle>New Taxonomy</DialogTitle>
        <DialogContent dividers>
          <NewTaxonomy onClose={closeNewDialog} />
        </DialogContent>
      </Dialog>
      <Dialog
        open={detailsDialogOpen && taxonomyToViewEditDelete}
        onClose={closeDetailsDialog}
        style={{ position: "fixed" }}
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
        style={{ position: "fixed" }}
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
  hideTitle: PropTypes.bool,
  deletePermission: PropTypes.bool.isRequired,
};

TaxonomyTable.defaultProps = {
  totalMatches: 0,
  sortingCallback: null,
  hideTitle: false,
};

export default TaxonomyTable;
