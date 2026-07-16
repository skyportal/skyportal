import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import { useGetGroupsQuery } from "../ducks/groups";
import {
  useGetObjGroupsQuery,
  useUpdateSourceGroupsMutation,
} from "../ducks/source";
import { useAppDispatch } from "../types/hooks";

interface SaveCandidateGroupsDialogProps {
  objId: string | null;
  open: boolean;
  onClose: () => void;
}

// Save/manage a candidate's groups from the toolbar quick-search. The checkboxes
// are seeded with the obj's current groups, so ticking adds (invite/save) and
// unticking removes (unsave) — same add/remove semantics as the source page's
// EditSourceGroups (POST /api/source_groups with inviteGroupIds/unsaveGroupIds).
const SaveCandidateGroupsDialog = ({
  objId,
  open,
  onClose,
}: SaveCandidateGroupsDialogProps) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const userAccessibleGroups = useGetGroupsQuery().data?.userAccessible ?? [];
  const { data: currentGroups } = useGetObjGroupsQuery(objId as string, {
    skip: !objId,
  });
  const [updateSourceGroups, { isLoading }] = useUpdateSourceGroupsMutation();
  const [groupIDs, setGroupIDs] = useState<number[]>([]);

  const currentGroupIds = (currentGroups ?? []).map((g: any) => g.id);

  // Seed the checkboxes with the obj's current groups whenever it changes.
  useEffect(() => {
    setGroupIDs((currentGroups ?? []).map((g: any) => g.id));
  }, [objId, currentGroups]);

  const toggleGroup = (id: number) => {
    setGroupIDs((prev) =>
      prev.includes(id) ? prev.filter((g) => g !== id) : [...prev, id],
    );
  };

  const inviteGroupIds = groupIDs.filter((id) => !currentGroupIds.includes(id));
  const unsaveGroupIds = currentGroupIds.filter(
    (id: number) => !groupIDs.includes(id),
  );
  const hasChanges = inviteGroupIds.length > 0 || unsaveGroupIds.length > 0;

  const goToSource = () => {
    onClose();
    navigate(`/source/${objId}`);
  };

  const handleUpdate = async () => {
    if (!objId || !hasChanges) {
      return;
    }
    try {
      await updateSourceGroups({
        objId,
        inviteGroupIds,
        unsaveGroupIds,
      }).unwrap();
      dispatch(showNotification(`Updated groups for ${objId}.`));
    } catch {
      // error notification handled by the baseQuery; stay on the dialog
      return;
    }
    onClose();
    // Only go to the source page if it's still saved to a group; removing it from
    // every group leaves no source page to navigate to.
    if (groupIDs.length > 0) {
      navigate(`/source/${objId}`);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Save candidate {objId}</DialogTitle>
      <DialogContent>
        <Typography variant="subtitle2" gutterBottom>
          Groups (checked = saved)
        </Typography>
        <FormGroup
          sx={{ maxHeight: "40vh", overflowY: "auto", flexWrap: "nowrap" }}
        >
          {userAccessibleGroups.map((group: any) => (
            <FormControlLabel
              key={group.id}
              control={
                <Checkbox
                  checked={groupIDs.includes(group.id)}
                  onChange={() => toggleGroup(group.id)}
                  size="small"
                />
              }
              label={group.nickname || group.name}
            />
          ))}
        </FormGroup>
      </DialogContent>
      <DialogActions>
        {currentGroupIds.length > 0 && (
          <Button onClick={goToSource}>Go to source page</Button>
        )}
        <Button
          primary
          onClick={handleUpdate}
          disabled={isLoading || !hasChanges}
        >
          {groupIDs.length === 0
            ? "Update groups"
            : currentGroupIds.length > 0
              ? "Update groups & go to source page"
              : "Save & go to source page"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SaveCandidateGroupsDialog;
