import { useState, useEffect, useRef } from "react";
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

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";

import FormValidationError from "../FormValidationError";

import { useSaveAlertAsSourceMutation } from "../../ducks/boom_alert";
import { useLazyGetSourceQuery } from "../../ducks/source";
import { useGetGroupsQuery } from "../../ducks/groups";

interface SaveAlertButtonProps {
  alert: any;
  userGroups: any[];
}

const SaveAlertButton = ({ alert, userGroups }: SaveAlertButtonProps) => {
  const [saveAlertAsSource] = useSaveAlertAsSourceMutation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Dialog logic:

  const dispatch = useAppDispatch();
  const [triggerGetSource, getSourceResult] = useLazyGetSourceQuery();
  const [dialogOpen, setDialogOpen] = useState(false);
  // RTK Query: read results from the query hooks (no more redux slices).
  const source: any = getSourceResult.data;
  const groups = (useGetGroupsQuery().data?.all ?? []).filter(
    (g: any) => !g.single_user_group,
  );

  const currentGroupIds =
    source?.id === alert.id
      ? (source?.groups?.map((g: any) => g.id) ?? [])
      : [];
  const unsavedGroups = groups?.filter(
    (g: any) => !currentGroupIds.includes(g.id),
  );

  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();

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
    const formState: any = getValues();
    return (
      formState.group_ids.filter((value: any) => Boolean(value)).length >= 1
    );
  };

  const onSubmitGroupSelectSave = async (data: any) => {
    setIsSubmitting(true);
    data.id = alert.id;
    data.survey = alert.survey;
    const groupIDs = unsavedGroups.map((g: any) => g.id);
    const selectedGroupIDs = groupIDs.filter(
      (_ID: any, idx: number) => data.group_ids[idx],
    );

    data.payload = { candid: alert.candid, group_ids: selectedGroupIDs };

    let result: any;
    try {
      result = await saveAlertAsSource(data).unwrap();
    } catch {
      setIsSubmitting(false);
      return;
    }
    dispatch(
      showNotification("Source photometry updated successfully", "info"),
    );
    if (result?.used_latest_candid) {
      dispatch(
        showNotification(
          "Note that the latest alert packet was used to post thumbnails, as the provided candid didn't have any.",
          "warning",
        ),
      );
    }
    setIsSubmitting(false);
    setDialogOpen(false);
    reset();
    triggerGetSource(alert.id);
  };

  // Split button logic (largely copied from
  // https://material-ui.com/components/button-group/#split-button):

  const options = ["Select groups & save as a source"];
  // const options = ["Select groups & save as a source", "Select filters & save as a candidate"];

  const [splitButtonMenuOpen, setSplitButtonMenuOpen] = useState(false);
  const anchorRef = useRef<any>(null);
  const [anchorEl, setAnchorEl] = useState<any>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    setAnchorEl(anchorRef.current);
  }, []);

  const handleClickMainButton = async () => {
    if (selectedIndex === 0) {
      handleClickOpenDialog();
    }
  };

  const handleMenuItemClick = (_event: any, index: number) => {
    setSelectedIndex(index);
    setSplitButtonMenuOpen(false);
  };

  const handleToggleSplitButtonMenu = () => {
    setSplitButtonMenuOpen((prevOpen) => !prevOpen);
  };

  const handleCloseSplitButtonMenu = (event: any) => {
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
        anchorEl={anchorEl}
        role={undefined}
        transition
        disablePortal
        style={{ zIndex: 1000 }}
      >
        {({ TransitionProps, placement }) => (
          <Grow
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
                      {...({
                        name: `buttonMenuOption${alert.id}_${option}`,
                      } as any)}
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
            {errors["group_ids"] && (
              <FormValidationError message="Select at least one group." />
            )}
            {unsavedGroups.map((unsavedGroup: any, idx: number) => (
              <FormControlLabel
                key={unsavedGroup.id}
                control={
                  <Controller
                    name={`group_ids[${idx}]`}
                    control={control}
                    rules={{ validate: validateGroups }}
                    defaultValue={false}
                    render={({ field: { onChange, value } }) => (
                      <Checkbox
                        {...({ color: "primary", type: "checkbox" } as any)}
                        onChange={(event) => onChange(event.target.checked)}
                        checked={value}
                      />
                    )}
                  />
                }
                label={unsavedGroup.name}
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

export default SaveAlertButton;
