import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";

import PropTypes from "prop-types";
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
import calendar from "dayjs/plugin/calendar";

import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { makeStyles } from "tss-react/mui";

import * as sourceActions from "../../ducks/source";

import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

dayjs.extend(relativeTime);
dayjs.extend(utc);
dayjs.extend(calendar);

const useStyles = makeStyles()(() => ({
  observationplanRequestTable: {
    borderSpacing: "0.7em",
  },
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
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
  },
  container: {
    width: "100%",
    margin: "auto",
    height: "100%",
  },
}));

const AnalysisList = ({ obj_id }) => {
  const { classes } = useStyles();
  const dispatch = useDispatch();

  const analyses = useSelector((state) => state.source.analyses);
  useEffect(() => {
    const fetchAnalysesList = async (objID) => {
      dispatch(sourceActions.fetchAnalyses("obj", { objID }));
    };
    fetchAnalysesList(obj_id);
  }, [dispatch, obj_id]);

  // filter out the results, to only show the analyses for this object
  let analysesList = [];
  if (analyses !== undefined && analyses !== null) {
    analysesList = analyses.filter((analysis) => analysis.obj_id === obj_id);
  }

  if (!analysesList || analysesList.length === 0) {
    return <p>No analyses for this source...</p>;
  }

  const deleteAnalysis = async (analysisID) => {
    dispatch(showNotification(`Deleting Analysis (${analysisID}).`));
    dispatch(sourceActions.deleteAnalysis(analysisID));
  };

  const renderDedicatedPage = (params) => {
    const analysis = params.row;
    return (
      <div className={classes.infoButton}>
        <Tooltip title="Link to analysis page" placement="top">
          <Link to={`/source/${obj_id}/analysis/${analysis.id}`} role="link">
            <Button primary size="small">
              {analysis.id}
            </Button>
          </Link>
        </Tooltip>
      </div>
    );
  };

  const renderStatus = (params) => {
    const analysis = params.row;
    let chip_color = "warning";
    if (analysis.status === "completed") {
      chip_color = "success";
    }
    if (analysis.status === "failure") {
      chip_color = "error";
    }
    const last_active_str = `${dayjs().to(
      dayjs.utc(`${analysis.last_activity}Z`),
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

  const renderLastActivity = (params) => {
    const analysis = params.row;
    const last_active_str = `${dayjs().to(
      dayjs.utc(`${analysis?.last_activity}Z`),
    )}`;
    const duration_str = `${analysis?.duration?.toFixed(2)} sec`;
    const info_str = `${last_active_str} (duration ${duration_str})`;
    return (
      <div>
        <Chip
          label={info_str}
          key={`chip${analysis.id}_${analysis.analysis_service_id}_activity`}
          size="small"
          className={classes.chip}
        />
      </div>
    );
  };

  const renderService = (params) => {
    const analysis = params.row;
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

  const renderDelete = (params) => {
    const analysis = params.row;
    const dataIndex = analysesList.findIndex((a) => a.id === analysis.id);
    return (
      <Button
        size="small"
        primary
        type="button"
        name={`deleteAnalysisButton${dataIndex}`}
        onClick={() => deleteAnalysis(analysis.id)}
        className="analysisDelete"
      >
        <DeleteIcon fontSize="small" />
      </Button>
    );
  };

  const renderAnalysisParameters = (params) => (
    <div>{JSON.stringify(params.row.analysis_parameters)}</div>
  );

  const renderPlot = (params) => {
    const analysis = params.row;
    return (
      <div>
        {analysis?.status === "completed" && (
          <Button
            href={`/api/obj/analysis/${analysis.id}/plots/0`}
            size="small"
            primary
            type="submit"
            data-testid={`analysis_plots_${analysis.id}`}
          >
            Download Plot
          </Button>
        )}
      </div>
    );
  };

  const renderCornerPlot = (params) => {
    const analysis = params.row;
    return (
      <div>
        {analysis?.status === "completed" && (
          <Button
            primary
            href={`/api/obj/analysis/${analysis.id}/corner`}
            size="small"
            type="submit"
            data-testid={`analysis_cornerplots_${analysis.id}`}
          >
            Download Corner Plot
          </Button>
        )}
      </div>
    );
  };

  const renderResults = (params) => {
    const analysis = params.row;
    return (
      <div>
        {analysis?.status === "completed" && (
          <div>
            <div>
              <Button
                primary
                href={`/api/obj/analysis/${analysis.id}/results?download=True`}
                size="small"
                type="submit"
                data-testid={`analysis_results_${analysis.id}`}
              >
                Download Results
              </Button>
            </div>
            <div>
              <Button
                primary
                href={`/api/obj/analysis/${analysis.id}/results`}
                size="small"
                type="submit"
                data-testid={`analysis_results_display_${analysis.id}`}
              >
                Display Results
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  };

  const columns = [
    {
      field: "Link",
      headerName: "Analysis Page",
      width: 120,
      sortable: false,
      renderCell: renderDedicatedPage,
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 110,
      sortable: false,
      renderCell: renderStatus,
    },
    {
      field: "Last Activity",
      headerName: "Last Activity",
      flex: 1,
      minWidth: 180,
      sortable: false,
      renderCell: renderLastActivity,
    },
    {
      field: "Analysis Service",
      headerName: "Analysis Service",
      width: 140,
      sortable: false,
      renderCell: renderService,
    },
    {
      field: "status_message",
      headerName: "Message",
      flex: 1,
      minWidth: 160,
      sortable: false,
    },
    {
      field: "Delete",
      headerName: "",
      width: 70,
      sortable: false,
      renderCell: renderDelete,
    },
    {
      field: "parameters",
      headerName: "Parameters",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: renderAnalysisParameters,
    },
    {
      field: "plot",
      headerName: "Plot",
      width: 140,
      sortable: false,
      renderCell: renderPlot,
    },
    {
      field: "cornerplot",
      headerName: "Corner Plot",
      width: 160,
      sortable: false,
      renderCell: renderCornerPlot,
    },
    {
      field: "results",
      headerName: "Results",
      width: 160,
      sortable: false,
      renderCell: renderResults,
    },
  ];

  return (
    <div style={{ height: "100%", width: "100%" }}>
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
            <StyledDataGrid
              autoHeight
              rows={analysesList || []}
              columns={columns}
              getRowId={(row) => row.id}
              initialState={{
                pagination: { paginationModel: { pageSize: 10 } },
              }}
              pageSizeOptions={[1, 10, 15]}
              showToolbar
            />
          </AccordionDetails>
        </Accordion>
      </div>
    </div>
  );
};

AnalysisList.propTypes = {
  obj_id: PropTypes.string.isRequired,
};

export default AnalysisList;
