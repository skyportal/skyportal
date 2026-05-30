import React, { useEffect, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import SurveyEfficiencyForm from "./SurveyEfficiencyForm";
import SurveyEfficiencyObservationPlanLists from "./SurveyEfficiencyObservationPlanLists";

import { GET } from "../../API";
import Button from "../Button";
import { useAppDispatch } from "../../types/hooks";

interface AddSurveyEfficiencyObservationPlanPageProps {
  gcnevent: {
    dateobs?: string;
    localizations?: { id?: number; localization_name?: string }[];
    id?: number;
    [key: string]: any;
  };
  observationplanRequest: {
    id?: number;
    status?: string;
    [key: string]: any;
  };
}

const AddSurveyEfficiencyObservationPlanPage = ({
  gcnevent,
  observationplanRequest,
}: AddSurveyEfficiencyObservationPlanPageProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const dispatch = useAppDispatch();

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
    useState<any>(null);
  useEffect(() => {
    const fetchSurveyEfficiencyAnalysisList = async () => {
      setFetchingSurveyEfficiencyAnalysisList(true);
      dispatch(
        GET(
          `/api/observation_plan/${observationplanRequest.id}/survey_efficiency`,
          "skyportal/FETCH_OBSERVATION_PLAN_SURVEY_EFFICIENCY",
        ),
      ).then((response: any) => {
        setSurveyEfficiencyAnalysisList(response.data);
        setFetchingSurveyEfficiencyAnalysisList(false);
      });
    };
    if (
      !fetchingSurveyEfficiencyAnalysisList &&
      !surveyEfficiencyAnalysisList &&
      observationplanRequest?.status === "complete"
    ) {
      fetchSurveyEfficiencyAnalysisList();
    }
  }, [dispatch, surveyEfficiencyAnalysisList, observationplanRequest]);

  return (
    <>
      <Button
        secondary
        size="small"
        onClick={openDialog}
        data-testid={`addSimSurveyButton_${gcnevent.id}`}
      >
        SimSurvey Analysis
      </Button>
      <Dialog open={dialogOpen} onClose={closeDialog}>
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

export default AddSurveyEfficiencyObservationPlanPage;
