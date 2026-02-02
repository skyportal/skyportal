import { useState, useMemo, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogActions from "@mui/material/DialogActions";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import * as objectTagsActions from "../ducks/objectTags";

const useStyles = makeStyles(() => ({
  groupList: {
    display: "flex",
    flexDirection: "column",
    marginTop: "0.5rem",
  },
  dialogActions: {
    justifyContent: "space-between",
  },
}));

const EditTagGroups = ({ tag, source, groups, open, onClose }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const userGroups = useSelector((state) => state.groups.userAccessible);
  const userGroupIds = useMemo(
    () => new Set(userGroups?.map((g) => g.id) || []),
    [userGroups],
  );

  // Get the tag's current group IDs that the user has access to
  const tagGroupIds = useMemo(
    () => new Set(tag?.groups?.map((g) => g.id) || []),
    [tag?.groups],
  );

  // Filter available groups to only those where the source is saved
  const sourceGroupIds = useMemo(
    () => new Set(source.groups?.map((g) => g.id) || []),
    [source.groups],
  );

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

  const handleGroupToggle = (groupId) => {
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
    const groupsToAdd = selectedGroupIds.filter(
      (id) => !tagGroupIds.has(id),
    );

    try {
      // Remove groups if needed
      if (groupsToRemove.length > 0) {
        const deleteResult = await dispatch(
          objectTagsActions.deleteObjectTag({
            id: tag.id,
            group_ids: groupsToRemove,
          }),
        );
        if (deleteResult.status !== "success") {
          throw new Error(deleteResult.message || "Failed to remove groups");
        }
      }

      // Add groups if needed
      if (groupsToAdd.length > 0) {
        const addResult = await dispatch(
          objectTagsActions.addObjectTag({
            obj_id: source.id,
            objtagoption_id: tag.objtagoption_id,
            group_ids: groupsToAdd,
          }),
        );
        if (addResult.status !== "success") {
          throw new Error(addResult.message || "Failed to add groups");
        }
      }

      dispatch(showNotification("Tag groups updated successfully"));
      handleClose();
    } catch (error) {
      dispatch(showNotification(error.message, "error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = () => {
    setIsDeleting(true);

    dispatch(
      objectTagsActions.deleteObjectTag({ id: tag.id }),
    ).then((result) => {
      setIsDeleting(false);

      if (result.status === "success") {
        dispatch(showNotification("Tag removed from source"));
        handleClose();
      } else {
        dispatch(
          showNotification(result.message || "Failed to delete tag", "error"),
        );
      }
    });
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
          <div className={classes.groupList}>
            {availableGroups.map((group) => (
              <FormControlLabel
                key={group.id}
                control={
                  <Checkbox
                    checked={selectedGroupIds.includes(group.id)}
                    onChange={() => handleGroupToggle(group.id)}
                    data-testid={`tag-group-checkbox-${group.id}`}
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
      </DialogContent>
      <DialogActions className={classes.dialogActions}>
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
          <Button onClick={handleClose} secondary style={{ marginRight: "0.5rem" }}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            primary
            disabled={isSubmitting || isDeleting || selectedGroupIds.length === 0}
            data-testid="save-tag-groups-button"
          >
            {isSubmitting ? "Saving..." : "Save"}
          </Button>
        </div>
      </DialogActions>
    </Dialog>
  );
};

EditTagGroups.propTypes = {
  tag: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    objtagoption_id: PropTypes.number.isRequired,
    groups: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number.isRequired,
      }),
    ),
  }),
  source: PropTypes.shape({
    id: PropTypes.string.isRequired,
    groups: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
      }),
    ),
  }).isRequired,
  groups: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    }),
  ).isRequired,
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

EditTagGroups.defaultProps = {
  tag: null,
};

export default EditTagGroups;
