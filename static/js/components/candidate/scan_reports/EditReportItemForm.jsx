import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Link from "@mui/material/Link";
import Box from "@mui/material/Box";
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
    comment: itemToEdit?.comment,
    already_classified: itemToEdit?.already_classified,
  });

  const updateReportItemSchema = () => {
    return {
      type: "object",
      properties: {
        comment: { type: ["string", "null"], title: "comment" },
        already_classified: {
          type: ["boolean", "null"],
          title: "Already classified?",
        },
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
          <Box>Update scan report item</Box>
          <Link
            href={`/source/${itemToEdit.obj_id}`}
            underline="none"
            color="text.secondary"
            fontSize="1rem"
            target="_blank"
          >
            {itemToEdit.obj_id}
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
    comment: PropTypes.string,
    already_classified: PropTypes.bool,
  }).isRequired,
  setItemToEdit: PropTypes.func.isRequired,
};

export default EditReportItemForm;
