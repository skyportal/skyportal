import React, { useState, useEffect } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Button from "@mui/material/Button";
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

import * as sourceActions from "../ducks/source";

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

const LightcurveFitLists = ({ obj_id }) => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();

  const [analysisServiceList, setAnalysisServiceList] = useState(null);
  useEffect(() => {
    const fetchAnalysisServiceList = async (objID) => {
      const response = await dispatch(
        sourceActions.fetchAnalysisService("obj", { objID })
      );
      setAnalysisServiceList(response.data);
    };
    fetchAnalysisServiceList(obj_id);
  }, [dispatch, setAnalysisServiceList, obj_id]);

  if (!analysisServiceList || analysisServiceList.length === 0) {
    return <p>No analysis services for this source...</p>;
  }

  if (!analysisServiceList || analysisServiceList.length === 0) {
    return <p>No survey efficiency analyses for this event...</p>;
  }

  const getDataTableColumns = () => {
    const columns = [
      { name: "status", label: "Status" },
      { name: "created_at", label: "Created" },
      { name: "last_activity", label: "Last Activity" },
      { name: "duration", label: "Duration [s]" },
    ];

    const renderAnalysisParameters = (dataIndex) => {
      const analysis = analysisServiceList[dataIndex];
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
      const analysis = analysisServiceList[dataIndex];
      return (
        <div>
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
      const analysis = analysisServiceList[dataIndex];
      return (
        <div>
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
      const analysis = analysisServiceList[dataIndex];
      return (
        <div>
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
      <Accordion className={classes.accordion} key="instrument_table_div">
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
                data={analysisServiceList}
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

LightcurveFitLists.propTypes = {
  obj_id: PropTypes.number.isRequired,
};

export default LightcurveFitLists;
