import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Button from "@mui/material/Button";

import SurveyEfficiencyForm from "./SurveyEfficiencyForm";
import SurveyEfficiencyObservationsLists from "./SurveyEfficiencyObservationsLists";

import { GET } from "../API";

const AddSurveyEfficiencyObservationsPage = ({ gcnevent }) => {
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
          `/api/gcn_event/${gcnevent.id}/survey_efficiency`,
          "skyportal/FETCH_GCNEVENT_SURVEY_EFFICIENCY"
        )
      );
      setSurveyEfficiencyAnalysisList(response.data);
    };
    fetchSurveyEfficiencyAnalysisList();
  }, [dispatch, setSurveyEfficiencyAnalysisList, gcnevent]);

  return (
    <>
      <Button
        variant="outlined"
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
            <SurveyEfficiencyForm gcnevent={gcnevent} />
            {surveyEfficiencyAnalysisList?.length > 0 && (
              <SurveyEfficiencyObservationsLists
                survey_efficiency_analyses={surveyEfficiencyAnalysisList}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

AddSurveyEfficiencyObservationsPage.propTypes = {
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
};

export default AddSurveyEfficiencyObservationsPage;
