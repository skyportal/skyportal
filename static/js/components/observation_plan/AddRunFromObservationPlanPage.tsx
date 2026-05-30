import React, { useState } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Box from "@mui/material/Box";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as Actions from "../../ducks/gcnEvent";
import GroupShareSelect from "../group/GroupShareSelect";
import Button from "../Button";

interface AddRunFromObservationPlanPageProps {
  observationplanRequest: {
    id?: number;
  };
}

const AddRunFromObservationPlanPage = ({
  observationplanRequest,
}: AddRunFromObservationPlanPageProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const dispatch = useAppDispatch();

  const allGroups = useAppSelector((state) => state.groups.all);
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const [isCreatingObservingRun, setIsCreatingObservingRun] = useState<
    number | null
  >(null);
  const handleCreateObservingRun = async (id: number, groupIds: number[]) => {
    setIsCreatingObservingRun(id);
    const params = { groupIds };
    await dispatch(
      Actions.createObservationPlanRequestObservingRun(id, params),
    );
    setIsCreatingObservingRun(null);
    closeDialog();
  };

  return (
    <>
      <Button
        secondary
        size="small"
        onClick={openDialog}
        data-testid={`addObservingRunButton_${observationplanRequest.id}`}
      >
        Create Observing Run
      </Button>
      <Dialog open={dialogOpen} onClose={closeDialog}>
        <DialogTitle>Create Observing Run</DialogTitle>
        <DialogContent>
          {isCreatingObservingRun === observationplanRequest.id ? (
            <Box sx={{ textAlign: "center" }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <GroupShareSelect
                groupList={allGroups}
                setGroupIDs={setSelectedGroupIds}
                groupIDs={selectedGroupIds}
              />
              <Button
                secondary
                onClick={() => {
                  handleCreateObservingRun(
                    observationplanRequest.id as number,
                    selectedGroupIds,
                  );
                }}
                size="small"
                type="submit"
                data-testid={`observingRunRequest_${observationplanRequest.id}`}
              >
                Create Observing Run
              </Button>
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AddRunFromObservationPlanPage;
