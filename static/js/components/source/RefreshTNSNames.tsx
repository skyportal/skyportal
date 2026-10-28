import { useState } from "react";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import { useAppDispatch } from "../../types/hooks";
import { useBulkRefreshTNSMutation } from "../../ducks/source";
import { useGetProfileQuery } from "../../ducks/profile";

const formSchema = {
  type: "object",
  properties: {
    max_objects: {
      type: "integer",
      title: "Most sources to refresh",
      minimum: 1,
      default: 100,
    },
  },
};

const RefreshTNSNames = () => {
  const dispatch = useAppDispatch();
  const { data: currentUser } = useGetProfileQuery();
  const [bulkRefreshTNS] = useBulkRefreshTNSMutation();
  const [dialogOpen, setDialogOpen] = useState(false);

  const permitted =
    currentUser?.permissions.includes("Manage sources") ||
    currentUser?.permissions.includes("System admin");
  if (!permitted) return null;

  const handleSubmit = async ({ formData }: { formData: any }) => {
    try {
      const { queued } = await bulkRefreshTNS({
        stale_names_only: true,
        max_objects: formData.max_objects,
      }).unwrap();
      setDialogOpen(false);
      dispatch(
        showNotification(
          queued
            ? `Queued ${queued} sources for a TNS name refresh`
            : "No sources are waiting on a TNS name refresh",
        ),
      );
    } catch {
      dispatch(showNotification("Failed to queue a TNS name refresh", "error"));
    }
  };

  return (
    <>
      <Button
        secondary
        size="small"
        data-testid="refreshTNSNamesButton"
        onClick={() => setDialogOpen(true)}
      >
        Refresh TNS names
      </Button>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Refresh TNS names</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ marginBottom: "1rem" }}>
            Ask TNS for the current name of every classified source whose stored
            name still carries the AT prefix, most recently classified first. An
            AT becomes an SN once TNS accepts a classification for it. The
            sources are queued and their names update as the queue works through
            them.
          </DialogContentText>
          <Form
            schema={formSchema as any}
            validator={validator}
            onSubmit={handleSubmit as any}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default RefreshTNSNames;
