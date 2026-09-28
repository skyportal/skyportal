import { useState } from "react";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Box from "@mui/material/Box";
import InfoIcon from "@mui/icons-material/Info";
import FilterListIcon from "@mui/icons-material/FilterList";

import StyledDataGrid, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT,
} from "../StyledDataGrid";
import GalaxyTableFilterForm from "./GalaxyTableFilterForm";
import { filterOutEmptyValues } from "../../API";

const GalaxyTableToolbar = ({
  title,
  onFilterClick,
}: {
  title: string;
  onFilterClick: () => void;
}) => (
  <DataGridToolbar title={title} quickFilterTestId="galaxy-search-input">
    <Tooltip title="Filter Table">
      <IconButton
        size="small"
        data-testid="Filter Table-iconButton"
        onClick={onFilterClick}
      >
        <FilterListIcon />
      </IconButton>
    </Tooltip>
  </DataGridToolbar>
);

interface GalaxyTableProps {
  galaxies?: any[] | null;
  totalMatches?: number;
  handleTableChange?: ((...a: any[]) => void) | false;
  onFilterSubmit?: ((params: any) => void) | undefined;
  pageNumber?: number;
  numPerPage?: number;
  serverSide?: boolean;
  fixedHeader?: boolean;
  title?: string;
}

const GalaxyTable = ({
  galaxies = null,
  totalMatches = 0,
  handleTableChange = false,
  onFilterSubmit = undefined,
  pageNumber = 1,
  numPerPage = 25,
  serverSide = true,
  fixedHeader = false,
  title = "Galaxies",
}: GalaxyTableProps) => {
  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [sortModel, setSortModel] = useState<any[]>([]);
  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);

  const handleFilterSubmit = async (formData: any) => {
    if (
      formData?.position &&
      !formData?.position?.ra &&
      !formData?.position?.dec &&
      !formData?.position?.radius
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

    onFilterSubmit?.(data);
    setFilterFormSubmitted(true);
  };

  if (!galaxies) {
    return <p>No galaxies available...</p>;
  }

  const emitTableChange = (action: any, model: any) => {
    if (typeof handleTableChange !== "function") {
      return;
    }
    handleTableChange(action, {
      page: model.page,
      rowsPerPage: model.pageSize,
    });
  };

  const handlePaginationModelChange = (model: any) => {
    setRowsPerPage(model.pageSize);
    emitTableChange("changePage", model);
  };

  const handleSortModelChange = (model: any) => {
    setSortModel(model);
  };

  const renderRA = (params: any) => params.row.ra.toFixed(6);
  const renderDec = (params: any) => params.row.dec.toFixed(6);
  const renderDistance = (params: any) =>
    params.row.distmpc ? params.row.distmpc.toFixed(2) : "";
  const renderDistanceUncertainty = (params: any) =>
    params.row.distmpc_unc ? params.row.distmpc_unc.toFixed(6) : "";
  const renderMstar = (params: any) =>
    params.row.mstar ? Math.log10(params.row.mstar).toFixed(2) : "";
  const renderRedshift = (params: any) =>
    params.row.redshift ? params.row.redshift.toFixed(6) : "";
  const renderRedshiftUncertainty = (params: any) =>
    params.row.redshift_error ? params.row.redshift_error.toFixed(6) : "";
  const renderSFRFUV = (params: any) =>
    params.row.sfr_fuv ? params.row.sfr_fuv.toFixed(6) : "";
  const renderSFRW4 = (params: any) =>
    params.row.sfr_w4 ? params.row.sfr_w4.toFixed(6) : "";
  const renderMagB = (params: any) =>
    params.row.magb ? params.row.magb.toFixed(2) : "";
  const renderMagK = (params: any) =>
    params.row.magk ? params.row.magk.toFixed(2) : "";
  const renderMagFUV = (params: any) =>
    params.row.mag_fuv ? params.row.mag_fuv.toFixed(2) : "";
  const renderMagNUV = (params: any) =>
    params.row.mag_nuv ? params.row.mag_nuv.toFixed(2) : "";

  const columns: any[] = [
    {
      field: "name",
      headerName: "Galaxy Name",
      flex: 1,
      minWidth: 140,
    },
    {
      field: "alt_name",
      headerName: "Alternative Galaxy Name",
      flex: 1,
      minWidth: 180,
    },
    {
      field: "ra",
      headerName: "Right Ascension",
      flex: 1,
      minWidth: 130,
      filterable: false,
      renderCell: renderRA,
    },
    {
      field: "dec",
      headerName: "Declination",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: renderDec,
    },
    {
      field: "distmpc",
      headerName: "Distance [mpc]",
      flex: 1,
      minWidth: 130,
      filterable: false,
      renderCell: renderDistance,
    },
    {
      field: "distmpc_unc",
      headerName: "Distance uncertainty [mpc]",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: renderDistanceUncertainty,
    },
    {
      field: "redshift",
      headerName: "Redshift",
      flex: 1,
      minWidth: 110,
      filterable: false,
      renderCell: renderRedshift,
    },
    {
      field: "redshift_error",
      headerName: "Redshift error",
      flex: 1,
      minWidth: 130,
      filterable: false,
      renderCell: renderRedshiftUncertainty,
    },
    {
      field: "sfr_fuv",
      headerName: "SFR based on FUV [Msol/yr]",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: renderSFRFUV,
    },
    {
      field: "sfr_w4",
      headerName: "SFR based on W4 [Msol/yr]",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: renderSFRW4,
    },
    {
      field: "mstar",
      headerName: "log10 (Stellar mass [Msol])",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: renderMstar,
    },
    {
      field: "magb",
      headerName: "B band magnitude [mag]",
      flex: 1,
      minWidth: 170,
      filterable: false,
      renderCell: renderMagB,
    },
    {
      field: "magk",
      headerName: "K band magnitude [mag]",
      flex: 1,
      minWidth: 170,
      filterable: false,
      renderCell: renderMagK,
    },
    {
      field: "mag_fuv",
      headerName: "FUV band magnitude [mag]",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: renderMagFUV,
    },
    {
      field: "mag_nuv",
      headerName: "NUV band magnitude [mag]",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: renderMagNUV,
    },
  ];

  return (
    <Box
      sx={{
        width: "100%",
        display: "flex",
        flexDirection: "column",
        ...(fixedHeader && { height: FULL_PAGE_HEIGHT }),
      }}
    >
      <StyledDataGrid
        autoHeight={!fixedHeader}
        rows={galaxies}
        columns={columns}
        getRowId={(row: any) => row.id ?? `${row.name}_${row.ra}_${row.dec}`}
        paginationMode={serverSide ? "server" : "client"}
        sortingMode={serverSide ? "server" : "client"}
        rowCount={totalMatches}
        paginationModel={{
          page: pageNumber - 1,
          pageSize: rowsPerPage,
        }}
        onPaginationModelChange={handlePaginationModelChange}
        sortModel={sortModel}
        onSortModelChange={handleSortModelChange}
        filterMode={serverSide ? "server" : "client"}
        onFilterModelChange={(model: any) =>
          serverSide &&
          onFilterSubmit?.({
            galaxyName: model.quickFilterValues?.join(" ") || undefined,
            pageNumber: 1,
          })
        }
        slots={{ toolbar: GalaxyTableToolbar }}
        slotProps={{
          toolbar: { title, onFilterClick: () => setFilterOpen(true) },
        }}
        showToolbar
      />
      <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth>
        <DialogContent>
          {filterFormSubmitted && (
            <div>
              <InfoIcon /> &nbsp; Filters submitted to server!
            </div>
          )}
          <GalaxyTableFilterForm handleFilterSubmit={handleFilterSubmit} />
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default GalaxyTable;
