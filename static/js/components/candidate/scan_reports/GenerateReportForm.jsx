import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import { generateScanReport } from "../../../ducks/candidate/scan_reports";

const GenerateReportForm = ({ dialogOpen, setDialogOpen }) => {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);

  const now = new Date();
  const oneDayAgo = new Date(now);
  oneDayAgo.setDate(now.getDate() - 1);
  const twelveHoursAgo = new Date(now);
  twelveHoursAgo.setHours(now.getHours() - 12);
  const [saveOptions, setSaveOptions] = useState({
    candidates_detection_range: {
      start_date: oneDayAgo.toISOString(),
      end_date: now.toISOString(),
    },
    saved_candidates_range: {
      start_save_date: twelveHoursAgo.toISOString(),
      end_save_date: now.toISOString(),
    },
  });

  const generateReportSchema = () => {
    return {
      type: "object",
      properties: {
        candidates_detection_range: {
          title: "Candidates Detection Time Range",
          type: "object",
          properties: {
            start_date: {
              title: "Start (Local Time)",
              format: "date-time",
              type: "string",
            },
            end_date: {
              title: "End (Local Time)",
              format: "date-time",
              type: "string",
            },
          },
        },
        saved_candidates_range: {
          title: "Saved Candidates Time Range",
          type: "object",
          properties: {
            start_save_date: {
              title: "Start (Local Time)",
              format: "date-time",
              type: "string",
            },
            end_save_date: {
              title: "End (Local Time)",
              format: "date-time",
              type: "string",
            },
          },
        },
      },
    };
  };

  const generateReport = () => {
    setLoading(true);
    dispatch(generateScanReport(saveOptions)).then((result) => {
      setLoading(false);
      if (result.status === "success") {
        dispatch(showNotification("Scan report successfully generated"));
        setDialogOpen(false);
      } else {
        dispatch(showNotification("Failed to generate scan report", "error"));
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
        <DialogTitle sx={{ textAlign: "center", fontSize: "1.5em" }}>
          Generate candidate scan report
        </DialogTitle>
        <DialogContent>
          <Form
            formData={saveOptions}
            onChange={({ formData }) => setSaveOptions(formData)}
            schema={generateReportSchema()}
            liveValidate
            validator={validator}
            onSubmit={generateReport}
            disabled={loading}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

GenerateReportForm.propTypes = {
  dialogOpen: PropTypes.bool.isRequired,
  setDialogOpen: PropTypes.func.isRequired,
};

export default GenerateReportForm;
