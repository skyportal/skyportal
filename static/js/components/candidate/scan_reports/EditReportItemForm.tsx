import { useState } from "react";
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
import { useUpdateScanReportItemMutation } from "../../../ducks/candidate/scan_report";

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
  const [updateScanReportItem] = useUpdateScanReportItemMutation();
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

  const updateReportItem = async () => {
    setLoading(true);
    try {
      await updateScanReportItem({
        reportId,
        itemId: itemToEdit.id,
        payload: { ...saveOptions },
      }).unwrap();
      dispatch(showNotification("Report item successfully updated"));
      closeDialog();
    } catch {
      dispatch(showNotification("Failed to update report item", "error"));
    } finally {
      setLoading(false);
    }
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
        slotProps={{
          paper: { style: { maxWidth: "800px" } },
        }}
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
            target="_blank"
            sx={{
              color: "text.secondary",
              fontSize: "1rem",
              display: "flex",
              alignItems: "center",
              columnGap: "0.5rem",
            }}
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
