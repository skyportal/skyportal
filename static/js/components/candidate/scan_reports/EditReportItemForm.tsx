import React, { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Link from "@mui/material/Link";
import Box from "@mui/material/Box";
import VisibilityIcon from "@mui/icons-material/Visibility";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../../types/hooks";
import { updateScanReportItem } from "../../../ducks/candidate/scan_report";

interface EditReportItemFormProps {
  dialogOpen: boolean;
  setDialogOpen: (...args: any[]) => void;
  reportId: number;
  itemToEdit: {
    id: number;
    obj_id: string;
    data: {
      comment?: string;
    };
  };
  setItemToEdit: (...args: any[]) => void;
}

const EditReportItemForm = ({
  dialogOpen,
  setDialogOpen,
  reportId,
  itemToEdit,
  setItemToEdit,
}: EditReportItemFormProps) => {
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(false);
  const [saveOptions, setSaveOptions] = useState<any>({
    comment: itemToEdit?.data?.comment,
  });

  const updateReportItemSchema = () => {
    return {
      type: "object",
      properties: {
        comment: { type: ["string", "null"], title: "comment" },
      },
    };
  };

  const updateReportItem = () => {
    setLoading(true);
    dispatch(
      updateScanReportItem(reportId, itemToEdit.id, { ...saveOptions }),
    ).then((result: any) => {
      setLoading(false);
      if (result.status === "success") {
        dispatch(showNotification("Report item successfully updated"));
        closeDialog();
      } else {
        dispatch(showNotification("Failed to update report item", "error"));
      }
    });
  };

  const closeDialog = () => {
    setDialogOpen(false);
    setSaveOptions({});
    setItemToEdit(null);
  };

  return (
    <div>
      <Dialog
        open={dialogOpen}
        onClose={() => closeDialog()}
        PaperProps={{ style: { maxWidth: "800px" } }}
      >
        <DialogTitle
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            columnGap: "3rem",
          }}
        >
          <Box>Edit report item</Box>
          <Link
            href={`/source/${itemToEdit.obj_id}`}
            underline="none"
            color="text.secondary"
            fontSize="1rem"
            target="_blank"
            sx={{ display: "flex", alignItems: "center", columnGap: "0.5rem" }}
          >
            {itemToEdit.obj_id}
            <VisibilityIcon fontSize="small" />
          </Link>
        </DialogTitle>
        <DialogContent>
          <Form
            formData={saveOptions}
            onChange={
              (({ formData }: { formData: any }) =>
                setSaveOptions(formData)) as any
            }
            schema={updateReportItemSchema() as any}
            liveValidate
            validator={validator}
            onSubmit={updateReportItem}
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

export default EditReportItemForm;
