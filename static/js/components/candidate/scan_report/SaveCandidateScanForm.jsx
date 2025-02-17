import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import {
  updateCandidateFromReport,
  submitCandidateToReport,
} from "../../../ducks/candidate/candidate_scan_report";

const SaveCandidateScanForm = ({
  dialogOpen,
  setDialogOpen,
  objId = null,
  candidateScanToEdit = {},
  setCandidateScanToEdit = null,
}) => {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const [saveOptions, setSaveOptions] = useState({
    comment: candidateScanToEdit?.comment,
    already_classified: candidateScanToEdit?.already_classified,
    forced_photometry_requested:
      candidateScanToEdit?.forced_photometry_requested,
    photometry_followup: candidateScanToEdit?.photometry_followup,
    photometry_assigned_to: candidateScanToEdit?.photometry_assigned_to,
    is_real: candidateScanToEdit?.is_real,
    spectroscopy_requested: candidateScanToEdit?.spectroscopy_requested,
    spectroscopy_assigned_to: candidateScanToEdit?.spectroscopy_assigned_to,
    priority: candidateScanToEdit?.priority,
  });

  const saveCandidateScanOptionsSchema = () => {
    return {
      type: "object",
      properties: {
        comment: { type: ["string", "null"], title: "comment" },
        already_classified: {
          type: ["boolean", "null"],
          title: "Already classified?",
        },
        forced_photometry_requested: {
          type: ["boolean", "null"],
          title: "Forced photometry requested?",
        },
        photometry_followup: {
          type: ["boolean", "null"],
          title: "Photometry follow-up?",
        },
        photometry_assigned_to: {
          type: ["string", "null"],
          title: "Photometry assigned to",
        },
        is_real: { type: ["boolean", "null"], title: "Sure if real?" },
        spectroscopy_requested: {
          type: ["boolean", "null"],
          title: "Spectroscopy requested?",
        },
        spectroscopy_assigned_to: {
          type: ["string", "null"],
          title: "Spectroscopy assigned to",
        },
        priority: { type: ["integer", "null"], title: "priority" },
      },
    };
  };

  const saveToReport = () => {
    setLoading(true);
    const action = candidateScanToEdit?.id
      ? updateCandidateFromReport(candidateScanToEdit.id, { ...saveOptions })
      : submitCandidateToReport({ obj_id: objId, ...saveOptions });
    dispatch(action).then((result) => {
      setLoading(false);
      if (result.status === "success") {
        dispatch(
          showNotification(
            candidateScanToEdit
              ? "Candidate scan successfully updated"
              : "Candidate scan successfully saved to the report",
          ),
        );
        setDialogOpen(false);
        setSaveOptions({});
      } else {
        dispatch(
          showNotification("Failed to save candidate scan report", "error"),
        );
      }
    });
  };

  return (
    <div>
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          setSaveOptions({});
          if (setCandidateScanToEdit) setCandidateScanToEdit(null);
        }}
        PaperProps={{ style: { maxWidth: "800px" } }}
      >
        <DialogTitle>Save candidate scan to report</DialogTitle>
        <DialogContent>
          <Form
            formData={saveOptions}
            onChange={({ formData }) => setSaveOptions(formData)}
            schema={saveCandidateScanOptionsSchema()}
            liveValidate
            validator={validator}
            onSubmit={saveToReport}
            disabled={loading}
            uiSchema={{
              comment: {
                "ui:widget": "textarea",
                "ui:options": { rows: 3 },
              },
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

SaveCandidateScanForm.propTypes = {
  dialogOpen: PropTypes.bool.isRequired,
  setDialogOpen: PropTypes.func.isRequired,
  objId: PropTypes.string,
  candidateScanToEdit: PropTypes.shape({
    comment: PropTypes.string,
    already_classified: PropTypes.bool,
    forced_photometry_requested: PropTypes.bool,
    photometry_followup: PropTypes.bool,
    photometry_assigned_to: PropTypes.string,
    is_real: PropTypes.bool,
    spectroscopy_requested: PropTypes.bool,
    spectroscopy_assigned_to: PropTypes.string,
    priority: PropTypes.number,
  }),
  setCandidateScanToEdit: PropTypes.func,
};

export default SaveCandidateScanForm;
