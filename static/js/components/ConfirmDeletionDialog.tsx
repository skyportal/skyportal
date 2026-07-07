import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Button from "./Button";

interface ConfirmDeletionDialogProps {
  deleteFunction: (...args: any[]) => void;
  dialogOpen: boolean;
  closeDialog: (...args: any[]) => void;
  resourceName: string;
}

const ConfirmDeletionDialog = ({
  deleteFunction,
  dialogOpen,
  closeDialog,
  resourceName,
}: ConfirmDeletionDialogProps) => (
  <Dialog sx={{ "z-index": 99999 }} open={dialogOpen} onClose={closeDialog}>
    <DialogTitle>Delete {resourceName}?</DialogTitle>
    <DialogContent>
      Are you sure you want to delete this/these {resourceName}?
    </DialogContent>
    <DialogActions>
      <Button
        data-testid="dismissDeletetionButton"
        secondary
        autoFocus
        onClick={closeDialog}
      >
        Dismiss
      </Button>
      <Button
        data-testid="confirmDeletetionButton"
        primary
        onClick={() => deleteFunction()}
      >
        Confirm
      </Button>
    </DialogActions>
  </Dialog>
);

export default ConfirmDeletionDialog;
