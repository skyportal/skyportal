import { useState } from "react";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import { useAppDispatch } from "../../types/hooks";
import {
  downloadAllocationReport,
  downloadFollowupSchedule,
} from "../../ducks/followup_requests";
import Button from "../Button";
import useTriggeredAllocations from "./useTriggeredAllocations";

interface FollowupScheduleDialogProps {
  open: boolean;
  onClose: () => void;
}

const FollowupScheduleDialog = ({
  open,
  onClose,
}: FollowupScheduleDialogProps) => {
  const dispatch = useAppDispatch();
  const { instruments } = useTriggeredAllocations();
  const [instrument, setInstrument] = useState<any>(null);
  const [format, setFormat] = useState("csv");
  const [includeStandards, setIncludeStandards] = useState(false);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Schedule (with astroplan)</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <Autocomplete
            options={instruments}
            value={instrument}
            onChange={(_e, value) => setInstrument(value)}
            renderInput={(params) => (
              <TextField {...params} label="Instrument" />
            )}
          />
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <TextField
              select
              label="Format"
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              sx={{ minWidth: 120 }}
            >
              <MenuItem value="csv">CSV</MenuItem>
              <MenuItem value="pdf">PDF</MenuItem>
              <MenuItem value="png">PNG</MenuItem>
            </TextField>
            <FormControlLabel
              label="Include standards"
              control={
                <Checkbox
                  checked={includeStandards}
                  onChange={(e) => setIncludeStandards(e.target.checked)}
                />
              }
            />
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button
          secondary
          disabled={!instrument}
          onClick={() => dispatch(downloadAllocationReport(instrument.id))}
        >
          Allocation Analysis
        </Button>
        <Button
          primary
          disabled={!instrument}
          onClick={() =>
            dispatch(
              downloadFollowupSchedule(instrument.id, format, includeStandards),
            )
          }
        >
          Download Schedule
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default FollowupScheduleDialog;
