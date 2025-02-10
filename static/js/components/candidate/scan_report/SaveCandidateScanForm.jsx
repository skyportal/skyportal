import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import * as candidateScanReportActions from "../../../ducks/candidate/candidate_scan_report";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";

const SaveCandidateScanForm = ({
  dialogOpen,
  setDialogOpen,
  candidateObjId,
  candidateScan = {},
}) => {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const [saveOptions, setSaveOptions] = useState(candidateScan);

  const saveCandidateScanOptionsSchema = () => {
    return {
      type: "object",
      properties: {
        comment: { type: "string", title: "comment" },
        already_classified: { type: "boolean", title: "Already classified?" },
        forced_photometry_requested: {
          type: "boolean",
          title: "Forced photometry requested?",
        },
        photometry_followup: {
          type: "boolean",
          title: "Photometry follow-up?",
        },
        photometry_assigned_to: {
          type: "string",
          title: "Photometry assigned to",
        },
        is_real: { type: "boolean", title: "Sure if real?" },
        spectroscopy_requested: {
          type: "boolean",
          title: "Spectroscopy requested?",
        },
        spectroscopy_assigned_to: {
          type: "string",
          title: "Spectroscopy assigned to",
        },
        priority: { type: "integer", title: "priority" },
      },
    };
  };

  const saveToReport = () => {
    setLoading(true);
    dispatch(
      candidateScanReportActions.submitCandidateToReport(candidateObjId, {
        ...saveOptions,
      }),
    ).then((result) => {
      setLoading(false);
      if (result.status === "success") {
        dispatch(
          showNotification("Candidate scan successfully saved to the report"),
        );
        setDialogOpen(false);
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
        onClose={() => setDialogOpen(false)}
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
  candidateObjId: PropTypes.string.isRequired,
  candidateScan: PropTypes.shape({
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
};

export default SaveCandidateScanForm;
