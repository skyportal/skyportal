import React from "react";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";

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
    components: {
      MUIDataTablePagination: {
        styleOverrides: {
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
    },
  });

const ExecutedObservationsTable = ({
  observations,
  totalMatches,
  handleTableChange = false,
  pageNumber = 1,
  numPerPage = 10,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  const renderTelescope = (dataIndex) => {
    const { instrument } = observations[dataIndex];

    return <div>{instrument.telescope ? instrument.telescope.name : ""}</div>;
  };

  const renderInstrument = (dataIndex) => {
    const { instrument } = observations[dataIndex];

    return <div>{instrument ? instrument.name : ""}</div>;
  };

  const columns = [
    {
      name: "telescope_name",
      label: "Telescope",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderTelescope,
      },
    },
    {
      name: "instrument_name",
      label: "Instrument",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderInstrument,
      },
    },
    {
      name: "observation_id",
      label: " Observation ID",
    },
    {
      name: "obstime",
      label: "Observation time",
    },
    {
      name: "filt",
      label: "Filter",
    },
    {
      name: "exposure_time",
      label: "Exposure time [s]",
    },
    {
      name: "airmass",
      label: "Airmass",
    },
    {
      name: "seeing",
      label: "Seeing",
    },
    {
      name: "limmag",
      label: "Limiting magnitude",
    },
  ];

  const options = {
    search: true,
    selectableRows: "none",
    elevation: 0,
    page: pageNumber - 1,
    rowsPerPage: numPerPage,
    rowsPerPageOptions: [10, 25, 50, 100],
    jumpToPage: true,
    serverSide: true,
    pagination: true,
    count: totalMatches,
  };
  if (typeof handleTableChange === "function") {
    options.onTableChange = handleTableChange;
  }

  return (
    <div>
      {observations ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                data={observations}
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

ExecutedObservationsTable.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  observations: PropTypes.arrayOf(PropTypes.any).isRequired,
  handleTableChange: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
};

ExecutedObservationsTable.defaultProps = {
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
};

export default ExecutedObservationsTable;
