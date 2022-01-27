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

// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

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
    },
    {
      name: "dec",
      label: "Declination",
    },
    {
      name: "distmpc",
      label: "Distance [mpc]",
    },
    {
      name: "distmpc_unc",
      label: "Distance uncertainty [mpc]",
    },
    {
      name: "redshift",
      label: "Redshift",
    },
    {
      name: "redshift_error",
      label: "Redshift error",
    },
    {
      name: "sfr_fuv",
      label: "SFR based on FUV [Msol/yr]",
    },
    {
      name: "mstar",
      label: "Stellar mass [log(Msol)]",
    },
    {
      name: "magb",
      label: "B band magnitude [mag]",
    },
    {
      name: "magk",
      label: "K band magnitude [mag]",
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
      name: PropTypes.String,
      alt_name: PropTypes.String,
      ra: PropTypes.number,
      dec: PropTypes.number,
      distmpc: PropTypes.number,
      distmpc_unc: PropTypes.number,
      redshift: PropTypes.number,
      redshift_error: PropTypes.number,
      sfr_fuv: PropTypes.number,
      magb: PropTypes.number,
      magk: PropTypes.number,
      a: PropTypes.number,
      b2a: PropTypes.number,
      pa: PropTypes.number,
      btc: PropTypes.number,
    })
  ).isRequired,
};

export default GalaxyTable;
