import { useEffect, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import Button from "../Button";
import SurveyEfficiencyForm from "./SurveyEfficiencyForm";
import SurveyEfficiencyObservationsLists from "./SurveyEfficiencyObservationsLists";

import { fetchGcnEventSurveyEfficiency } from "../../ducks/gcnEvent";

const AddSurveyEfficiencyObservationsPage = () => {
  const dispatch = useAppDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [fetchingSurveyEfficiency, setFetchingSurveyEfficiency] =
    useState(false);

  const gcnEvent = useAppSelector((state) => state["gcnEvent"]) as any;

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
        },
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
                <SurveyEfficiencyForm gcnevent={gcnEvent} />
              </Paper>
            </Grid>
          </Grid>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AddSurveyEfficiencyObservationsPage;
