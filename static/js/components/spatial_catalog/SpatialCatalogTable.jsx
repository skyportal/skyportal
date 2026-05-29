import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import SourceTableFilterForm from "../source/SourceTableFilterForm";

import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import { filterOutEmptyValues } from "../../API";
import * as sourcesActions from "../../ducks/sources";

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
  },
}));

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
      <Dialog open={dialogOpen} onClose={closeDialog}>
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

const SpatialCatalogTable = ({ catalog, setSelectedSpatialCatalogEntryId }) => {
  const { classes } = useStyles();

  if (!catalog || catalog.entries.length === 0) {
    return <p>No entries available...</p>;
  }

  const renderData = (params) => {
    const entry = params.row;
    return <div>{JSON.stringify(entry.data)}</div>;
  };

  const renderRetrieveSources = (params) => {
    const entry = params.row;

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
      field: "entry_name",
      headerName: "Entry Name",
      flex: 1,
      minWidth: 160,
    },
    {
      field: "data",
      headerName: "Entry data",
      flex: 2,
      minWidth: 240,
      renderCell: renderData,
    },
    {
      field: "retrieve_sources",
      headerName: "Retrieve Sources",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: renderRetrieveSources,
    },
  ];

  return (
    <div>
      {catalog.entries ? (
        <Paper className={classes.container}>
          <Typography variant="h6">Catalog Entries</Typography>
          <StyledDataGrid
            autoHeight
            rows={catalog.entries}
            columns={columns}
            getRowId={(row) => row.id}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
            }}
            pageSizeOptions={[2, 10, 25, 50, 100]}
            showToolbar
          />
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
};

SpatialCatalogTable.defaultProps = {
  catalog: null,
};

export default SpatialCatalogTable;
