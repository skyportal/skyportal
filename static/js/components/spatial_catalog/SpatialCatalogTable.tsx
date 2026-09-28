import { useState } from "react";
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

  if (!entry?.entry_name) return null;

  const handleFilterSubmit = (formData: any) => {
    setDialogOpen(false);

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
  };

  return (
    <>
      <Button primary onClick={() => setDialogOpen(true)} size="small">
        Retrieve Sources
      </Button>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Query Spatial Catalog Sources</DialogTitle>
        <DialogContent>
          <SourceTableFilterForm
            handleFilterSubmit={handleFilterSubmit}
            spatialCatalogQuery={false}
          />
        </DialogContent>
      </Dialog>
    </>
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
      renderCell: ({ row }: any) => JSON.stringify(row.data),
    },
    {
      field: "retrieve_sources",
      headerName: "Retrieve Sources",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: ({ row }: any) => (
        <RetrieveSpatialCatalogSources
          entry={row}
          catalog={catalog}
          setSourcesArgs={setSourcesArgs}
        />
      ),
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
