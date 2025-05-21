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
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Autocomplete from "@mui/material/Autocomplete";
import { Controller, useForm } from "react-hook-form";
import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import * as objectTagsActions from "../ducks/objectTags";

const useStyles = makeStyles((theme) => ({
  root: {
    margin: "0",
    padding: "0",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
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
  addButton: {
    height: "0.75rem",
    cursor: "pointer",
  },
  loadingIcon: {
    marginLeft: theme.spacing(1),
    fontSize: "0.875rem",
  },
  divider: {
    marginTop: theme.spacing(3),
    marginBottom: theme.spacing(2),
  },
  newTagField: {
    width: "100%",
  },
}));

const ObjectTags = ({ source }) => {
  const styles = useStyles();
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [selectedTag, setSelectedTag] = useState(null);
  const [isAddingTag, setIsAddingTag] = useState(false);
  const [newTagName, setNewTagName] = useState("");
  const [isCreatingTag, setIsCreatingTag] = useState(false);
  const [tagError, setTagError] = useState("");
  const tagOptions = useSelector((state) => state.objectTags || []);
  const currentUser = useSelector((state) => state.profile);
  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage sources");

  const { control, setValue, getValues } = useForm();

  useEffect(() => {
    dispatch(objectTagsActions.fetchTagOptions());
  }, [dispatch]);

  const handleOpenDialog = () => {
    setOpen(true);
    setNewTagName("");
    setSelectedTag(null);
    setValue("tag", null);
  };

  const handleCloseDialog = () => {
    setOpen(false);
    setSelectedTag(null);
    setValue("tag", null);
    setNewTagName("");
  };

  const handleNewTagNameChange = (event) => {
    setNewTagName(event.target.value);
    setTagError("");
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
        dispatch(objectTagsActions.fetchTagOptions()).then(() => {
          if (result.data) {
            setSelectedTag(result.data);
            setValue("tag", result.data);
          }
        });
        setNewTagName("");
      } else {
        const errorMsg = result.message || "Failed to create tag";
        setTagError(errorMsg);
        dispatch(showNotification(errorMsg, "error"));
      }
    });
  };

  const handleAddTag = () => {
    const formValues = getValues();
    const tagToAdd = formValues.tag;

    setIsAddingTag(true);

    dispatch(
      objectTagsActions.addObjectTag({
        obj_id: source.id,
        objtagoption_id: tagToAdd.id,
      }),
    ).then((result) => {
      setIsAddingTag(false);
      if (result.status === "success") {
        dispatch(showNotification("Tag added successfully"));
        dispatch(objectTagsActions.fetchObjectTags());
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
          dispatch(objectTagsActions.fetchObjectTags());
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
          {availableTags.length > 0 ? (
            <Controller
              name="tag"
              control={control}
              render={({ field: { onChange, value } }) => {
                return (
                  <Autocomplete
                    id="tagSelect"
                    options={availableTags}
                    getOptionLabel={(option) => option.name}
                    value={value}
                    onChange={(e, data) => {
                      onChange(data);
                      setSelectedTag(data);
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        variant="outlined"
                        label="Select Tag"
                        size="small"
                        className={styles.autocomplete}
                        data-testid="tag-autocomplete-input"
                      />
                    )}
                    filterSelectedOptions
                    data-testid="tag-select"
                  />
                );
              }}
            />
          ) : (
            <Typography variant="body2" color="textSecondary">
              No (more) available tags to add to this source.
            </Typography>
          )}

          {permission && (
            <>
              <Divider className={styles.divider} />

              <div className={styles.createTagSection}>
                <Typography variant="subtitle1" gutterBottom>
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
            disabled={!selectedTag || isAddingTag}
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
