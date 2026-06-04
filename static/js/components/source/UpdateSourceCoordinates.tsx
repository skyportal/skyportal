import { useEffect, useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
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
import * as sourceActions from "../../ducks/source";

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

interface UpdateSourceCoordinatesProps {
  source: {
    id?: string;
    ra?: number;
    dec?: number;
  };
}

const UpdateSourceCoordinates = ({ source }: UpdateSourceCoordinatesProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [state, setState] = useState<{
    ra?: number | undefined;
    dec?: number | undefined;
  }>({
    ra: source.ra,
    dec: source.dec,
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(
      !source.ra ||
        isNaN(source.ra as number) ||
        !source.dec ||
        isNaN(source.dec as number),
    );
    setState({
      ra: source.ra,
      dec: source.dec,
    });
  }, [source, setInvalid]);

  const handleChange = (e: any) => {
    const newState: any = {};
    newState[e.target.name] = parseFloat(e.target.value);
    setState({
      ...state,
      ...newState,
    });
  };

  const handleSubmit = async (subState: {
    ra?: number | undefined;
    dec?: number | undefined;
  }) => {
    setIsSubmitting(true);
    const newState: any = {};
    if (!Number.isNaN(subState.ra)) {
      newState.ra = subState.ra;
    }
    if (!Number.isNaN(subState.dec)) {
      newState.dec = subState.dec;
    }
    const result = (await dispatch(
      sourceActions.updateSource(source.id!, {
        ...newState,
      }),
    )) as any;
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Source location successfully updated."));
      setDialogOpen(false);
    }
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
        <DialogTitle>Update Coordinates</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a valid float" />
            )}
            <TextField
              data-testid="updateCoordinatesRATextfield"
              size="small"
              label="ra"
              value={state.ra}
              name="ra"
              onChange={handleChange}
              type="number"
              variant="outlined"
            />
          </div>
          <p />
          <div>
            <TextField
              data-testid="updateCoordinatesDecTextfield"
              size="small"
              label="dec"
              value={state.dec}
              name="dec"
              onChange={handleChange}
              type="number"
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => {
                handleSubmit(state);
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateCoordinatesSubmitButton"
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

export default UpdateSourceCoordinates;
