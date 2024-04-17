import React, { useState } from "react";
import { JSONTree } from "react-json-tree";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";

import MUIDataTable from "mui-datatables";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";
import * as taxonomyActions from "../ducks/taxonomies";

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

  const [dialogOpen, setDialogOpen] = useState(false);
  const [taxonomyToDelete, setTaxonomyToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setTaxonomyToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setTaxonomyToDelete(null);
  };

  const deleteTaxonomy = () => {
    dispatch(taxonomyActions.deleteTaxonomy(taxonomyToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Taxonomy deleted"));
          closeDialog();
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

  const renderHierarchy = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];

    const cellStyle = {
      whiteSpace: "nowrap",
    };

    return (
      <div style={cellStyle}>
        {taxonomy ? <JSONTree data={taxonomy.hierarchy} /> : ""}
      </div>
    );
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

  const renderDelete = (dataIndex) => {
    const taxonomy = taxonomies[dataIndex];
    return (
      <div>
        <Button
          key={taxonomy.id}
          id="delete_button"
          classes={{
            root: classes.taxonomyDelete,
            disabled: classes.taxonomyDeleteDisabled,
          }}
          onClick={() => openDialog(taxonomy.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
        <ConfirmDeletionDialog
          deleteFunction={deleteTaxonomy}
          dialogOpen={dialogOpen}
          closeDialog={closeDialog}
          resourceName="taxonomy"
        />
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
      name: "hierarchy",
      label: "Hierarchy",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderHierarchy,
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
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderGroups,
      },
    },
    {
      name: "delete",
      label: " ",
      options: {
        customBodyRenderLite: renderDelete,
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
  };

  return (
    <div>
      {taxonomies ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title={!hideTitle ? "" : ""}
                data={taxonomies}
                options={options}
                columns={columns}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </Paper>
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

TaxonomyTable.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
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
