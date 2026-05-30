import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { makeStyles } from "tss-react/mui";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import * as surveyEfficiencyObservationPlansActions from "../../ducks/survey_efficiency_observation_plans";

const useStyles = makeStyles()(() => ({
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

const SurveyEfficiencyObservationPlanLists = ({
  survey_efficiency_analyses,
}) => {
  const { classes } = useStyles();
  const dispatch = useDispatch();
  const [isDeleting, setIsDeleting] = useState(null);

  if (!survey_efficiency_analyses || survey_efficiency_analyses.length === 0) {
    return <p>No survey efficiency analyses for this observation plan...</p>;
  }

  const handleDelete = async (id) => {
    setIsDeleting(id);
    const result = await dispatch(
      surveyEfficiencyObservationPlansActions.deleteSurveyEfficiencyObservationPlan(
        id,
      ),
    );
    setIsDeleting(null);
    if (result.status === "success") {
      dispatch(showNotification("Survey efficiency successfully deleted."));
    }
  };

  const columns = [
    { field: "status", headerName: "Status", flex: 1, minWidth: 120 },
    {
      field: "payload",
      headerName: "Payload",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: (params) => <div>{JSON.stringify(params.row.payload)}</div>,
    },
    {
      field: "ntransients",
      headerName: "Number of Transients",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: (params) => (
        <div>
          {params.row.number_of_transients ? (
            <div>{params.row.number_of_transients}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      ),
    },
    {
      field: "ncovered",
      headerName: "Number in Covered Region",
      flex: 1,
      minWidth: 180,
      sortable: false,
      renderCell: (params) => (
        <div>
          {params.row.number_in_covered ? (
            <div>{params.row.number_in_covered}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      ),
    },
    {
      field: "ndetected",
      headerName: "Number Detected",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params) => (
        <div>
          {params.row.number_detected ? (
            <div>{params.row.number_detected}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      ),
    },
    {
      field: "efficiency",
      headerName: "Efficiency",
      flex: 1,
      minWidth: 110,
      sortable: false,
      renderCell: (params) => (
        <div>
          {params.row.efficiency ? (
            <div>{params.row.efficiency.toFixed(3)}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      ),
    },
    {
      field: "plot",
      headerName: " ",
      width: 140,
      sortable: false,
      renderCell: (params) => (
        <div>
          <Button
            primary
            href={`/api/observation_plan/${params.row.id}/simsurvey/plot`}
            size="small"
            type="submit"
            data-testid={`simsurvey_${params.row.id}`}
          >
            Download Plot
          </Button>
        </div>
      ),
    },
    {
      field: "delete",
      headerName: " ",
      width: 100,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const analysis = params.row;
        return (
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
        );
      },
    },
  ];

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
          <StyledDataGrid
            autoHeight
            rows={survey_efficiency_analyses}
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
  );
};

SurveyEfficiencyObservationPlanLists.propTypes = {
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

export default SurveyEfficiencyObservationPlanLists;
