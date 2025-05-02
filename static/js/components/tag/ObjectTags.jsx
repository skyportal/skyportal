import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import AddIcon from "@mui/icons-material/Add";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogActions from "@mui/material/DialogActions";
import Divider from "@mui/material/Divider";
import makeStyles from "@mui/styles/makeStyles";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import * as objectTagsActions from "../../ducks/objectTags";
import * as sourceActions from "../../ducks/source";

const useStyles = makeStyles((theme) => ({
  root: {
    margin: "0",
    padding: "0",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  title: {
    margin: 0,
    marginRight: "0.45rem",
    padding: "0",
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: 0,
      marginBottom: 0,
      marginLeft: "0.05rem",
      marginRight: "0.05rem",
    },
  },
  tagDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
  addButton: {
    height: "0.75rem",
    cursor: "pointer",
  },
  selectFormControl: {
    minWidth: 250,
    width: "100%",
    marginBottom: theme.spacing(2),
  },
  loadingIcon: {
    marginLeft: theme.spacing(1),
    fontSize: "0.875rem",
  },
}));

const ObjectTags = ({ source }) => {
  const styles = useStyles();
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [selectedTagId, setSelectedTagId] = useState("");
  const [isAddingTag, setIsAddingTag] = useState(false);
  const [newTagName, setNewTagName] = useState("");
  const [isCreatingTag, setIsCreatingTag] = useState(false);
  const [tagError, setTagError] = useState("");
  const tagOptions = useSelector((state) => state.objectTags || []);
  const currentUser = useSelector((state) => state.profile);
  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage sources");

  useEffect(() => {
    dispatch(objectTagsActions.fetchTagOptions());
  }, [dispatch]);

  const handleOpenDialog = () => {
    setOpen(true);
    setNewTagName("");
  };

  const handleCloseDialog = () => {
    setOpen(false);
    setSelectedTagId("");
    setNewTagName("");
  };

  const handleTagChange = (event) => {
    setSelectedTagId(event.target.value);
  };

  const refreshSource = () => {
    if (source && source.id) {
      dispatch(sourceActions.fetchSource(source.id));
    }
  };

  const handleNewTagNameChange = (event) => {
    setNewTagName(event.target.value);
  };

  const handleCreateTag = () => {
    if (!newTagName.trim()) {
      setTagError("Tag name cannot be empty");
      return;
    }

    setIsCreatingTag(true);

    dispatch(
      objectTagsActions.createTagOption({
        name: newTagName,
      }),
    ).then((result) => {
      setIsCreatingTag(false);

      if (result.status === "success") {
        dispatch(showNotification("Tag created successfully"));
        dispatch(objectTagsActions.fetchTagOptions());
        setNewTagName("");

        if (result.data && result.data.id) {
          setSelectedTagId(result.data.id);
        }
      } else {
        const errorMsg = result.message || "Failed to create tag";
        setTagError(errorMsg);
        dispatch(showNotification(errorMsg, "error"));
      }
    });
  };

  const handleAddTag = () => {
    if (!selectedTagId) return;

    setIsAddingTag(true);

    dispatch(
      objectTagsActions.addObjectTag({
        obj_id: source.id,
        objtagoption_id: selectedTagId,
      }),
    ).then((result) => {
      setIsAddingTag(false);
      if (result.status === "success") {
        dispatch(showNotification("Tag added successfully"));

        refreshSource();

        handleCloseDialog();
      } else {
        dispatch(showNotification("Failed to add tag", "error"));
      }
    });
  };

  const handleDeleteTag = (association_id) => {
    dispatch(objectTagsActions.deleteObjectTag({ id: association_id })).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Source Tag deleted"));

          refreshSource();
        } else {
          dispatch(showNotification("Failed to delete tag", "error"));
        }
      },
    );
  };

  const usedTagIds = (source.tags || []).map((tag) => tag.objtagoption_id);
  const availableTags = tagOptions.filter(
    (tag) => !usedTagIds.includes(tag.id),
  );

  return (
    <div className={styles.root}>
      <div className={styles.chips}>
        {(source.tags || []).map((tag) => (
          <Chip
            className={styles.chip}
            key={tag.id}
            label={tag.name}
            size="small"
            onDelete={() => handleDeleteTag(tag.id)}
            data-testid={`tag-chip-${tag.id}`}
          />
        ))}
      </div>

      <Tooltip title="Add Tag">
        <IconButton
          size="small"
          className={styles.addButton}
          onClick={handleOpenDialog}
          data-testid="add-tag-button"
        >
          <AddIcon fontSize="small" />
        </IconButton>
      </Tooltip>

      <Dialog
        open={open}
        onClose={handleCloseDialog}
        maxWidth="xs"
        fullWidth
        data-testid="add-tag-dialog"
      >
        <DialogTitle>Add Tag to {source.id}</DialogTitle>
        <DialogContent>
          <FormControl className={styles.selectFormControl}>
            <InputLabel id="tag-select-label">Select Tag</InputLabel>
            <Select
              labelId="tag-select-label"
              value={selectedTagId}
              onChange={handleTagChange}
              fullWidth
              data-testid="tag-select"
              disabled={availableTags.length === 0 && !permission}
            >
              {availableTags.length === 0 ? (
                <MenuItem value="" disabled>
                  No available tags to add
                </MenuItem>
              ) : (
                availableTags.map((option) => (
                  <MenuItem
                    key={option.id}
                    value={option.id}
                    data-testid={`tag-option-${option.id}`}
                  >
                    {option.name}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>

          {permission && (
            <>
              <Divider className={styles.divider} />

              <div className={styles.createTagSection}>
                <Typography variant="subtitle2" gutterBottom>
                  Create New Tag
                </Typography>

                <TextField
                  label="New Tag Name"
                  value={newTagName}
                  onChange={handleNewTagNameChange}
                  variant="outlined"
                  size="small"
                  className={styles.newTagField}
                  error={!!tagError}
                  helperText={
                    tagError ||
                    "Only letters and numbers, no spaces or special characters"
                  }
                  disabled={isCreatingTag}
                  inputProps={{
                    "data-testid": "new-tag-input",
                  }}
                />

                <Button
                  color="primary"
                  onClick={handleCreateTag}
                  disabled={!newTagName || isCreatingTag}
                  data-testid="create-tag-button"
                >
                  {isCreatingTag ? "Creating..." : "Create Tag"}
                  {isCreatingTag && (
                    <CircularProgress
                      size={16}
                      className={styles.loadingIcon}
                    />
                  )}
                </Button>
              </div>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} color="secondary">
            Cancel
          </Button>
          <Button
            onClick={handleAddTag}
            color="primary"
            disabled={!selectedTagId || isAddingTag}
            data-testid="save-tag-button"
          >
            {isAddingTag ? "Saving..." : "Save"}
            {isAddingTag && (
              <CircularProgress size={16} className={styles.loadingIcon} />
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

ObjectTags.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string.isRequired,
    tags: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
        objtagoption_id: PropTypes.number,
      }),
    ),
  }).isRequired,
};

export default ObjectTags;
