import { useState } from "react";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { useUpdateSourceMutation } from "../../ducks/source";
import type { Source } from "../../types";
import EditDialog, { emptyChipSx } from "./EditDialog";

interface UpdateSourceT0Props {
  source: Source;
  readOnly?: boolean;
}

const UpdateSourceT0 = ({ source, readOnly = false }: UpdateSourceT0Props) => {
  const dispatch = useAppDispatch();
  const [updateSource] = useUpdateSourceMutation();
  const [open, setOpen] = useState(false);
  const [t0, setT0] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const hasT0 = source.t0 != null;
  const firstDetectedMjd = source.photstats?.[0]?.first_detected_mjd ?? null;
  const invalid = !t0.trim() || isNaN(Number(t0));

  const submit = async (value: string | null) => {
    setIsSubmitting(true);
    const result = await updateSource({
      id: source.id,
      payload: { t0: value },
    });
    setIsSubmitting(false);
    if ("error" in result) return;
    dispatch(showNotification("Source t0 successfully updated."));
    setOpen(false);
  };

  return (
    <>
      <Chip
        size="small"
        data-testid="t0Chip"
        variant={hasT0 ? "filled" : "outlined"}
        sx={hasT0 ? undefined : emptyChipSx}
        label={hasT0 ? String(Number(Number(source.t0).toFixed(5))) : "None"}
        onClick={
          readOnly
            ? undefined
            : () => {
                setT0(hasT0 ? String(source.t0) : "");
                setOpen(true);
              }
        }
      />
      <EditDialog
        open={open}
        onClose={() => setOpen(false)}
        title="T0"
        description="Reference time of the transient, such as the explosion or the first detection"
        leftAction={
          hasT0 && (
            <Button
              secondary
              onClick={() => submit(null)}
              disabled={isSubmitting}
              data-testid="nullifyT0Button"
            >
              Clear
            </Button>
          )
        }
        actions={
          <Button
            primary
            onClick={() => submit(t0)}
            disabled={isSubmitting || invalid}
            data-testid="updateT0SubmitButton"
          >
            Save
          </Button>
        }
      >
        <TextField
          data-testid="updateT0Textfield"
          size="small"
          label="MJD"
          value={t0}
          onChange={(event) => setT0(event.target.value)}
          error={Boolean(t0.trim()) && invalid}
          autoFocus
          fullWidth
        />
        {firstDetectedMjd != null && (
          <Button
            size="small"
            sx={{ alignSelf: "flex-start", mt: -1 }}
            onClick={() => setT0(String(firstDetectedMjd))}
            data-testid="t0FirstDetectionButton"
          >
            Use first detection
          </Button>
        )}
      </EditDialog>
    </>
  );
};

export default UpdateSourceT0;
