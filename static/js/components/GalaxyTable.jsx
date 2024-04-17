import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import InfoIcon from "@mui/icons-material/Info";
import CircularProgress from "@mui/material/CircularProgress";
import MUIDataTable from "mui-datatables";

import GalaxyTableFilterForm from "./GalaxyTableFilterForm";
import { filterOutEmptyValues } from "../API";

import * as galaxiesActions from "../ducks/galaxies";

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

const GalaxyTable = ({
  galaxies,
  totalMatches,
  handleTableChange = false,
  pageNumber = 1,
  numPerPage = 10,
  serverSide = true,
  showTitle = false,
}) => {
  const theme = useTheme();
  const dispatch = useDispatch();

  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);

  if (!galaxies) {
    return <p>No galaxies available...</p>;
  }

  const renderRA = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.ra.toFixed(6);
  };

  const renderDec = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.dec.toFixed(6);
  };

  const renderDistance = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.distmpc ? galaxy.distmpc.toFixed(2) : "";
  };

  const renderDistanceUncertainty = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.distmpc_unc ? galaxy.distmpc_unc.toFixed(6) : "";
  };

  const renderMstar = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.mstar ? Math.log10(galaxy.mstar).toFixed(2) : "";
  };

  const renderRedshift = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.redshift ? galaxy.redshift.toFixed(6) : "";
  };

  const renderRedshiftUncertainty = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.redshift_error ? galaxy.redshift_error.toFixed(6) : "";
  };

  const renderSFRFUV = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.sfr_fuv ? galaxy.sfr_fuv.toFixed(6) : "";
  };

  const renderSFRW4 = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.sfr_w4 ? galaxy.sfr_w4.toFixed(6) : "";
  };

  const renderMagB = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.magb ? galaxy.magb.toFixed(2) : "";
  };

  const renderMagK = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.magk ? galaxy.magk.toFixed(2) : "";
  };

  const renderMagFUV = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.mag_fuv ? galaxy.mag_fuv.toFixed(2) : "";
  };

  const renderMagNUV = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.mag_nuv ? galaxy.mag_nuv.toFixed(2) : "";
  };

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

  const handleSearchChange = (searchText) => {
    const params = {
      pageNumber: 1,
    };
    if (searchText?.length > 0) {
      params.galaxyName = searchText;
    }
    handleFilterSubmit(params);
  };

  const handleFilterReset = () => {
    handleFilterSubmit({});
  };

  const customFilterDisplay = () => (
    <>
      {filterFormSubmitted && (
        <div>
          <InfoIcon /> &nbsp; Filters submitted to server!
        </div>
      )}
      <GalaxyTableFilterForm handleFilterSubmit={handleFilterSubmit} />
    </>
  );

  const columns = [
    {
      name: "name",
      label: "Galaxy Name",
    },
    {
      name: "alt_name",
      label: "Alternative Galaxy Name",
    },
    {
      name: "ra",
      label: "Right Ascension",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderRA,
      },
    },
    {
      name: "dec",
      label: "Declination",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderDec,
      },
    },
    {
      name: "distmpc",
      label: "Distance [mpc]",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderDistance,
      },
    },
    {
      name: "distmpc_unc",
      label: "Distance uncertainty [mpc]",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderDistanceUncertainty,
      },
    },
    {
      name: "redshift",
      label: "Redshift",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderRedshift,
      },
    },
    {
      name: "redshift_error",
      label: "Redshift error",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderRedshiftUncertainty,
      },
    },
    {
      name: "sfr_fuv",
      label: "SFR based on FUV [Msol/yr]",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderSFRFUV,
      },
    },
    {
      name: "sfr_w4",
      label: "SFR based on W4 [Msol/yr]",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderSFRW4,
      },
    },
    {
      name: "mstar",
      label: "log10 (Stellar mass [Msol])",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMstar,
      },
    },
    {
      name: "magb",
      label: "B band magnitude [mag]",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMagB,
      },
    },
    {
      name: "magk",
      label: "K band magnitude [mag]",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMagK,
      },
    },
    {
      name: "mag_fuv",
      label: "FUV band magnitude [mag]",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMagFUV,
      },
    },
    {
      name: "mag_nuv",
      label: "NUV band magnitude [mag]",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMagNUV,
      },
    },
  ];

  const options = {
    search: true,
    onSearchChange: handleSearchChange,
    selectableRows: "none",
    elevation: 0,
    page: pageNumber - 1,
    rowsPerPage: numPerPage,
    rowsPerPageOptions: [2, 10, 25, 50, 100],
    jumpToPage: true,
    serverSide,
    pagination: true,
    count: totalMatches,
    filter: true,
    onFilterChange: handleFilterReset,
    customFilterDialogFooter: customFilterDisplay,
  };
  if (typeof handleTableChange === "function") {
    options.onTableChange = handleTableChange;
  }

  return (
    <div>
      {galaxies ? (
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              title={showTitle ? "Galaxies" : ""}
              data={galaxies}
              options={options}
              columns={columns}
            />
          </ThemeProvider>
        </StyledEngineProvider>
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
  showTitle: PropTypes.bool,
  serverSide: PropTypes.bool,
};

GalaxyTable.defaultProps = {
  galaxies: null,
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  showTitle: false,
  serverSide: true,
};

export default GalaxyTable;
