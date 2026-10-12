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

const TEST_IDS = {
  Tag: {
    icon: "addGcnEventTagIconButton",
    field: "addTagTextfield",
    submit: "addTagSubmitButton",
  },
  Alias: {
    icon: "addGcnEventAliasIconButton",
    field: "addAliasTextfield",
    submit: "addAliasSubmitButton",
  },
};

interface AddGcnEventValueProps {
  noun: "Tag" | "Alias";
  existing: string[] | undefined;
  onSave: (value: string) => Promise<unknown>;
}

// "+" icon and dialog for adding a tag or alias to a GCN event.
const AddGcnEventValue = ({
  noun,
  existing,
  onSave,
}: AddGcnEventValueProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const [value, setValue] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(existing?.includes(value as string) ?? false);
  }, [existing, setInvalid, value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await onSave(value as string);
      dispatch(showNotification(`GCN Event ${noun} successfully added.`));
      setDialogOpen(false);
    } catch {
      // error notification handled centrally by the base query
    }
    setIsSubmitting(false);
  };

  if (isReadOnly) return null;

  const testIds = TEST_IDS[noun];
  const lowerNoun = noun.toLowerCase();

  return (
    <>
      <AddIcon
        data-testid={testIds.icon}
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>{`Add ${noun}`}</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError
                message={`Please enter a new ${lowerNoun}`}
              />
            )}
            <TextField
              data-testid={testIds.field}
              size="small"
              label={lowerNoun}
              name={lowerNoun}
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
              data-testid={testIds.submit}
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

export default AddGcnEventValue;
