import { useState } from "react";
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

import { useAppDispatch } from "../../types/hooks";
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

interface RetrieveSpatialCatalogSourcesProps {
  catalog?: any;
  entry?: any;
  setSelectedSpatialCatalogEntryId: (...args: any[]) => void;
}

const RetrieveSpatialCatalogSources = ({
  entry = null,
  catalog = null,
  setSelectedSpatialCatalogEntryId,
}: RetrieveSpatialCatalogSourcesProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [queryInProgress, setQueryInProgress] = useState(false);

  const dispatch = useAppDispatch();

  if (!entry?.entry_name) {
    return <div />;
  }

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const handleFilterSubmit = async (formData: any) => {
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

    const data = filterOutEmptyValues(formData) as any;
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

interface SpatialCatalogTableProps {
  catalog?: any;
  setSelectedSpatialCatalogEntryId: (...args: any[]) => void;
}

const SpatialCatalogTable = ({
  catalog = null,
  setSelectedSpatialCatalogEntryId,
}: SpatialCatalogTableProps) => {
  const { classes } = useStyles();

  if (!catalog || catalog.entries.length === 0) {
    return <p>No entries available...</p>;
  }

  const renderData = (params: any) => {
    const entry = params.row;
    return <div>{JSON.stringify(entry.data)}</div>;
  };

  const renderRetrieveSources = (params: any) => {
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

  const columns: any[] = [
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
            getRowId={(row: any) => row.id}
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

export default SpatialCatalogTable;
