import { useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { useUpdateSourceMutation } from "../../ducks/source";
import EditDialog from "./EditDialog";

interface UpdateSourceCoordinatesProps {
  source: {
    id?: string;
    ra?: number;
    dec?: number;
  };
}

const UpdateSourceCoordinates = ({ source }: UpdateSourceCoordinatesProps) => {
  const dispatch = useAppDispatch();
  const [updateSource] = useUpdateSourceMutation();
  const [open, setOpen] = useState(false);
  const [ra, setRa] = useState("");
  const [dec, setDec] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const badRa = !ra.trim() || isNaN(Number(ra));
  const badDec = !dec.trim() || isNaN(Number(dec));

  const submit = async () => {
    setIsSubmitting(true);
    const result = await updateSource({
      id: source.id!,
      payload: { ra: Number(ra), dec: Number(dec) },
    });
    setIsSubmitting(false);
    if ("error" in result) return;
    dispatch(showNotification("Source location successfully updated."));
    setOpen(false);
  };

  return (
    <>
      <Tooltip title="Edit position">
        <IconButton
          size="small"
          data-testid="updateCoordinatesIconButton"
          onClick={() => {
            setRa(source.ra != null ? String(source.ra) : "");
            setDec(source.dec != null ? String(source.dec) : "");
            setOpen(true);
          }}
        >
          <EditIcon />
        </IconButton>
      </Tooltip>
      <EditDialog
        open={open}
        onClose={() => setOpen(false)}
        title="Position"
        actions={
          <Button
            primary
            onClick={submit}
            disabled={isSubmitting || badRa || badDec}
            data-testid="updateCoordinatesSubmitButton"
          >
            Save
          </Button>
        }
      >
        <Box sx={{ display: "flex", gap: 1 }}>
          <TextField
            data-testid="updateCoordinatesRATextfield"
            size="small"
            label="RA (deg)"
            value={ra}
            onChange={(e) => setRa(e.target.value)}
            error={Boolean(ra.trim()) && badRa}
            autoFocus
            fullWidth
          />
          <TextField
            data-testid="updateCoordinatesDecTextfield"
            size="small"
            label="Dec (deg)"
            value={dec}
            onChange={(e) => setDec(e.target.value)}
            error={Boolean(dec.trim()) && badDec}
            fullWidth
          />
        </Box>
      </EditDialog>
    </>
  );
};

export default UpdateSourceCoordinates;
