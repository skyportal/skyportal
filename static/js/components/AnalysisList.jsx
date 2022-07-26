import React, { useState, useEffect } from "react";
import { useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import PropTypes from "prop-types";
import Button from "@mui/material/Button";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import { showNotification } from "baselayer/components/Notifications";
import dayjs from "dayjs";

import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
  adaptV4Theme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";

import * as sourceActions from "../ducks/source";

dayjs.extend(relativeTime);
dayjs.extend(utc);

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
  chip: {
    margin: "0.1em",
  },
  infoButton: {
    paddingRight: "0.5rem",
  },
  tooltipContent: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    width: "100%",
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

const AnalysisList = ({ obj_id }) => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();

  const [analysesList, setAnalysesList] = useState(null);
  useEffect(() => {
    const fetchAnalysesList = async (objID) => {
      const response = await dispatch(
        sourceActions.fetchAnalyses("obj", { objID })
      );
      setAnalysesList(response.data);
    };
    fetchAnalysesList(obj_id);
  }, [dispatch, setAnalysesList, obj_id]);

  if (!analysesList || analysesList.length === 0) {
    return <p>No analyses for this source...</p>;
  }

  const deleteAnalysis = async (analysisID) => {
    dispatch(showNotification(`Deleting Analysis (${analysisID}).`));
    dispatch(sourceActions.deleteAnalysis(analysisID));
    const fetchAnalysesList = async (objID) => {
      const response = await dispatch(
        sourceActions.fetchAnalyses("obj", { objID })
      );
      setAnalysesList(response.data);
    };
    fetchAnalysesList(obj_id);
  };

  const getDataTableColumns = () => {
    const columns = [];

    const renderDedicatedPage = (dataIndex) => {
      const analysis = analysesList[dataIndex];
      return (
        <div className={classes.infoButton}>
          <Tooltip title="Link to analysis page" placement="top">
            <Link to={`/source/${obj_id}/analysis/${analysis.id}`} role="link">
              <Button variant="contained" size="small">
                {analysis.id}
              </Button>
            </Link>
          </Tooltip>
        </div>
      );
    };
    columns.push({
      name: "Link",
      label: "Analysis Page",
      options: {
        customBodyRenderLite: renderDedicatedPage,
      },
    });

    const renderStatus = (dataIndex) => {
      const analysis = analysesList[dataIndex];
      let chip_color = "warning";
      if (analysis.status === "completed") {
        chip_color = "success";
      }
      if (analysis.status === "failure") {
        chip_color = "error";
      }
      const last_active_str = `${dayjs().to(
        dayjs.utc(`${analysis.last_activity}Z`)
      )}`;
      const duration_str = `${analysis.duration?.toFixed(2)} sec`;
      const tooltip_str = `${last_active_str} (${duration_str})`;
      return (
        <div>
          <Tooltip title={tooltip_str} placement="top">
            <Chip
              label={analysis?.status}
              key={`chip${analysis.id}_${analysis.status}`}
              size="small"
              className={classes.chip}
              color={chip_color}
            />
          </Tooltip>
        </div>
      );
    };
    columns.push({
      name: "status",
      label: "Status",
      options: {
        customBodyRenderLite: renderStatus,
      },
    });

    const renderService = (dataIndex) => {
      const analysis = analysesList[dataIndex];
      return (
        <div>
          <Tooltip
            title={`${analysis?.analysis_service_name}: ${analysis?.analysis_service_description}`}
          >
            <Chip
              label={analysis.analysis_service_id}
              key={`chip${analysis.id}_${analysis.analysis_service_id}`}
              size="small"
              className={classes.chip}
            />
          </Tooltip>
        </div>
      );
    };
    columns.push({
      name: "Anaylsis Service",
      label: "Anaylsis Service",
      options: {
        customBodyRenderLite: renderService,
      },
    });

    columns.push({ name: "status_message", label: "Message" });

    const renderDelete = (dataIndex) => {
      const analysis = analysesList[dataIndex];
      return (
        <Button
          size="small"
          color="primary"
          type="button"
          name={`deleteAnalysisButton${dataIndex}`}
          onClick={() => deleteAnalysis(analysis.id)}
          className="analysisDelete"
        >
          <DeleteIcon fontSize="small" />
        </Button>
      );
    };
    columns.push({
      name: "Delete",
      label: "",
      options: {
        customBodyRenderLite: renderDelete,
      },
    });

    const renderAnalysisParameters = (dataIndex) => {
      const analysis = analysesList[dataIndex];
      return <div>{JSON.stringify(analysis.analysis_parameters)}</div>;
    };
    columns.push({
      name: "parameters",
      label: "Parameters",
      options: {
        customBodyRenderLite: renderAnalysisParameters,
      },
    });

    const renderPlot = (dataIndex) => {
      const analysis = analysesList[dataIndex];
      return (
        <div>
          {analysis?.status === "completed" && (
            <Button
              href={`/api/obj/analysis/${analysis.id}/plots/0`}
              size="small"
              color="primary"
              type="submit"
              variant="outlined"
              data-testid={`analysis_plots_${analysis.id}`}
            >
              Download Plot
            </Button>
          )}
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

    const renderCornerPlot = (dataIndex) => {
      const analysis = analysesList[dataIndex];
      return (
        <div>
          {analysis?.status === "completed" && (
            <Button
              href={`/api/obj/analysis/${analysis.id}/corner`}
              size="small"
              color="primary"
              type="submit"
              variant="outlined"
              data-testid={`analysis_cornerplots_${analysis.id}`}
            >
              Download Corner Plot
            </Button>
          )}
        </div>
      );
    };
    columns.push({
      name: "cornerplot",
      label: "Corner Plot",
      options: {
        customBodyRenderLite: renderCornerPlot,
      },
    });

    const renderResults = (dataIndex) => {
      const analysis = analysesList[dataIndex];
      return (
        <div>
          {analysis?.status === "completed" && (
            <Button
              href={`/api/obj/analysis/${analysis.id}/results`}
              size="small"
              color="primary"
              type="submit"
              variant="outlined"
              data-testid={`analysis_results_${analysis.id}`}
            >
              Download Results
            </Button>
          )}
        </div>
      );
    };
    columns.push({
      name: "results",
      label: "Results",
      options: {
        customBodyRenderLite: renderResults,
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
      <Accordion className={classes.accordion} key="analysis_table_div">
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="analysis-requests"
          data-testid="analysis-header"
        >
          <Typography variant="subtitle1">Analysis Requests</Typography>
        </AccordionSummary>
        <AccordionDetails data-testid="analysisTable">
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                data={analysesList}
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

AnalysisList.propTypes = {
  obj_id: PropTypes.string.isRequired,
};

export default AnalysisList;
