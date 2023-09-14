import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import Button from "./Button";
import SurveyEfficiencyForm from "./SurveyEfficiencyForm";
import SurveyEfficiencyObservationsLists from "./SurveyEfficiencyObservationsLists";

import { fetchGcnEventSurveyEfficiency } from "../ducks/gcnEvent";

const AddSurveyEfficiencyObservationsPage = () => {
  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [fetchingSurveyEfficiency, setFetchingSurveyEfficiency] =
    useState(false);

  const gcnEvent = useSelector((state) => state.gcnEvent);

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  useEffect(() => {
    if (
      gcnEvent?.id &&
      !gcnEvent?.survey_efficiency &&
      !fetchingSurveyEfficiency
    ) {
      setFetchingSurveyEfficiency(true);
      dispatch(fetchGcnEventSurveyEfficiency({ gcnID: gcnEvent?.id })).then(
        () => {
          setFetchingSurveyEfficiency(false);
        }
      );
    }
  }, [dispatch, gcnEvent]);

  const surveyEfficiencyAnalysisList = gcnEvent?.survey_efficiency || [];

  return (
    <>
      <Button
        secondary
        size="small"
        onClick={openDialog}
        data-testid={`addSimSurveyButton_${gcnEvent.id}`}
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
            <SurveyEfficiencyForm gcnevent={gcnEvent} />
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

export default AddSurveyEfficiencyObservationsPage;
