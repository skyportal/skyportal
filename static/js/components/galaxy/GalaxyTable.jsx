import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import InfoIcon from "@mui/icons-material/Info";
import FilterListIcon from "@mui/icons-material/FilterList";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";

import StyledDataGrid from "../StyledDataGrid";
import GalaxyTableFilterForm from "./GalaxyTableFilterForm";
import { filterOutEmptyValues } from "../../API";

import * as galaxiesActions from "../../ducks/galaxies";

const PAGE_SIZE_OPTIONS = [2, 10, 25, 50, 100];

const GalaxyTable = ({
  galaxies,
  totalMatches,
  handleTableChange = false,
  pageNumber = 1,
  numPerPage = 10,
  serverSide = true,
}) => {
  const dispatch = useDispatch();

  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [sortModel, setSortModel] = useState([]);
  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);

  if (!galaxies) {
    return <p>No galaxies available...</p>;
  }

  const handleFilterSubmit = async (formData) => {
    // Remove empty position
    if (
      formData?.position &&
      !formData?.position?.ra &&
      !formData?.position?.dec &&
      !formData?.position?.radius
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

    await dispatch(galaxiesActions.fetchGalaxies(data));
    setFilterFormSubmitted(true);
  };

  const handleSearchChange = (value) => {
    const params = {
      pageNumber: 1,
    };
    if (value?.length > 0) {
      params.galaxyName = value;
    }
    handleFilterSubmit(params);
  };

  // Synthesize the mui-datatables onTableChange(action, tableState) contract
  // from the DataGrid handlers so callers (GalaxyPage) stay unchanged.
  const emitTableChange = (action, model) => {
    if (typeof handleTableChange !== "function") {
      return;
    }
    handleTableChange(action, {
      page: model.page,
      rowsPerPage: model.pageSize,
    });
  };

  const handlePaginationModelChange = (model) => {
    setRowsPerPage(model.pageSize);
    emitTableChange("changePage", model);
  };

  const handleSortModelChange = (model) => {
    setSortModel(model);
  };

  const renderRA = (params) => params.row.ra.toFixed(6);
  const renderDec = (params) => params.row.dec.toFixed(6);
  const renderDistance = (params) =>
    params.row.distmpc ? params.row.distmpc.toFixed(2) : "";
  const renderDistanceUncertainty = (params) =>
    params.row.distmpc_unc ? params.row.distmpc_unc.toFixed(6) : "";
  const renderMstar = (params) =>
    params.row.mstar ? Math.log10(params.row.mstar).toFixed(2) : "";
  const renderRedshift = (params) =>
    params.row.redshift ? params.row.redshift.toFixed(6) : "";
  const renderRedshiftUncertainty = (params) =>
    params.row.redshift_error ? params.row.redshift_error.toFixed(6) : "";
  const renderSFRFUV = (params) =>
    params.row.sfr_fuv ? params.row.sfr_fuv.toFixed(6) : "";
  const renderSFRW4 = (params) =>
    params.row.sfr_w4 ? params.row.sfr_w4.toFixed(6) : "";
  const renderMagB = (params) =>
    params.row.magb ? params.row.magb.toFixed(2) : "";
  const renderMagK = (params) =>
    params.row.magk ? params.row.magk.toFixed(2) : "";
  const renderMagFUV = (params) =>
    params.row.mag_fuv ? params.row.mag_fuv.toFixed(2) : "";
  const renderMagNUV = (params) =>
    params.row.mag_nuv ? params.row.mag_nuv.toFixed(2) : "";

  const columns = [
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

  const CustomToolbar = () => (
    <GridToolbarContainer>
      <GridToolbarColumnsButton />
      <Tooltip title="Filter Table">
        <IconButton
          size="small"
          data-testid="Filter Table-iconButton"
          onClick={() => setFilterOpen(true)}
        >
          <FilterListIcon />
        </IconButton>
      </Tooltip>
      <TextField
        size="small"
        variant="standard"
        placeholder="Search Galaxy Name…"
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            handleSearchChange(searchText);
          }
        }}
      />
    </GridToolbarContainer>
  );

  return (
    <div>
      {galaxies ? (
        <Box sx={{ width: "100%" }}>
          <Typography variant="h6" style={{ padding: "0.5rem" }}>
            Galaxies
          </Typography>
          <StyledDataGrid
            autoHeight
            title="Galaxies"
            rows={galaxies}
            columns={columns}
            getRowId={(row) => row.id ?? `${row.name}_${row.ra}_${row.dec}`}
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
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
          <Dialog
            open={filterOpen}
            onClose={() => setFilterOpen(false)}
            fullWidth
          >
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
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

GalaxyTable.propTypes = {
  galaxies: PropTypes.arrayOf(
    PropTypes.shape({
      catalog_name: PropTypes.string,
      name: PropTypes.string,
      alt_name: PropTypes.string,
      ra: PropTypes.number,
      dec: PropTypes.number,
      distmpc: PropTypes.number,
      distmpc_unc: PropTypes.number,
      redshift: PropTypes.number,
      redshift_error: PropTypes.number,
      sfr_fuv: PropTypes.number,
      sfr_w4: PropTypes.number,
      mstar: PropTypes.number,
      magb: PropTypes.number,
      magk: PropTypes.number,
      mag_fuv: PropTypes.number,
      mag_nuv: PropTypes.number,
      a: PropTypes.number,
      b2a: PropTypes.number,
      pa: PropTypes.number,
      btc: PropTypes.number,
    }),
  ),
  handleTableChange: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  serverSide: PropTypes.bool,
};

GalaxyTable.defaultProps = {
  galaxies: null,
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  serverSide: true,
};

export default GalaxyTable;
