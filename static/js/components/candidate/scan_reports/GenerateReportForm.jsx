import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
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
  const groups = useSelector((state) => state.groups.userAccessible);

  const now = new Date();
  const oneDayAgo = new Date(now);
  oneDayAgo.setDate(now.getDate() - 1);
  const twelveHoursAgo = new Date(now);
  twelveHoursAgo.setHours(now.getHours() - 12);
  const [saveOptions, setSaveOptions] = useState({
    passed_filters_range: {
      start_date: oneDayAgo.toISOString(),
      end_date: now.toISOString(),
    },
    saved_candidates_range: {
      start_saved_date: twelveHoursAgo.toISOString(),
      end_saved_date: now.toISOString(),
    },
    groups: [],
  });

  const generateReportSchema = () => {
    return {
      type: "object",
      properties: {
        group_ids: {
          type: "array",
          items: {
            type: "number",
            enum: (groups || []).map((group) => group.id),
          },
          uniqueItems: true,
          default: [],
          title: "Include sources saved to these groups",
        },
        passed_filters_range: {
          title: "Passed filters",
          type: "object",
          properties: {
            start_date: {
              title: "After (Local Time)",
              format: "date-time",
              type: "string",
            },
            end_date: {
              title: "Before (Local Time)",
              format: "date-time",
              type: "string",
            },
          },
        },
        saved_candidates_range: {
          title: "Saved to groups",
          type: "object",
          properties: {
            start_saved_date: {
              title: "After (Local Time)",
              format: "date-time",
              type: "string",
            },
            end_saved_date: {
              title: "Before (Local Time)",
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
        dispatch(showNotification("Scanning report successfully generated"));
        setDialogOpen(false);
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
          Generate candidate scanning report
        </DialogTitle>
        <DialogContent>
          <Form
            formData={saveOptions}
            onChange={({ formData }) => setSaveOptions(formData)}
            schema={generateReportSchema()}
            uiSchema={{
              group_ids: {
                "ui:enumNames": (groups || []).map((group) => group.name),
              },
            }}
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
