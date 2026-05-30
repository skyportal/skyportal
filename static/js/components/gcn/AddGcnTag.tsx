import React, { useEffect, useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { GcnEvent } from "../../types";
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import * as gcnTagsActions from "../../ducks/gcnTags";

const useStyles = makeStyles()(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
}));

interface AddGcnTagProps {
  gcnEvent: GcnEvent;
}

const AddGcnTag = ({ gcnEvent }: AddGcnTagProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [tag, setTag] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(gcnEvent?.tags?.includes(tag as string) ?? false);
  }, [gcnEvent, setInvalid, tag]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTag(e.target.value);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    const result: any = await dispatch(
      gcnTagsActions.postGcnTag({ dateobs: gcnEvent.dateobs, text: tag }),
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("GCN Event Tag successfully added."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <AddIcon
        data-testid="addGcnEventTagIconButton"
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Add Tag</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a new tag" />
            )}
            <TextField
              data-testid="addTagTextfield"
              size="small"
              label="tag"
              name="tag"
              onChange={handleChange}
              type="string"
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => {
                handleSubmit();
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="addTagSubmitButton"
              disabled={isSubmitting || invalid}
            >
              Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AddGcnTag;
