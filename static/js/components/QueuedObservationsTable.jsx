import React from "react";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";

import MUIDataTable from "mui-datatables";
import ObservationFilterForm from "./ObservationFilterForm";

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

const QueuedObservationsTable = ({
  observations,
  totalMatches,
  downloadCallback,
  handleTableChange = false,
  handleFilterSubmit = false,
  pageNumber = 1,
  numPerPage = 10,
  serverSide = true,
  hideTitle = false,
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

  const renderFieldID = (dataIndex) => {
    const { field } = observations[dataIndex];

    return <div>{field ? field.field_id.toFixed(0) : ""}</div>;
  };

  const renderRA = (dataIndex) => {
    const { field } = observations[dataIndex];

    return <div>{field ? field.ra.toFixed(5) : ""}</div>;
  };

  const renderDeclination = (dataIndex) => {
    const { field } = observations[dataIndex];

    return <div>{field ? field.dec.toFixed(5) : ""}</div>;
  };

  const customFilterDisplay = () => (
    <ObservationFilterForm handleFilterSubmit={handleFilterSubmit} />
  );

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
      name: "queue_name",
      label: "Queue name",
    },
    {
      name: "field_id",
      label: "Field ID",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderFieldID,
      },
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
        customBodyRenderLite: renderDeclination,
      },
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
      name: "validity_window_start",
      label: "Validity Window [start]",
    },
    {
      name: "validity_window_end",
      label: "Validity Window [end]",
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
    serverSide,
    pagination: true,
    count: totalMatches,
    filter: true,
    download: true,
    customFilterDialogFooter: customFilterDisplay,
    onDownload: (buildHead, buildBody) => {
      const renderTelescopeDownload = (observation) => {
        const { instrument } = observation;
        return instrument.telescope ? instrument.telescope.name : "";
      };
      const renderInstrumentDownload = (observation) => {
        const { instrument } = observation;
        return instrument ? instrument.name : "";
      };
      const renderFieldIDDownload = (observation) => {
        const { field } = observation;
        return field ? field.field_id : "";
      };
      const renderRADownload = (observation) => {
        const { field } = observation;
        return field ? field.ra : "";
      };
      const renderDeclinationDownload = (observation) => {
        const { field } = observation;
        return field ? field.dec : "";
      };
      downloadCallback().then((data) => {
        // if there is no data, cancel download
        if (data?.length > 0) {
          const result =
            buildHead([
              {
                name: "telescope_name",
                download: true,
              },
              {
                name: "instrument_name",
                download: true,
              },
              {
                name: "queue_name",
                download: true,
              },
              {
                name: "field_id",
                download: true,
              },
              {
                name: "ra",
                download: true,
              },
              {
                name: "dec",
                download: true,
              },
              {
                name: "obstime",
                download: true,
              },
              {
                name: "filt",
                download: true,
              },
              {
                name: "exposure_time",
                download: true,
              },
              {
                name: "validity_window_start",
                download: true,
              },
              {
                name: "validity_window_end",
                download: true,
              },
            ]) +
            buildBody(
              data.map((x) => ({
                ...x,
                data: [
                  renderTelescopeDownload(x),
                  renderInstrumentDownload(x),
                  x.queue_name,
                  renderFieldIDDownload(x),
                  renderRADownload(x),
                  renderDeclinationDownload(x),
                  x.obstime,
                  x.filt,
                  x.exposure_time,
                  x.validity_window_start,
                  x.validity_window_end,
                ],
              })),
            );
          const blob = new Blob([result], {
            type: "text/csv;charset=utf-8;",
          });
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.setAttribute("download", "observations.csv");
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      });
      return false;
    },
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
                title={!hideTitle ? "Queued Observations" : ""}
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

QueuedObservationsTable.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  observations: PropTypes.arrayOf(PropTypes.any).isRequired,
  handleTableChange: PropTypes.func.isRequired,
  handleFilterSubmit: PropTypes.func.isRequired,
  downloadCallback: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  hideTitle: PropTypes.bool,
  serverSide: PropTypes.bool,
};

QueuedObservationsTable.defaultProps = {
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  hideTitle: false,
  serverSide: true,
};

export default QueuedObservationsTable;
