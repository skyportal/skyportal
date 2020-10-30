import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import Checkbox from "@material-ui/core/Checkbox";
import Button from "@material-ui/core/Button";
import ButtonGroup from "@material-ui/core/ButtonGroup";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import ArrowDropDownIcon from "@material-ui/icons/ArrowDropDown";
import ClickAwayListener from "@material-ui/core/ClickAwayListener";
import Grow from "@material-ui/core/Grow";
import Paper from "@material-ui/core/Paper";
import Popper from "@material-ui/core/Popper";
import MenuItem from "@material-ui/core/MenuItem";
import MenuList from "@material-ui/core/MenuList";
import { useForm, Controller } from "react-hook-form";

import * as sourceActions from "../ducks/source";
import FormValidationError from "./FormValidationError";

const SaveCandidateButton = ({ candidate, userGroups, filterGroups }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Dialog logic:

  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { handleSubmit, errors, reset, control, getValues } = useForm();

  useEffect(() => {
    reset({
      group_ids: userGroups.map((userGroup) =>
        filterGroups.map((g) => g.id).includes(userGroup.id)
      ),
    });
  }, [reset, userGroups, filterGroups, candidate]);

  const handleClickOpenDialog = () => {
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
  };

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.group_ids.filter((value) => Boolean(value)).length >= 1;
  };

  const onSubmitGroupSelectSave = async (data) => {
    setIsSubmitting(true);
    data.id = candidate.id;
    const groupIDs = userGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter((ID, idx) => data.group_ids[idx]);
    data.group_ids = selectedGroupIDs;
    const result = await dispatch(sourceActions.saveSource(data));
    if (result.status === "success") {
      reset();
      setDialogOpen(false);
    } else if (result.status === "error") {
      setIsSubmitting(false);
    }
  };

  // Split button logic (largely copied from
  // https://material-ui.com/components/button-group/#split-button):

  const filteredGroupNames = filterGroups
    .map((g) => {
      let name = g.nickname
        ? g.nickname.substring(0, 15)
        : g.name.substring(0, 15);
      if (name.length > 15) {
        name += "...";
      }
      return name;
    })
    .join(",");

  const options = [`Save to ${filteredGroupNames}`, "Select groups & save"];

  const [splitButtonMenuOpen, setSplitButtonMenuOpen] = useState(false);
  const anchorRef = useRef(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const handleClickMainButton = async () => {
    if (selectedIndex === 0) {
      setIsSubmitting(true);
      const data = {
        id: candidate.id,
        group_ids: candidate.passing_group_ids,
      };
      const result = await dispatch(sourceActions.saveSource(data));
      if (result.status === "error") {
        setIsSubmitting(false);
      }
    } else if (selectedIndex === 1) {
      handleClickOpenDialog();
    }
  };

  const handleMenuItemClick = (event, index) => {
    setSelectedIndex(index);
    setSplitButtonMenuOpen(false);
  };

  const handleToggleSplitButtonMenu = () => {
    setSplitButtonMenuOpen((prevOpen) => !prevOpen);
  };

  const handleCloseSplitButtonMenu = (event) => {
    if (anchorRef.current && anchorRef.current.contains(event.target)) {
      return;
    }
    setSplitButtonMenuOpen(false);
  };

  return (
    <div>
      <ButtonGroup
        variant="contained"
        ref={anchorRef}
        aria-label="split button"
      >
        <Button
          onClick={handleClickMainButton}
          name={`initialSaveCandidateButton${candidate.id}`}
          data-testid={`saveCandidateButton_${candidate.id}`}
          disabled={isSubmitting}
          size="small"
        >
          {options[selectedIndex]}
        </Button>
        <Button
          size="small"
          aria-controls={splitButtonMenuOpen ? "split-button-menu" : undefined}
          aria-expanded={splitButtonMenuOpen ? "true" : undefined}
          aria-label="Save as Source"
          aria-haspopup="menu"
          name={`saveCandidateButtonDropDownArrow${candidate.id}`}
          onClick={handleToggleSplitButtonMenu}
        >
          <ArrowDropDownIcon />
        </Button>
      </ButtonGroup>
      <Popper
        open={splitButtonMenuOpen}
        anchorEl={anchorRef.current}
        role={undefined}
        transition
        disablePortal
      >
        {({ TransitionProps, placement }) => (
          <Grow
            /* eslint-disable-next-line react/jsx-props-no-spreading */
            {...TransitionProps}
            style={{
              transformOrigin:
                placement === "bottom" ? "center top" : "center bottom",
            }}
          >
            <Paper>
              <ClickAwayListener onClickAway={handleCloseSplitButtonMenu}>
                <MenuList id="split-button-menu">
                  {options.map((option, index) => (
                    <MenuItem
                      key={option}
                      name={`buttonMenuOption${candidate.id}_${option}`}
                      selected={index === selectedIndex}
                      onClick={(event) => handleMenuItemClick(event, index)}
                    >
                      {option}
                    </MenuItem>
                  ))}
                </MenuList>
              </ClickAwayListener>
            </Paper>
          </Grow>
        )}
      </Popper>

      <Dialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Select one or more groups:</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(onSubmitGroupSelectSave)}>
            {errors.group_ids && (
              <FormValidationError message="Select at least one group." />
            )}
            {userGroups.map((userGroup, idx) => (
              <FormControlLabel
                key={userGroup.id}
                control={
                  <Controller
                    as={Checkbox}
                    name={`group_ids[${idx}]`}
                    control={control}
                    rules={{ validate: validateGroups }}
                  />
                }
                label={userGroup.name}
              />
            ))}
            <br />
            <div style={{ textAlign: "center" }}>
              <Button
                variant="contained"
                type="submit"
                name={`finalSaveCandidateButton${candidate.id}`}
              >
                Save
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};
SaveCandidateButton.propTypes = {
  candidate: PropTypes.shape({
    id: PropTypes.string,
    passing_group_ids: PropTypes.arrayOf(PropTypes.number),
  }).isRequired,
  userGroups: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      nickname: PropTypes.string,
    })
  ).isRequired,
  filterGroups: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      nickname: PropTypes.string,
    })
  ).isRequired,
};

export default SaveCandidateButton;
