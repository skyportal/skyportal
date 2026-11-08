import { useState } from "react";

import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useAddTNSMutation } from "../../ducks/source";
import Button from "../Button";

const UpdateSourceTNS = ({ sourceId }: { sourceId: string }) => {
  const dispatch = useAppDispatch();
  const [addTNS, { isLoading }] = useAddTNSMutation();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [radius, setRadius] = useState("2");

  const search = async () => {
    try {
      await addTNS({
        id: sourceId,
        formData: { radius: Number(radius) },
      }).unwrap();
      dispatch(showNotification("Successfully queried TNS"));
      setDialogOpen(false);
    } catch {
      dispatch(showNotification("Failed to query TNS", "error"));
    }
  };

  return (
    <>
      <Tooltip title="Look for this source on TNS">
        <Button
          variant="outlined"
          color="primary"
          size="small"
          onClick={() => setDialogOpen(true)}
          data-testid="updateTNSIconButton"
          sx={{ py: 0 }}
        >
          Search
        </Button>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Search TNS</DialogTitle>
        <DialogContent>
          <TextField
            label="Search radius (arcsec)"
            type="number"
            size="small"
            fullWidth
            autoFocus
            value={radius}
            onChange={(e) => setRadius(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            primary
            onClick={search}
            disabled={isLoading || !(Number(radius) > 0)}
          >
            Search
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default UpdateSourceTNS;
