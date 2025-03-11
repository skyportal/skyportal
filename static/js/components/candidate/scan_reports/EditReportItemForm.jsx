import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Link from "@mui/material/Link";
import Box from "@mui/material/Box";
import VisibilityIcon from "@mui/icons-material/Visibility";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import { updateScanReportItem } from "../../../ducks/candidate/scan_report";

const EditReportItemForm = ({
  dialogOpen,
  setDialogOpen,
  reportId,
  itemToEdit,
  setItemToEdit,
}) => {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const [saveOptions, setSaveOptions] = useState({
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
    ).then((result) => {
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
            onChange={({ formData }) => setSaveOptions(formData)}
            schema={updateReportItemSchema()}
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

EditReportItemForm.propTypes = {
  dialogOpen: PropTypes.bool.isRequired,
  setDialogOpen: PropTypes.func.isRequired,
  reportId: PropTypes.number.isRequired,
  itemToEdit: PropTypes.shape({
    id: PropTypes.number.isRequired,
    obj_id: PropTypes.string.isRequired,
    data: PropTypes.shape({
      comment: PropTypes.string,
    }).isRequired,
  }).isRequired,
  setItemToEdit: PropTypes.func.isRequired,
};

export default EditReportItemForm;
