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
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import { TableProgressText } from "../ProgressIndicators";
import * as surveyEfficiencyObservationsActions from "../../ducks/survey_efficiency_observations";

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
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTable: {
        styleOverrides: {
          paper: {
            width: "100%",
          },
        },
      },
      MUIDataTableBodyCell: {
        styleOverrides: {
          stackedCommon: {
            overflow: "hidden",
            "&:last-child": {
              paddingLeft: "0.25rem",
            },
          },
        },
      },
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
      surveyEfficiencyObservationsActions.deleteSurveyEfficiencyObservations(
        id,
      ),
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

  // for each analysisGroupedByInstId, we sort the analyses by their created_at date, most recent first
  Object.keys(analysesGroupedByInstId).forEach((key) => {
    analysesGroupedByInstId[key].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at),
    );
  });

  const getDataTableColumns = (keys, instrument_id) => {
    const columns = [{ name: "status", label: "Status" }];

    const renderPayload = (dataIndex) => {
      const analysis = analysesGroupedByInstId[instrument_id][dataIndex];
      return (
        <p
          style={{
            maxHeight: "120px",
            overflowWrap: "break-word",
            overflowY: "auto",
          }}
        >
          {JSON.stringify(analysis.payload || {})}
        </p>
      );
    };
    columns.push({
      name: "payload",
      label: "Payload",
      options: {
        customBodyRenderLite: renderPayload,
        setCellProps: () => ({ style: { maxWidth: "40rem" } }),
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
            Plot
          </Button>
        </div>
      );
    };
    columns.push({
      name: "plot",
      label: " ",
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
                  secondary
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
      label: " ",
      options: {
        customBodyRenderLite: renderDelete,
      },
    });

    return columns;
  };

  const options = {
    filter: false,
    sort: false,
    print: false,
    download: true,
    search: true,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    elevation: 0,
    rowsPerPageOptions: [1, 10, 15],
    customSearch: (searchText, currentRow, columns) => {
      try {
        if (searchText === "" || !searchText) {
          return true;
        }
        const search = searchText.toLowerCase();
        const payloadColumnIndex = columns.findIndex(
          (column) => column.name === "payload",
        );
        const statusColumnIndex = columns.findIndex(
          (column) => column.name === "status",
        );

        const inPayload =
          payloadColumnIndex !== -1
            ? (JSON.stringify(currentRow[payloadColumnIndex]) || "")
                .toLowerCase()
                .includes(search)
            : false;
        const inStatus =
          statusColumnIndex !== -1
            ? (currentRow[statusColumnIndex] || "")
                .toLowerCase()
                .includes(search)
            : false;

        return inPayload || inStatus;
      } catch (e) {
        return false;
      }
    },
    customToolbar: () => (
      <TableProgressText
        nbItems={
          (survey_efficiency_analyses || []).filter(
            (a) => a.status === "running",
          ).length
        }
      />
    ),
    onDownload: (buildHead) => {
      // iterate over all the payloads and get the full list of keys
      const allKeys = survey_efficiency_analyses.reduce((r, a) => {
        Object.keys(a.payload).forEach((key) => {
          if (!r.includes(key)) {
            r = [...r, key];
          }
        });
        return r;
      }, []);

      // we want to have the payload keys, then the status, then the other columns
      const columnsDownload = allKeys.map((key) => ({
        name: key,
        download: true,
      }));
      columnsDownload.push({ name: "status", download: true });
      columnsDownload.push({ name: "ntransients", download: true });
      columnsDownload.push({ name: "ncovered", download: true });
      columnsDownload.push({ name: "ndetected", download: true });
      columnsDownload.push({ name: "efficiency", download: true });
      columnsDownload.unshift({ name: "id", download: true });

      const data = survey_efficiency_analyses.map((analysis) => {
        const row = columnsDownload.map((column) => {
          const key = column.name;
          if (key === "id") {
            return analysis.id;
          }
          if (key === "status") {
            return analysis[key];
          }
          if (key === "ntransients") {
            return analysis.number_of_transients || "N/A";
          }
          if (key === "ncovered") {
            return analysis.number_in_covered || "N/A";
          }
          if (key === "ndetected") {
            return analysis.number_detected || "N/A";
          }
          if (key === "efficiency") {
            return analysis.efficiency || "N/A";
          }
          if (key === "plot") {
            return "";
          }
          if (key === "delete") {
            return "";
          }
          return typeof analysis.payload[key] === "object"
            ? JSON.stringify(analysis.payload[key])
            : analysis.payload[key];
        });
        return row;
      });

      const head = buildHead(columnsDownload);
      // we build the body ourselves, without the MUIDataTable buildBody function
      const body = data.map((row) => row.join(","));
      const result = head + body.join("\n");
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

      return false;
    },
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
    <div>
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
            defaultExpanded
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
              style={{ padding: 0 }}
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
    }),
  ).isRequired,
};

export default SurveyEfficiencyObservationsLists;
