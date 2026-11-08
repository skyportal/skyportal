import { useState } from "react";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import EditIcon from "@mui/icons-material/Edit";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useAddTNSMutation, useUpdateSourceMutation } from "../../ducks/source";
import Button from "../Button";

interface UpdateSourceTNSProps {
  source: {
    id: string;
    withhold_from_tns?: boolean;
    withhold_from_tns_set_at?: string | null;
    withhold_from_tns_set_by?: { username?: string } | null;
  };
}

const UpdateSourceTNS = ({ source }: UpdateSourceTNSProps) => {
  const dispatch = useAppDispatch();
  const [addTNS, { isLoading }] = useAddTNSMutation();
  const [updateSource] = useUpdateSourceMutation();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [radius, setRadius] = useState("2");

  const search = async () => {
    try {
      await addTNS({
        id: source.id,
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
      <IconButton
        data-testid="updateTNSIconButton"
        onClick={() => setDialogOpen(true)}
        size="small"
      >
        <EditIcon sx={{ fontSize: "0.9rem" }} />
      </IconButton>
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>TNS</DialogTitle>
        <DialogContent
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Find the TNS name
            </Typography>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
              <TextField
                label="Radius (arcsec)"
                type="number"
                size="small"
                value={radius}
                onChange={(e) => setRadius(e.target.value)}
                sx={{ flex: 1 }}
              />
              <Button
                variant="outlined"
                onClick={search}
                disabled={isLoading || !(Number(radius) > 0)}
              >
                Search
              </Button>
            </Box>
          </Box>
          <Box>
            <FormControlLabel
              sx={{ m: 0 }}
              control={
                <Checkbox
                  size="small"
                  sx={{ p: 0.5, mr: 0.5 }}
                  checked={Boolean(source.withhold_from_tns)}
                  onChange={(event) =>
                    updateSource({
                      id: source.id,
                      payload: { withhold_from_tns: event.target.checked },
                    })
                  }
                />
              }
              label="Don't report"
            />
            <Typography
              variant="caption"
              color="text.secondary"
              component="div"
            >
              {`Never send this source to TNS, automatically or manually.${
                source.withhold_from_tns_set_at
                  ? ` Last changed by ${
                      source.withhold_from_tns_set_by?.username ??
                      "a deleted user"
                    } on ${source.withhold_from_tns_set_at.slice(0, 10)}.`
                  : ""
              }`}
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default UpdateSourceTNS;
