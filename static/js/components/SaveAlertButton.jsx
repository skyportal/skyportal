import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Checkbox from "@mui/material/Checkbox";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Grow from "@mui/material/Grow";
import Paper from "@mui/material/Paper";
import Popper from "@mui/material/Popper";
import MenuItem from "@mui/material/MenuItem";
import MenuList from "@mui/material/MenuList";
import { useForm, Controller } from "react-hook-form";

import * as alertActions from "../ducks/alert";
import * as sourceActions from "../ducks/source";
import FormValidationError from "./FormValidationError";

const SaveAlertButton = ({ alert, userGroups }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Dialog logic:

  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { handleSubmit, errors, reset, control, getValues } = useForm();

  useEffect(() => {
    reset({
      group_ids: [],
    });
  }, [reset, userGroups, alert]);

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
    data.id = alert.id;
    const groupIDs = userGroups.map((g) => g.id);
    const selectedGroupIDs = groupIDs.filter((ID, idx) => data.group_ids[idx]);

    data.payload = { candid: alert.candid, group_ids: selectedGroupIDs };

    const result = await dispatch(alertActions.saveAlertAsSource(data));
    if (result.status === "error") {
      setIsSubmitting(false);
    } else {
      setDialogOpen(false);
      reset();
      await dispatch(sourceActions.fetchSource(alert.id));
    }
  };

  // Split button logic (largely copied from
  // https://material-ui.com/components/button-group/#split-button):

  const options = ["Select groups & save as a source"];
  // const options = ["Select groups & save as a source", "Select filters & save as a candidate"];

  const [splitButtonMenuOpen, setSplitButtonMenuOpen] = useState(false);
  const anchorRef = useRef(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const handleClickMainButton = async () => {
    if (selectedIndex === 0) {
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
          name={`initialSaveAlertButton${alert.id}`}
          data-testid={`saveAlertButton_${alert.id}`}
          disabled={isSubmitting}
        >
          {options[selectedIndex]}
        </Button>
        <Button
          size="small"
          aria-controls={splitButtonMenuOpen ? "split-button-menu" : undefined}
          aria-expanded={splitButtonMenuOpen ? "true" : undefined}
          aria-label="Save as Source"
          aria-haspopup="menu"
          name={`saveAlertButtonDropDownArrow${alert.id}`}
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
        style={{ zIndex: 1000 }}
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
                      name={`buttonMenuOption${alert.id}_${option}`}
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
                    defaultValue={false}
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
                name={`finalSaveAlertButton${alert.id}`}
                disabled={isSubmitting}
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
SaveAlertButton.propTypes = {
  alert: PropTypes.shape({
    id: PropTypes.string,
    candid: PropTypes.number,
    group_ids: PropTypes.arrayOf(PropTypes.number),
  }).isRequired,
  userGroups: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    })
  ).isRequired,
};

export default SaveAlertButton;
