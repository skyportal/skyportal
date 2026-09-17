import { useState } from "react";

import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { useSaveSourceMutation } from "../../ducks/source";
import type { SuperObjEpoch } from "../../ducks/superObjs";

interface GroupOption {
  id: number;
  name: string;
  nickname?: string | null;
}

interface SaveTrackButtonProps {
  trackName: string;
  /** The track's distinct detections, already deduplicated by the caller. */
  epochs: SuperObjEpoch[];
  userGroups: GroupOption[];
}

/**
 * Accept a track by saving its detections to a group.
 *
 * Every detection is saved, not just one: accepting a track means accepting
 * that all of them are the same body, and each is its own Obj. A group set to
 * auto-report files one submission for the whole track regardless, because the
 * submission is deduplicated across the track's members.
 *
 * There is no reject control because SkyPortal has no rejection: a candidate
 * the reviewer does not save is simply not saved.
 */
const SaveTrackButton = ({
  trackName,
  epochs,
  userGroups,
}: SaveTrackButtonProps) => {
  const dispatch = useAppDispatch();
  const [saveSource] = useSaveSourceMutation();
  const [open, setOpen] = useState(false);
  const [groupId, setGroupId] = useState<number | "">("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (groupId === "") {
      return;
    }
    setSaving(true);
    const failures: string[] = [];
    // Saved one at a time rather than in parallel. Each save fires the
    // auto-publisher, which files an MPC submission only if none exists for any
    // of the track's members; concurrent saves could each find none and file
    // one, which is the duplicate submission the dedupe exists to prevent.
    for (const epoch of epochs) {
      try {
        // eslint-disable-next-line no-await-in-loop
        const result = await saveSource({
          id: epoch.id,
          group_ids: [groupId],
        }).unwrap();
        if ((result as { status?: string })?.status === "error") {
          failures.push(epoch.id);
        }
      } catch {
        failures.push(epoch.id);
      }
    }
    setSaving(false);
    setOpen(false);
    if (failures.length) {
      dispatch(
        showNotification(
          `Saved ${epochs.length - failures.length} of ${epochs.length} ` +
            `detections; ${failures.length} failed`,
          "error",
        ),
      );
    } else {
      dispatch(
        showNotification(`Saved ${epochs.length} detections of ${trackName}`),
      );
    }
  };

  return (
    <>
      <Button
        size="small"
        variant="contained"
        onClick={() => setOpen(true)}
        disabled={epochs.length === 0}
        data-testid={`save-track-${trackName}`}
      >
        Save track
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Save {trackName}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Saves all {epochs.length} detections of this track as sources. If
            the group reports to the Minor Planet Center, the track is submitted
            once rather than once per detection.
          </Typography>
          <Select
            fullWidth
            size="small"
            displayEmpty
            value={groupId}
            onChange={(e) => setGroupId(Number(e.target.value))}
          >
            <MenuItem value="" disabled>
              Select a group
            </MenuItem>
            {userGroups.map((group) => (
              <MenuItem key={group.id} value={group.id}>
                {group.nickname || group.name}
              </MenuItem>
            ))}
          </Select>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={save}
            disabled={groupId === "" || saving}
          >
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default SaveTrackButton;
