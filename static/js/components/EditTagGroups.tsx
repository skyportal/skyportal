import { useGetGroupsQuery } from "../ducks/groups";
import { useState, useMemo, useEffect } from "react";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogActions from "@mui/material/DialogActions";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Typography from "@mui/material/Typography";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../types/hooks";
import Button from "./Button";
import * as objectTagsActions from "../ducks/objectTags";

interface TagShape {
  id: number;
  name: string;
  objtagoption_id: number;
  groups?: { id: number }[];
  total_group_count?: number;
}

interface EditTagGroupsProps {
  tag?: TagShape | null;
  source: {
    id: string;
    groups?: { id: number }[];
  };
  groups: { id: number; name?: string }[];
  open: boolean;
  onClose: () => void;
}

const EditTagGroups = ({
  tag = null,
  source,
  groups,
  open,
  onClose,
}: EditTagGroupsProps) => {
  const dispatch = useAppDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);

  const { data: groupsData } = useGetGroupsQuery();
  const userGroups = useMemo(
    () => groupsData?.userAccessible ?? [],
    [groupsData],
  );
  const userGroupIds = useMemo(
    () => new Set(userGroups?.map((g) => g.id) || []),
    [userGroups],
  );

  // Get the tag's current group IDs that the user has access to
  const tagGroups = tag?.groups;
  const tagGroupIds = useMemo(
    () => new Set(tagGroups?.map((g) => g.id) || []),
    [tagGroups],
  );

  // Filter available groups to only those where the source is saved
  const sourceGroupIds = useMemo(
    () => new Set(source.groups?.map((g) => g.id) || []),
    [source.groups],
  );

  // Groups associated with this tag that the user cannot see
  const inaccessibleTagGroupCount =
    (tag?.total_group_count ?? 0) - (tag?.groups?.length ?? 0);

  // Groups available for selection: user has access AND source is saved there
  const availableGroups = useMemo(
    () =>
      groups?.filter(
        (g) => userGroupIds.has(g.id) && sourceGroupIds.has(g.id),
      ) || [],
    [groups, userGroupIds, sourceGroupIds],
  );

  // Initialize selected groups when dialog opens
  useEffect(() => {
    if (open && tag) {
      const initialSelected = availableGroups
        .filter((g) => tagGroupIds.has(g.id))
        .map((g) => g.id);
      setSelectedGroupIds(initialSelected);
    }
  }, [open, tag, availableGroups, tagGroupIds]);

  const handleClose = () => {
    setSelectedGroupIds([]);
    onClose();
  };

  const handleGroupToggle = (groupId: number) => {
    setSelectedGroupIds((prev) => {
      if (prev.includes(groupId)) {
        return prev.filter((id) => id !== groupId);
      }
      return [...prev, groupId];
    });
  };

  const handleSubmit = async () => {
    if (selectedGroupIds.length === 0) {
      dispatch(
        showNotification(
          "At least one group must be selected. Use delete to remove the tag entirely.",
          "error",
        ),
      );
      return;
    }

    setIsSubmitting(true);

    // Calculate groups to remove and add
    const currentUserTagGroupIds = availableGroups
      .filter((g) => tagGroupIds.has(g.id))
      .map((g) => g.id);

    const groupsToRemove = currentUserTagGroupIds.filter(
      (id) => !selectedGroupIds.includes(id),
    );
    const groupsToAdd = selectedGroupIds.filter((id) => !tagGroupIds.has(id));

    try {
      if (groupsToAdd.length > 0) {
        const addResult: any = await dispatch(
          objectTagsActions.addObjectTag({
            obj_id: source.id,
            objtagoption_id: tag!.objtagoption_id,
            group_ids: groupsToAdd,
          }),
        );
        if (addResult.status !== "success") {
          throw new Error(addResult.message || "Failed to add groups");
        }
      }

      if (groupsToRemove.length > 0) {
        const deleteResult: any = await dispatch(
          objectTagsActions.deleteObjectTag({
            id: tag!.id,
            group_ids: groupsToRemove,
          }),
        );
        if (deleteResult.status !== "success") {
          throw new Error(deleteResult.message || "Failed to remove groups");
        }
      }

      dispatch(showNotification("Tag groups updated successfully"));
      handleClose();
    } catch (error: any) {
      dispatch(showNotification(error.message, "error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = () => {
    setIsDeleting(true);

    dispatch(objectTagsActions.deleteObjectTag({ id: tag!.id })).then(
      (result: any) => {
        setIsDeleting(false);

        if (result.status === "success") {
          dispatch(showNotification("Tag removed from source"));
          handleClose();
        } else {
          dispatch(
            showNotification(result.message || "Failed to delete tag", "error"),
          );
        }
      },
    );
  };

  if (!tag) return null;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>Edit tag visibility: {tag.name}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          Select which groups can see this tag on the source.
        </Typography>

        {availableGroups.length > 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              marginTop: "0.5rem",
            }}
          >
            {availableGroups.map((group) => (
              <FormControlLabel
                key={group.id}
                control={
                  <Checkbox
                    checked={selectedGroupIds.includes(group.id)}
                    onChange={() => handleGroupToggle(group.id)}
                  />
                }
                label={group.name}
              />
            ))}
          </div>
        ) : (
          <Typography variant="body2" color="error">
            No groups available for this tag.
          </Typography>
        )}
        {inaccessibleTagGroupCount > 0 && (
          <Typography variant="caption" color="textSecondary">
            This tag is also shared with {inaccessibleTagGroupCount} group
            {inaccessibleTagGroupCount > 1 ? "s" : ""} you don&apos;t have
            access to.
          </Typography>
        )}
      </DialogContent>
      <DialogActions sx={{ justifyContent: "space-between" }}>
        <Button
          onClick={handleDelete}
          variant="outlined"
          color="error"
          disabled={isDeleting || isSubmitting}
          data-testid="delete-tag-button"
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </Button>
        <div>
          <Button
            onClick={handleClose}
            secondary
            style={{ marginRight: "0.5rem" }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            primary
            disabled={
              isSubmitting || isDeleting || selectedGroupIds.length === 0
            }
          >
            {isSubmitting ? "Saving..." : "Save"}
          </Button>
        </div>
      </DialogActions>
    </Dialog>
  );
};

export default EditTagGroups;
