import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";

import * as surveyEfficiencyObservationsActions from "../ducks/survey_efficiency_observations";

const useStyles = makeStyles(() => ({
  observationplanRequestTable: {
    borderSpacing: "0.7em",
  },
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
  },
  accordion: {
    width: "99%",
  },
  container: {
    margin: "1rem 0",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
      MUIDataTable: {
        paper: {
          width: "100%",
        },
      },
      MUIDataTableBodyCell: {
        stackedCommon: {
          overflow: "hidden",
          "&:last-child": {
            paddingLeft: "0.25rem",
          },
        },
      },
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

const SurveyEfficiencyObservationsLists = ({ survey_efficiency_analyses }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const theme = useTheme();

  const { instrumentList } = useSelector((state) => state.instruments);
  const [isDeleting, setIsDeleting] = useState(null);

  if (!survey_efficiency_analyses || survey_efficiency_analyses.length === 0) {
    return <p>No survey efficiency analyses for this event...</p>;
  }

  const handleDelete = async (id) => {
    setIsDeleting(id);
    const result = await dispatch(
      surveyEfficiencyObservationsActions.deleteSurveyEfficiencyObservations(id)
    );
    setIsDeleting(null);
    if (result.status === "success") {
      dispatch(showNotification("Survey efficiency successfully deleted."));
    }
  };

  const instLookUp = instrumentList.reduce((r, a) => {
    r[a.id] = a;
    return r;
  }, {});

  const analysesGroupedByInstId = survey_efficiency_analyses.reduce((r, a) => {
    r[a.instrument_id] = [...(r[a.instrument_id] || []), a];
    return r;
  }, {});

  Object.values(analysesGroupedByInstId).forEach((value) => {
    value.sort();
  });

  const getDataTableColumns = (keys, instrument_id) => {
    const columns = [{ name: "status", label: "Status" }];

    const renderPayload = (dataIndex) => {
      const analysis = analysesGroupedByInstId[instrument_id][dataIndex];
      return <div>{JSON.stringify(analysis.payload)}</div>;
    };
    columns.push({
      name: "payload",
      label: "Payload",
      options: {
        customBodyRenderLite: renderPayload,
      },
    });

    const renderNumberTransients = (dataIndex) => {
      const analysis = analysesGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          {analysis.number_of_transients ? (
            <div>{analysis.number_of_transients}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      );
    };
    columns.push({
      name: "ntransients",
      label: "Number of Transients",
      options: {
        customBodyRenderLite: renderNumberTransients,
      },
    });

    const renderNumberCovered = (dataIndex) => {
      const analysis = analysesGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          {analysis.number_in_covered ? (
            <div>{analysis.number_in_covered}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      );
    };
    columns.push({
      name: "ncovered",
      label: "Number in Covered Region",
      options: {
        customBodyRenderLite: renderNumberCovered,
      },
    });

    const renderNumberDetected = (dataIndex) => {
      const analysis = analysesGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          {analysis.number_detected ? (
            <div>{analysis.number_detected}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      );
    };
    columns.push({
      name: "ndetected",
      label: "Number Detected",
      options: {
        customBodyRenderLite: renderNumberDetected,
      },
    });

    const renderEfficiency = (dataIndex) => {
      const analysis = analysesGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          {analysis.efficiency ? (
            <div>{analysis.efficiency.toFixed(3)}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      );
    };
    columns.push({
      name: "effficiency",
      label: "Efficiency",
      options: {
        customBodyRenderLite: renderEfficiency,
      },
    });

    const renderPlot = (dataIndex) => {
      const analysis = analysesGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          <Button
            primary
            href={`/api/observation/simsurvey/${analysis.id}/plot`}
            size="small"
            type="submit"
            data-testid={`simsurvey_${analysis.id}`}
          >
            Download Skymap
          </Button>
        </div>
      );
    };
    columns.push({
      name: "plot",
      label: "Plot",
      options: {
        customBodyRenderLite: renderPlot,
      },
    });

    const renderDelete = (dataIndex) => {
      const analysis = survey_efficiency_analyses[dataIndex];
      return (
        <div>
          <div>
            {isDeleting === analysis.id ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <Button
                  primary
                  onClick={() => {
                    handleDelete(analysis.id);
                  }}
                  size="small"
                  type="submit"
                  data-testid={`deleteRequest_${analysis.id}`}
                >
                  Delete
                </Button>
              </div>
            )}
          </div>
        </div>
      );
    };
    columns.push({
      name: "delete",
      label: "Delete",
      options: {
        customBodyRenderLite: renderDelete,
      },
    });

    return columns;
  };

  const options = {
    filter: false,
    sort: false,
    print: true,
    download: true,
    search: true,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    elevation: 0,
    rowsPerPageOptions: [1, 10, 15],
  };

  const keyOrder = (a, b) => {
    // End date comes after start date
    if (a === "end_date" && b === "start_date") {
      return 1;
    }
    if (b === "end_date" && a === "start_date") {
      return -1;
    }

    // Dates come before anything else
    if (a === "end_date" || a === "start_date") {
      return -1;
    }
    if (b === "end_date" || b === "start_date") {
      return 1;
    }

    // Regular string comparison
    if (a < b) {
      return -1;
    }
    if (a > b) {
      return 1;
    }
    // a must be equal to b
    return 0;
  };

  return (
    <div className={classes.container}>
      {Object.keys(analysesGroupedByInstId).map((instrument_id) => {
        // get the flat, unique list of all keys across all requests
        const keys = analysesGroupedByInstId[instrument_id].reduce((r, a) => {
          Object.keys(a.payload).forEach((key) => {
            if (!r.includes(key)) {
              r = [...r, key];
            }
          });
          return r;
        }, []);

        keys.sort(keyOrder);

        return (
          <Accordion
            className={classes.accordion}
            key={`instrument_${instrument_id}_table_div`}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls={`${instLookUp[instrument_id].name}-requests`}
              data-testid={`${instLookUp[instrument_id].name}-requests-header`}
            >
              <Typography variant="subtitle1">
                {instLookUp[instrument_id].name} Requests
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              data-testid={`${instLookUp[instrument_id].name}_observationplanRequestsTable`}
            >
              <StyledEngineProvider injectFirst>
                <ThemeProvider theme={getMuiTheme(theme)}>
                  <MUIDataTable
                    data={analysesGroupedByInstId[instrument_id]}
                    options={options}
                    columns={getDataTableColumns(keys, instrument_id)}
                  />
                </ThemeProvider>
              </StyledEngineProvider>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </div>
  );
};

SurveyEfficiencyObservationsLists.propTypes = {
  survey_efficiency_analyses: PropTypes.arrayOf(
    PropTypes.shape({
      instrument_id: PropTypes.number,
      id: PropTypes.number,
      payload: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      status: PropTypes.string,
      number_of_transients: PropTypes.number,
      number_in_covered: PropTypes.number,
      number_detected: PropTypes.number,
      efficiency: PropTypes.number,
    })
  ).isRequired,
};

export default SurveyEfficiencyObservationsLists;
