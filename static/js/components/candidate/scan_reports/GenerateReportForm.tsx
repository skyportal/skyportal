import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import type { RJSFSchema } from "@rjsf/utils";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../../types/hooks";
import { useGetGroupsQuery } from "../../../ducks/groups";
import { useGetGcnEventsQuery } from "../../../ducks/gcnEvents";
import { useGenerateScanReportMutation } from "../../../ducks/candidate/scan_reports";

const dateRange = (title: string, start: string, end: string): RJSFSchema => ({
  title,
  type: "object",
  properties: {
    [start]: {
      title: "After (Local Time)",
      format: "date-time",
      type: "string",
    },
    [end]: {
      title: "Before (Local Time)",
      format: "date-time",
      type: "string",
    },
  },
});

const defaultOptions = () => {
  const now = new Date();
  const oneDayAgo = new Date(now).setDate(now.getDate() - 1);
  const twelveHoursAgo = new Date(now).setHours(now.getHours() - 12);
  return {
    passed_filters_range: {
      start_date: new Date(oneDayAgo).toISOString(),
      end_date: now.toISOString(),
    },
    saved_candidates_range: {
      start_saved_date: new Date(twelveHoursAgo).toISOString(),
      end_saved_date: now.toISOString(),
    },
  };
};

interface GenerateReportFormProps {
  dialogOpen: boolean;
  setDialogOpen: (open: boolean) => void;
}

const GenerateReportForm = ({
  dialogOpen,
  setDialogOpen,
}: GenerateReportFormProps) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const gcnEvents: any[] =
    useGetGcnEventsQuery({ numPerPage: 100 }).data?.events ?? [];
  const [generateScanReport, { isLoading }] = useGenerateScanReportMutation();
  const [saveOptions, setSaveOptions] = useState(defaultOptions);

  const generateReport = async () => {
    if ((await generateScanReport(saveOptions)).error) return;
    dispatch(showNotification("Scanning report successfully generated"));
    setDialogOpen(false);
    navigate("/candidates/scan_reports");
  };

  return (
    <Dialog
      open={dialogOpen}
      onClose={() => setDialogOpen(false)}
      slotProps={{ paper: { sx: { maxWidth: 800 } } }}
    >
      <DialogTitle>Generate candidate scanning report</DialogTitle>
      <DialogContent>
        <Form
          formData={saveOptions}
          onChange={({ formData }) => setSaveOptions(formData)}
          schema={{
            type: "object",
            properties: {
              group_ids: {
                type: "array",
                items: {
                  type: "number",
                  enum: groups.map((group) => group.id),
                },
                uniqueItems: true,
                default: [],
                title: "Include sources saved to these groups",
              },
              passed_filters_range: dateRange(
                "Passed filters",
                "start_date",
                "end_date",
              ),
              gcn_event_dateobs: {
                type: ["string", "null"],
                title: "Restrict to one GCN event (optional)",
                enum: [null, ...gcnEvents.map((e) => e.dateobs)],
              },
              saved_candidates_range: dateRange(
                "Saved to groups",
                "start_saved_date",
                "end_saved_date",
              ),
            },
          }}
          uiSchema={{
            group_ids: {
              "ui:enumNames": groups.map((group) => group.name),
            },
            gcn_event_dateobs: {
              "ui:enumNames": [
                "All events",
                ...gcnEvents.map((e) =>
                  [e.dateobs, (e.tags || []).join(", ")]
                    .filter(Boolean)
                    .join("  -  "),
                ),
              ],
            },
          }}
          liveValidate
          validator={validator}
          onSubmit={generateReport}
          disabled={isLoading}
        />
      </DialogContent>
    </Dialog>
  );
};

export default GenerateReportForm;
