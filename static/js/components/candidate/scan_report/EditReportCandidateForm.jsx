import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import { updateCandidateFromReport } from "../../../ducks/candidate/candidate_scan_report";

const EditReportCandidateForm = ({
  dialogOpen,
  setDialogOpen,
  reportCandidateToEdit,
  setReportCandidateToEdit,
}) => {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const [saveOptions, setSaveOptions] = useState({
    comment: reportCandidateToEdit?.comment,
    already_classified: reportCandidateToEdit?.already_classified,
    forced_photometry_requested:
      reportCandidateToEdit?.forced_photometry_requested,
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
      },
    };
  };

  const saveToReport = () => {
    setLoading(true);
    dispatch(
      updateCandidateFromReport(reportCandidateToEdit.id, { ...saveOptions }),
    ).then((result) => {
      setLoading(false);
      if (result.status === "success") {
        dispatch(showNotification("Candidate scan successfully updated"));
        closeDialog();
      } else {
        dispatch(
          showNotification("Failed to update candidate scan report", "error"),
        );
      }
    });
  };

  const closeDialog = () => {
    setDialogOpen(false);
    setSaveOptions({});
    setReportCandidateToEdit(null);
  };

  return (
    <div>
      <Dialog
        open={dialogOpen}
        onClose={() => closeDialog()}
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

EditReportCandidateForm.propTypes = {
  dialogOpen: PropTypes.bool.isRequired,
  setDialogOpen: PropTypes.func.isRequired,
  reportCandidateToEdit: PropTypes.shape({
    id: PropTypes.number.isRequired,
    comment: PropTypes.string,
    already_classified: PropTypes.bool,
    forced_photometry_requested: PropTypes.bool,
  }).isRequired,
  setReportCandidateToEdit: PropTypes.func.isRequired,
};

export default EditReportCandidateForm;
