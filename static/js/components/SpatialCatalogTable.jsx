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
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MUIDataTable from "mui-datatables";
import SourceTableFilterForm from "./source/SourceTableFilterForm";

import Button from "./Button";

import { filterOutEmptyValues } from "../API";
import * as sourcesActions from "../ducks/sources";

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
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
      MUIDataTablePagination: {
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
  });

const RetrieveSpatialCatalogSources = ({
  entry,
  catalog,
  setSelectedSpatialCatalogEntryId,
}) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [queryInProgress, setQueryInProgress] = useState(false);

  const dispatch = useDispatch();

  if (!entry.entry_name) {
    return <div />;
  }

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const handleFilterSubmit = async (formData) => {
    setQueryInProgress(true);
    closeDialog();

    // Remove empty position
    if (
      !formData.position.ra &&
      !formData.position.dec &&
      !formData.position.radius
    ) {
      delete formData.position;
    }

    const data = filterOutEmptyValues(formData);
    // Expand cone search params
    if ("position" in data) {
      data.ra = data.position.ra;
      data.dec = data.position.dec;
      data.radius = data.position.radius;
      delete data.position;
    }

    dispatch(
      sourcesActions.fetchSpatialCatalogSources(
        catalog.catalog_name,
        entry.entry_name,
        data,
      ),
    );

    setQueryInProgress(false);
  };

  return (
    <div>
      <Button
        primary
        onClick={() => {
          setSelectedSpatialCatalogEntryId(entry.id);
          openDialog();
        }}
        size="small"
        type="submit"
        data-testid={`retrieveSources_${entry.id}`}
      >
        Retrieve Sources
      </Button>
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Query Spatial Catalog Sources</DialogTitle>
        <DialogContent>
          <div>
            {queryInProgress ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <SourceTableFilterForm
                  handleFilterSubmit={handleFilterSubmit}
                  spatialCatalogQuery={false}
                />
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

RetrieveSpatialCatalogSources.propTypes = {
  catalog: PropTypes.shape({
    catalog_name: PropTypes.string,
    entries: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        entry_name: PropTypes.string,
        data: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      }),
    ),
  }),
  entry: PropTypes.shape({
    id: PropTypes.number,
    entry_name: PropTypes.string,
    data: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
  }),
  setSelectedSpatialCatalogEntryId: PropTypes.func.isRequired,
};

RetrieveSpatialCatalogSources.defaultProps = {
  catalog: null,
  entry: null,
};

const SpatialCatalogTable = ({
  catalog,
  totalMatches,
  setSelectedSpatialCatalogEntryId,
  pageNumber = 1,
  numPerPage = 10,
  serverSide = false,
  hideTitle = false,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!catalog || catalog.entries.length === 0) {
    return <p>No entries available...</p>;
  }

  const renderData = (dataIndex) => {
    const entry = catalog.entries[dataIndex];
    return <div>{JSON.stringify(entry.data)}</div>;
  };

  const renderRetrieveSources = (dataIndex) => {
    const entry = catalog.entries[dataIndex];

    return (
      <div>
        <RetrieveSpatialCatalogSources
          entry={entry}
          catalog={catalog}
          setSelectedSpatialCatalogEntryId={setSelectedSpatialCatalogEntryId}
        />
      </div>
    );
  };

  const columns = [
    {
      name: "entry_name",
      label: "Entry Name",
    },
    {
      name: "data",
      label: "Entry data",
      options: {
        customBodyRenderLite: renderData,
        download: false,
      },
    },
    {
      name: "retrieve_sources",
      label: "Retrieve Sources",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderRetrieveSources,
        download: false,
      },
    },
  ];

  const options = {
    search: true,
    selectableRows: "none",
    elevation: 0,
    page: pageNumber - 1,
    rowsPerPage: numPerPage,
    rowsPerPageOptions: [2, 10, 25, 50, 100],
    jumpToPage: true,
    serverSide,
    pagination: true,
    count: totalMatches,
  };

  return (
    <div>
      {catalog.entries ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title={!hideTitle ? "Catalog Entries" : ""}
                data={catalog.entries}
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

SpatialCatalogTable.propTypes = {
  catalog: PropTypes.shape({
    catalog_name: PropTypes.string,
    entries: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        entry_name: PropTypes.string,
        data: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      }),
    ),
  }),
  setSelectedSpatialCatalogEntryId: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  hideTitle: PropTypes.bool,
  serverSide: PropTypes.bool,
};

SpatialCatalogTable.defaultProps = {
  catalog: null,
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  hideTitle: false,
  serverSide: false,
};

export default SpatialCatalogTable;
