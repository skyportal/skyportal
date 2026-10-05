import { forwardRef, useState } from "react";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Tooltip from "@mui/material/Tooltip";
import Slide from "@mui/material/Slide";
import SettingsIcon from "@mui/icons-material/Settings";

import Button from "../Button";
import ScanningProfilesList from "./ScanningProfilesList";

const Transition = forwardRef(function Transition(props: any, ref) {
  return <Slide direction="up" ref={ref} {...props} />;
});

interface CandidatesPreferencesProps {
  hasProfiles: boolean;
  selectedScanningProfile?: Record<string, any> | null;
  setSelectedScanningProfile: (...args: any[]) => void;
}

const CandidatesPreferences = ({
  hasProfiles,
  selectedScanningProfile,
  setSelectedScanningProfile,
}: CandidatesPreferencesProps) => {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <>
      <Tooltip title="Save the current search options as a profile, or load one">
        <Button
          size="small"
          endIcon={<SettingsIcon />}
          data-testid="manageScanningProfilesButton"
          onClick={() => setOpen(true)}
        >
          {hasProfiles
            ? "Manage scanning profiles"
            : "Create a scanning profile"}
        </Button>
      </Tooltip>
      <Dialog
        open={open}
        fullScreen
        onClose={close}
        slots={{ transition: Transition }}
      >
        <DialogContent sx={{ bgcolor: "background.default" }}>
          <ScanningProfilesList
            selectedScanningProfile={selectedScanningProfile}
            setSelectedScanningProfile={setSelectedScanningProfile}
            onClose={close}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default CandidatesPreferences;
