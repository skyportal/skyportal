import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

interface ConfirmFilterDeletionDialogProps {
  filter: { id: number; name: string } | null;
  closeDialog: () => void;
  deleteFunction: () => void;
}

const ConfirmFilterDeletionDialog = ({
  filter,
  closeDialog,
  deleteFunction,
}: ConfirmFilterDeletionDialogProps) =>
  filter && (
    <ConfirmDeletionDialog
      deleteFunction={deleteFunction}
      dialogOpen
      closeDialog={closeDialog}
      resourceName={filter.name}
      message={`Deleting "${filter.name}" also deletes all of its versions, and none of it can be recovered.`}
    />
  );

export default ConfirmFilterDeletionDialog;
