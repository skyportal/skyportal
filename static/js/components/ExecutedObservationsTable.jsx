import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { useNavigate } from "react-router-dom";
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

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import ObservationFilterForm from "./ObservationFilterForm";

import { checkSource, saveSource } from "../ducks/source";

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
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const { instrumentList } = useSelector((state) => state.instruments);

  const instrumentsLookup = {};
  if (instrumentList) {
    instrumentList.forEach((instrument) => {
      instrumentsLookup[instrument.id] = instrument;
    });
  }

  const renderTelescope = (dataIndex) => {
    const { instrument_id } = observations[dataIndex];

    const instrument = instrumentsLookup[instrument_id] || null;

    if (!instrument) {
      return <div>Loading...</div>;
    }

    return <div>{instrument?.telescope?.name || ""}</div>;
  };

  const renderInstrument = (dataIndex) => {
    const { instrument_id } = observations[dataIndex];

    const instrument = instrumentsLookup[instrument_id] || null;

    if (!instrument) {
      return <div>Loading...</div>;
    }

    return <div>{instrument?.name || ""}</div>;
  };

  const renderFieldID = (dataIndex) => {
    const { field } = observations[dataIndex];

    return <div>{field ? field?.field_id?.toFixed(0) : ""}</div>;
  };

  const renderRA = (dataIndex) => {
    const { field } = observations[dataIndex];

    return <div>{field ? field?.ra?.toFixed(5) : ""}</div>;
  };

  const renderDeclination = (dataIndex) => {
    const { field } = observations[dataIndex];

    return <div>{field ? field?.dec?.toFixed(5) : ""}</div>;
  };

  const renderSeeing = (dataIndex) => {
    const { seeing } = observations[dataIndex];

    return <div>{seeing ? seeing.toFixed(1) : ""}</div>;
  };

  const renderLimitingMagnitude = (dataIndex) => {
    const { limmag } = observations[dataIndex];

    return <div>{limmag ? limmag.toFixed(2) : ""}</div>;
  };

  const [isSaving, setIsSaving] = useState(null);
  const handleSave = async (formData) => {
    setIsSaving(formData.id);
    let data = null;
    data = await dispatch(checkSource(formData.id, formData));
    if (data.data !== "A source of that name does not exist.") {
      dispatch(showNotification(data.data, "error"));
    } else {
      const result = await dispatch(saveSource(formData));
      if (result.status === "success") {
        dispatch(showNotification("Source saved"));
        navigate(`/source/${formData.id}`);
      }
    }
    setIsSaving(null);
  };

  const customFilterDisplay = () => (
    <ObservationFilterForm handleFilterSubmit={handleFilterSubmit} />
  );

  const renderSaveSource = (dataIndex) => {
    const formData = {
      id: observations[dataIndex].target_name?.replace(/ /g, "_"),
      ra: observations[dataIndex].field.ra,
      dec: observations[dataIndex].field.dec,
    };
    if (!observations[dataIndex].target_name) {
      return <div />;
    }
    return (
      <div className={classes.actionButtons}>
        {isSaving === formData.id ? (
          <div>
            <CircularProgress />
          </div>
        ) : (
          <div>
            <Button
              primary
              onClick={() => {
                handleSave(formData);
              }}
              size="small"
              type="submit"
              data-testid={`saveObservation_${formData.id}`}
            >
              Save Source
            </Button>
          </div>
        )}
      </div>
    );
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
      name: "target_name",
      label: "Target Name",
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
      label: "Seeing [arcsec]",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderSeeing,
      },
    },
    {
      name: "limmag",
      label: "Limiting magnitude",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderLimitingMagnitude,
      },
    },
    {
      name: "save_source",
      label: "Save Source",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderSaveSource,
      },
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
        const { instrument_id } = observation;
        const instrument = instrumentsLookup[instrument_id] || null;

        if (!instrument) {
          return "";
        }
        return instrument?.telescope?.name || "";
      };
      const renderInstrumentDownload = (observation) => {
        const { instrument_id } = observation;
        const instrument = instrumentsLookup[instrument_id] || null;

        if (!instrument) {
          return "";
        }
        return instrument?.name || "";
      };
      const renderFieldIDDownload = (observation) => {
        const { field } = observation;
        return field ? field?.field_id : "";
      };
      const renderRADownload = (observation) => {
        const { field } = observation;
        return field ? field?.ra : "";
      };
      const renderDeclinationDownload = (observation) => {
        const { field } = observation;
        return field ? field?.dec : "";
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
                name: "observation_id",
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
                name: "target_name",
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
                name: "airmass",
                download: true,
              },
              {
                name: "seeing",
                download: true,
              },
              {
                name: "limmag",
                download: true,
              },
              {
                name: "save_source",
                download: false,
              },
            ]) +
            buildBody(
              data.map((x) => ({
                ...x,
                data: [
                  renderTelescopeDownload(x),
                  renderInstrumentDownload(x),
                  x.observation_id,
                  renderFieldIDDownload(x),
                  renderRADownload(x),
                  renderDeclinationDownload(x),
                  x.target_name,
                  x.obstime,
                  x.filt,
                  x.exposure_time,
                  x.airmass,
                  x.seeing,
                  x.limmag,
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
                title={!hideTitle ? "Executed Observations" : ""}
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
  handleFilterSubmit: PropTypes.func.isRequired,
  downloadCallback: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  hideTitle: PropTypes.bool,
  serverSide: PropTypes.bool,
};

ExecutedObservationsTable.defaultProps = {
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  hideTitle: false,
  serverSide: true,
};

export default ExecutedObservationsTable;
