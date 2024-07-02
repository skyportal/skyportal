import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import * as Actions from "../../ducks/gcnEvent";
import GroupShareSelect from "../group/GroupShareSelect";
import Button from "../Button";

const AddRunFromObservationPlanPage = ({ observationplanRequest }) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const dispatch = useDispatch();

  const allGroups = useSelector((state) => state.groups.all);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const [isCreatingObservingRun, setIsCreatingObservingRun] = useState(null);
  const handleCreateObservingRun = async (id, groupIds) => {
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
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Create Observing Run</DialogTitle>
        <DialogContent>
          <div>
            {isCreatingObservingRun === observationplanRequest.id ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <GroupShareSelect
                  groupList={allGroups}
                  setGroupIDs={setSelectedGroupIds}
                  groupIDs={selectedGroupIds}
                />

                <Button
                  secondary
                  onClick={() => {
                    handleCreateObservingRun(
                      observationplanRequest.id,
                      selectedGroupIds,
                    );
                  }}
                  size="small"
                  type="submit"
                  data-testid={`observingRunRequest_${observationplanRequest.id}`}
                >
                  Create Observing Run
                </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

AddRunFromObservationPlanPage.propTypes = {
  observationplanRequest: PropTypes.shape({
    id: PropTypes.number,
  }).isRequired,
};

export default AddRunFromObservationPlanPage;
