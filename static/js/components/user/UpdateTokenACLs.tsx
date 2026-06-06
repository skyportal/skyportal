import { useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import SaveIcon from "@mui/icons-material/Save";
import FormControlLabel from "@mui/material/FormControlLabel";
import { Controller, useForm } from "react-hook-form";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import { useAppDispatch } from "../../types/hooks";
import { useUpdateTokenMutation } from "../../ducks/profile";

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

interface UpdateTokenACLsProps {
  tokenId: string;
  availableACLs: string[];
  currentACLs: string[];
}

const UpdateTokenACLs = ({
  tokenId,
  currentACLs,
  availableACLs,
}: UpdateTokenACLsProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [updateToken] = useUpdateTokenMutation();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { control, getValues } = useForm();

  const handleSubmit = async () => {
    const { acls } = getValues();
    const selectedACLs = availableACLs?.filter((_include, idx) => acls[idx]);
    const data: any = {};
    data.acls = selectedACLs;

    setIsSubmitting(true);
    try {
      await updateToken({ tokenID: tokenId, form_data: data }).unwrap();
      dispatch(showNotification("ACLs successfully updated."));
      setDialogOpen(false);
    } catch {
      // error notification handled by the API layer
    }
    setIsSubmitting(false);
  };

  return (
    <>
      <EditIcon
        data-testid="updateCoordinatesIconButton"
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Update ACLs</DialogTitle>
        <DialogContent>
          <div>
            {availableACLs?.map((acl, idx) => (
              <FormControlLabel
                key={acl}
                control={
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <Checkbox
                        onChange={(event) => onChange(event.target.checked)}
                        checked={value}
                        data-testid={`acls[${idx}]`}
                      />
                    )}
                    name={`acls[${idx}]`}
                    control={control}
                    defaultValue={currentACLs?.includes(acl)}
                  />
                }
                label={acl}
              />
            ))}
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => {
                handleSubmit();
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateACLsSubmitButton"
              disabled={isSubmitting}
            >
              Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UpdateTokenACLs;
