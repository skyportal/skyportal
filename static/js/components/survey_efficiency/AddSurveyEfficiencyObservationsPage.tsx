import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import { skipToken } from "@reduxjs/toolkit/query";

import Button from "../Button";
import SurveyEfficiencyForm from "./SurveyEfficiencyForm";
import SurveyEfficiencyObservationsLists from "./SurveyEfficiencyObservationsLists";

import {
  useGetGcnEventQuery,
  useGetGcnEventSurveyEfficiencyQuery,
} from "../../ducks/gcnEvent";

interface AddSurveyEfficiencyObservationsPageProps {
  dateobs: string;
}

const AddSurveyEfficiencyObservationsPage = ({
  dateobs,
}: AddSurveyEfficiencyObservationsPageProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: gcnEvent } = useGetGcnEventQuery(dateobs ?? skipToken);
  const { data: surveyEfficiency } = useGetGcnEventSurveyEfficiencyQuery(
    gcnEvent?.id != null ? { gcnID: gcnEvent["id"] } : skipToken,
  );

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const surveyEfficiencyAnalysisList = surveyEfficiency || [];

  return (
    <>
      <Button
        secondary
        size="small"
        onClick={openDialog}
        data-testid={`addSimSurveyButton_${gcnEvent?.id}`}
      >
        SimSurvey Analysis
      </Button>
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        fullWidth
        maxWidth={"xlg" as any}
      >
        <DialogTitle>SimSurvey Analysis</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} style={{ paddingTop: "0.1em" }}>
            <Grid size={{ xs: 12, lg: 8 }}>
              <SurveyEfficiencyObservationsLists
                survey_efficiency_analyses={surveyEfficiencyAnalysisList || []}
              />
            </Grid>
            <Grid size={{ xs: 12, lg: 4 }}>
              <Paper style={{ padding: "1em" }}>
                <SurveyEfficiencyForm gcnevent={gcnEvent as any} />
              </Paper>
            </Grid>
          </Grid>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AddSurveyEfficiencyObservationsPage;
