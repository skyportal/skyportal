import React from "react";
import PropTypes from "prop-types";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import {
  makeStyles,
  createTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";

import MUIDataTable from "mui-datatables";

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

const GalaxyTable = ({ galaxies }) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!galaxies || galaxies.length === 0) {
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

  const renderSFR = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.sfr_fuv ? galaxy.sfr_fuv.toFixed(6) : "";
  };

  const renderMagB = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.magb ? galaxy.magb.toFixed(2) : "";
  };

  const renderMagK = (dataIndex) => {
    const galaxy = galaxies[dataIndex];
    return galaxy.magk ? galaxy.magk.toFixed(2) : "";
  };

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
        customBodyRenderLite: renderSFR,
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
  ];

  const options = {
    search: true,
    selectableRows: "none",
    elevation: 0,
  };

  return (
    <div>
      <Typography variant="h5">Galaxies</Typography>
      {galaxies ? (
        <Paper className={classes.container}>
          <MuiThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable data={galaxies} options={options} columns={columns} />
          </MuiThemeProvider>
        </Paper>
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
      mstar: PropTypes.number,
      magb: PropTypes.number,
      magk: PropTypes.number,
      a: PropTypes.number,
      b2a: PropTypes.number,
      pa: PropTypes.number,
      btc: PropTypes.number,
    })
  ),
};

GalaxyTable.defaultProps = {
  galaxies: null,
};

export default GalaxyTable;
