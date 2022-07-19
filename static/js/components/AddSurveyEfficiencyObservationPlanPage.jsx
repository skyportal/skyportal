import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Button from "@mui/material/Button";

import SurveyEfficiencyForm from "./SurveyEfficiencyForm";
import SurveyEfficiencyObservationPlanLists from "./SurveyEfficiencyObservationPlanLists";

import { GET } from "../API";

const AddSurveyEfficiencyObservationPlanPage = ({
  gcnevent,
  observationplanRequest,
}) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const dispatch = useDispatch();

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
      const response = await dispatch(
        GET(
          `/api/observation_plan/${observationplanRequest.id}/survey_efficiency`,
          "skyportal/FETCH_OBSERVATION_PLAN_SURVEY_EFFICIENCY"
        )
      );
      setSurveyEfficiencyAnalysisList(response.data);
    };
    fetchSurveyEfficiencyAnalysisList();
  }, [dispatch, setSurveyEfficiencyAnalysisList, observationplanRequest]);

  return (
    <>
      <Button
        variant="contained"
        size="small"
        onClick={openDialog}
        data-testid={`addSimSurveyButton_${gcnevent.id}`}
      >
        SimSurvey Analysis
      </Button>
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        style={{ position: "fixed" }}
      >
        <DialogTitle>SimSurvey Analysis</DialogTitle>
        <DialogContent>
          <div>
            <SurveyEfficiencyForm
              gcnevent={gcnevent}
              observationplanRequest={observationplanRequest}
            />
            {surveyEfficiencyAnalysisList?.length > 0 && (
              <SurveyEfficiencyObservationPlanLists
                survey_efficiency_analyses={surveyEfficiencyAnalysisList}
              />
            )}
          </div>
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
      })
    ),
    id: PropTypes.number,
  }).isRequired,
  observationplanRequest: PropTypes.shape({
    id: PropTypes.number,
  }).isRequired,
};

export default AddSurveyEfficiencyObservationPlanPage;
