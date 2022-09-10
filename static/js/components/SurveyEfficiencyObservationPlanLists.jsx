import React from "react";
import PropTypes from "prop-types";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
  adaptV4Theme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";
import Button from "./Button";

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
  createTheme(
    adaptV4Theme({
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
    })
  );

const SurveyEfficiencyLists = ({ survey_efficiency_analyses }) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!survey_efficiency_analyses || survey_efficiency_analyses.length === 0) {
    return <p>No survey efficiency analyses for this event...</p>;
  }

  const getDataTableColumns = () => {
    const columns = [{ name: "status", label: "Status" }];

    const renderPayload = (dataIndex) => {
      const analysis = survey_efficiency_analyses[dataIndex];
      return <div>{JSON.stringify(analysis.payload)}</div>;
    };
    columns.push({
      name: "ntransients",
      label: "Payload",
      options: {
        customBodyRenderLite: renderPayload,
      },
    });

    const renderNumberTransients = (dataIndex) => {
      const analysis = survey_efficiency_analyses[dataIndex];
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
      const analysis = survey_efficiency_analyses[dataIndex];
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
      const analysis = survey_efficiency_analyses[dataIndex];
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
      const analysis = survey_efficiency_analyses[dataIndex];
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
      const analysis = survey_efficiency_analyses[dataIndex];
      return (
        <div>
          <Button
            primary
            href={`/api/observation_plan/${analysis.id}/simsurvey/plot`}
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

  return (
    <div className={classes.container}>
      <Accordion className={classes.accordion} key="instrument_table_div">
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="survey-efficiency-requests"
          data-testid="survey-requests-header"
        >
          <Typography variant="subtitle1">Survey Analysis Requests</Typography>
        </AccordionSummary>
        <AccordionDetails data-testid="survey-requests_observationplanRequestsTable">
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                data={survey_efficiency_analyses}
                options={options}
                columns={getDataTableColumns()}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </AccordionDetails>
      </Accordion>
    </div>
  );
};

SurveyEfficiencyLists.propTypes = {
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

export default SurveyEfficiencyLists;
