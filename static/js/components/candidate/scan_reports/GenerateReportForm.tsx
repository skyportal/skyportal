import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../../types/hooks";
import { generateScanReport } from "../../../ducks/candidate/scan_reports";

interface GenerateReportFormProps {
  dialogOpen: boolean;
  setDialogOpen: (...args: any[]) => void;
}

const GenerateReportForm = ({
  dialogOpen,
  setDialogOpen,
}: GenerateReportFormProps) => {
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(false);
  const groups = useAppSelector((state) => state.groups.userAccessible);

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
    dispatch(generateScanReport(saveOptions)).then((result: any) => {
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
            onChange={
              (({ formData }: { formData: any }) =>
                setSaveOptions(formData)) as any
            }
            schema={generateReportSchema() as any}
            uiSchema={{
              group_ids: {
                "ui:enumNames": (groups || []).map((group: any) => group.name),
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
