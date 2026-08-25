import { useGetGroupsQuery } from "../../../ducks/groups";
import { useGetGcnEventsQuery } from "../../../ducks/gcnEvents";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../../types/hooks";
import { useGenerateScanReportMutation } from "../../../ducks/candidate/scan_reports";

interface GenerateReportFormProps {
  dialogOpen: boolean;
  setDialogOpen: (...args: any[]) => void;
}

const GenerateReportForm = ({
  dialogOpen,
  setDialogOpen,
}: GenerateReportFormProps) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  // Recent events only: a report is scoped to one event a scanner just worked.
  const gcnEvents =
    (useGetGcnEventsQuery({ numPerPage: 100 }) as any).data?.events ?? [];
  const [generateScanReport] = useGenerateScanReportMutation();

  const now = new Date();
  const oneDayAgo = new Date(now);
  oneDayAgo.setDate(now.getDate() - 1);
  const twelveHoursAgo = new Date(now);
  twelveHoursAgo.setHours(now.getHours() - 12);
  const [saveOptions, setSaveOptions] = useState<any>({
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

  const generateReportSchema = (): any => {
    return {
      type: "object",
      properties: {
        group_ids: {
          type: "array",
          items: {
            type: "number",
            enum: (groups || []).map((group: any) => group.id),
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
        gcn_event_dateobs: {
          type: ["string", "null"],
          title: "Restrict to one GCN event (optional)",
          enum: [null, ...gcnEvents.map((e: any) => e.dateobs)],
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
    generateScanReport(saveOptions)
      .unwrap()
      .then(() => {
        setLoading(false);
        dispatch(showNotification("Scanning report successfully generated"));
        setDialogOpen(false);
        navigate("/candidates/scan_reports");
      })
      .catch(() => {
        setLoading(false);
      });
  };

  return (
    <div>
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        slotProps={{
          paper: { style: { maxWidth: "800px" } },
        }}
      >
        <DialogTitle sx={{ textAlign: "center", fontSize: "1.5em" }}>
          Generate candidate scanning report
        </DialogTitle>
        <DialogContent>
          <Form
            formData={saveOptions}
            onChange={
              (({ formData }: { formData: any }) =>
                setSaveOptions(formData)) as any
            }
            schema={generateReportSchema() as any}
            uiSchema={{
              group_ids: {
                "ui:enumNames": (groups || []).map((group: any) => group.name),
              },
              gcn_event_dateobs: {
                "ui:enumNames": [
                  "All events",
                  ...gcnEvents.map((e: any) =>
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
            disabled={loading}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default GenerateReportForm;
