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
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import { usePostGcnAliasMutation } from "../../ducks/gcnEvent";
import { useIsReadOnly } from "../../ducks/profile";

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

interface AddGcnAliasProps {
  gcnEvent: {
    dateobs?: string;
    aliases: string[];
  };
}

const AddGcnAlias = ({ gcnEvent }: AddGcnAliasProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const [postGcnAlias] = usePostGcnAliasMutation();
  const [alias, setAlias] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(gcnEvent?.aliases?.includes(alias as string));
  }, [gcnEvent, setInvalid, alias]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAlias(e.target.value);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await postGcnAlias({
        dateobs: gcnEvent.dateobs as string,
        params: { alias },
      }).unwrap();
      dispatch(showNotification("GCN Event Alias successfully added."));
      setDialogOpen(false);
    } catch {
      // error notification handled by baseQuery
    }
    setIsSubmitting(false);
  };

  if (isReadOnly) return null;

  return (
    <>
      <AddIcon
        data-testid="addGcnEventAliasIconButton"
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Add Alias</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a new alias" />
            )}
            <TextField
              data-testid="addAliasTextfield"
              size="small"
              label="alias"
              name="alias"
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
              data-testid="addAliasSubmitButton"
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

export default AddGcnAlias;
