import { useState } from "react";
import { useForm } from "react-hook-form";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAddMPCMutation } from "../../ducks/source";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";

dayjs.extend(utc);

interface UpdateSourceMPCProps {
  source: {
    id: string;
    mpc_name?: string;
    first_detected?: string;
    [key: string]: any;
  };
}

const UpdateSourceMPC = ({ source }: UpdateSourceMPCProps) => {
  const dispatch = useAppDispatch();
  const [addMPC] = useAddMPCMutation();
  const [dialogOpen, setDialogOpen] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm({
    defaultValues: {
      date: (
        source.first_detected ?? dayjs.utc().format("YYYY-MM-DDTHH:mm")
      ).slice(0, 16),
      search_radius: 1,
      limiting_magnitude: 24,
      obscode: "500",
    },
  });
  const field = (
    name: "date" | "search_radius" | "limiting_magnitude" | "obscode",
  ) => {
    const { ref, ...rest } = register(name, {
      valueAsNumber: name === "search_radius" || name === "limiting_magnitude",
    });
    return { ...rest, inputRef: ref, size: "small" as const, required: true };
  };

  const onSubmit = async (formData: Record<string, any>) => {
    const { error } = await addMPC({ id: source.id, formData });
    if (error) return;
    dispatch(
      showNotification(
        "MPC query sent. The MPC name will appear once the MPC answers.",
      ),
    );
    setDialogOpen(false);
  };

  return (
    <>
      <Tooltip title="Search the Minor Planet Center for a known solar system object at this position">
        <IconButton
          size="small"
          data-testid="updateMPCIconButton"
          onClick={() => setDialogOpen(true)}
        >
          <TravelExploreIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>Query the Minor Planet Center</DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ mb: 2 }}>
              Look for a known solar system object near this position. Its name
              is added to the source when one is found.
            </DialogContentText>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 2,
                pt: 1,
              }}
            >
              <TextField
                {...field("date")}
                type="datetime-local"
                label="Date (UTC)"
                slotProps={{ inputLabel: { shrink: true } }}
                sx={{ gridColumn: "1 / -1" }}
              />
              <TextField
                {...field("search_radius")}
                type="number"
                label="Search radius [arcmin]"
                slotProps={{ htmlInput: { step: 0.1, min: 0 } }}
              />
              <TextField
                {...field("limiting_magnitude")}
                type="number"
                label="Limiting magnitude"
                slotProps={{ htmlInput: { step: 0.1 } }}
              />
              <TextField
                {...field("obscode")}
                label="Observatory code"
                helperText="500 is the geocenter"
                sx={{ gridColumn: "1 / -1" }}
              />
            </Box>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              primary
              type="submit"
              disabled={isSubmitting}
              endIcon={<TravelExploreIcon />}
            >
              Query
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
};

export default UpdateSourceMPC;
