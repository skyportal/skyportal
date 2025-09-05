import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DeleteIcon from "@mui/icons-material/Delete";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import * as sourceActions from "../../ducks/source";

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
  aliasItem: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    borderRadius: "0px",
    position: "relative",
    lineHeight: 1,
    "&:hover $deleteButton": {
      opacity: 1,
    },
  },
  deleteButton: {
    opacity: 0,
    transition: "opacity 0.2s",
  },
}));

const SourceAlias = ({ source }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [alias, setAlias] = useState(null);

  const [hovering, setHovering] = useState(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(source?.alias?.includes(alias));
  }, [source, setInvalid, alias]);

  const handleChange = (e) => {
    setAlias(e.target.value);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    const newState = {};
    newState.alias = [...(source.alias || []), alias];

    const result = await dispatch(
      sourceActions.updateSource(source.id, {
        ...newState,
      }),
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Source alias successfully updated."));
      setDialogOpen(false);
    }
  };

  const handleDelete = async (aliasToDelete) => {
    setIsSubmitting(true);
    const newAliasList = (source.alias || []).filter(
      (a) => a !== aliasToDelete,
    );
    const uniqueAliasList = [...new Set(newAliasList)];

    const result = await dispatch(
      sourceActions.updateSource(source.id, {
        alias: newAliasList,
      }),
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Source alias removed successfully."));
    }
  };

  const handleHover = () => {
    setHovering(true);
  };

  const handleStopHover = () => {
    // here we only trigger if we stopped hovering the currently hovered item
    setHovering(null);
  };

  return (
    <>
      <div
        onMouseEnter={() => handleHover()}
        onMouseLeave={() => handleStopHover()}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "0px",
            gap: "0px",
            alignItems: "center",
          }}
        >
          <b>Aliases: &nbsp;</b>
          {(source.alias || []).map((a, idx) => (
            <div key={idx} className={classes.aliasItem}>
              <span>{a}</span>
              <IconButton
                size="small"
                onClick={() => handleDelete(a)}
                className={classes.deleteButton}
                data-testid={`deleteAlias-${a}`}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </div>
          ))}
          {hovering && (
            <IconButton
              data-testid="updateAliasIconButton"
              onClick={() => {
                setDialogOpen(true);
              }}
              size="small"
            >
              <EditIcon size="small" className={classes.editIcon} />
            </IconButton>
          )}
        </div>
      </div>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Add Alias</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a new alias" />
            )}
            <TextField
              data-testid="addAliasTextfield"
              size="small"
              label="alias"
              name="alias"
              onChange={handleChange}
              type="string"
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => {
                handleSubmit();
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="addAliasSubmitButton"
              disabled={isSubmitting || invalid}
            >
              Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

SourceAlias.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    alias: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
};

export default SourceAlias;
