import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import SurveyEfficiencyForm from "./SurveyEfficiencyForm";
import SurveyEfficiencyObservationPlanLists from "./SurveyEfficiencyObservationPlanLists";

import { GET } from "../../API";
import Button from "../Button";

const AddSurveyEfficiencyObservationPlanPage = ({
  gcnevent,
  observationPlanRequest,
}) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const dispatch = useDispatch();

  const [
    fetchingSurveyEfficiencyAnalysisList,
    setFetchingSurveyEfficiencyAnalysisList,
  ] = useState(false);

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const [surveyEfficiencyAnalysisList, setSurveyEfficiencyAnalysisList] =
    useState(null);
  useEffect(() => {
    const fetchSurveyEfficiencyAnalysisList = async () => {
      setFetchingSurveyEfficiencyAnalysisList(true);
      dispatch(
        GET(
          `/api/observation_plan/${observationPlanRequest.id}/survey_efficiency`,
          "skyportal/FETCH_OBSERVATION_PLAN_SURVEY_EFFICIENCY",
        ),
      ).then((response) => {
        setSurveyEfficiencyAnalysisList(response.data);
        setFetchingSurveyEfficiencyAnalysisList(false);
      });
    };
    if (
      !fetchingSurveyEfficiencyAnalysisList &&
      !surveyEfficiencyAnalysisList &&
      observationPlanRequest?.status === "complete"
    ) {
      fetchSurveyEfficiencyAnalysisList();
    }
  }, [dispatch, surveyEfficiencyAnalysisList, observationPlanRequest]);

  return (
    <>
      <Button
        secondary
        size="small"
        onClick={openDialog}
        data-testid={`addSimSurveyButton_${gcnevent.id}`}
        disabled={!observationPlanRequest.observation_plans?.length}
      >
        SimSurvey Analysis
      </Button>
      <Dialog open={dialogOpen} onClose={closeDialog}>
        <DialogTitle>SimSurvey Analysis</DialogTitle>
        <DialogContent>
          <SurveyEfficiencyForm
            gcnevent={gcnevent}
            observationplanRequest={observationPlanRequest}
          />
          {surveyEfficiencyAnalysisList?.length > 0 && (
            <SurveyEfficiencyObservationPlanLists
              survey_efficiency_analyses={surveyEfficiencyAnalysisList}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

AddSurveyEfficiencyObservationPlanPage.propTypes = {
  gcnevent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      }),
    ),
    id: PropTypes.number,
  }).isRequired,
  observationPlanRequest: PropTypes.shape({
    id: PropTypes.number,
    status: PropTypes.string,
    observation_plans: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
    ),
  }).isRequired,
};

export default AddSurveyEfficiencyObservationPlanPage;
