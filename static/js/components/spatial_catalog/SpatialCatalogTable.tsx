import { useState } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import SourceTableFilterForm from "../source/SourceTableFilterForm";

import Button from "../Button";
import StyledDataGrid, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT,
} from "../StyledDataGrid";

import { filterOutEmptyValues } from "../../API";

interface SpatialCatalogSourcesArgs {
  catalogName: string;
  entryName: string;
  filterParams?: any;
}

interface RetrieveSpatialCatalogSourcesProps {
  catalog?: any;
  entry?: any;
  setSourcesArgs: (args: SpatialCatalogSourcesArgs) => void;
}

const RetrieveSpatialCatalogSources = ({
  entry = null,
  catalog = null,
  setSourcesArgs,
}: RetrieveSpatialCatalogSourcesProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [queryInProgress, setQueryInProgress] = useState(false);

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

    if (
      !formData.position.ra &&
      !formData.position.dec &&
      !formData.position.radius
    ) {
      delete formData.position;
    }

    const data = filterOutEmptyValues(formData) as any;
    if ("position" in data) {
      data.ra = data.position.ra;
      data.dec = data.position.dec;
      data.radius = data.position.radius;
      delete data.position;
    }

    setSourcesArgs({
      catalogName: catalog.catalog_name,
      entryName: entry.entry_name,
      filterParams: data,
    });

    setQueryInProgress(false);
  };

  return (
    <div>
      <Button
        primary
        onClick={() => {
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
  setSourcesArgs: (args: SpatialCatalogSourcesArgs) => void;
}

const SpatialCatalogTable = ({
  catalog = null,
  setSourcesArgs,
}: SpatialCatalogTableProps) => {
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
          setSourcesArgs={setSourcesArgs}
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
    <StyledDataGrid
      height={FULL_PAGE_HEIGHT}
      rows={catalog.entries}
      columns={columns}
      getRowId={(row: any) => row.id}
      slots={{ toolbar: DataGridToolbar }}
      slotProps={{ toolbar: { title: catalog.catalog_name } }}
      showToolbar
    />
  );
};

export default SpatialCatalogTable;
