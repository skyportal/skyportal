import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Checkbox from "@mui/material/Checkbox";
import ButtonGroup from "@mui/material/ButtonGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Grow from "@mui/material/Grow";
import Paper from "@mui/material/Paper";
import Popper from "@mui/material/Popper";
import MenuItem from "@mui/material/MenuItem";
import MenuList from "@mui/material/MenuList";
import { Controller, useForm } from "react-hook-form";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";

import { useSaveSourceMutation } from "../../ducks/source";
import FormValidationError from "../FormValidationError";

interface GroupOption {
  id: number;
  name: string;
  nickname?: string | null;
}

interface SaveCandidateButtonProps {
  candidate: {
    id?: string;
    passing_group_ids?: number[];
  };
  userGroups: GroupOption[];
  filterGroups: GroupOption[];
}

const SaveCandidateButton = ({
  candidate,
  userGroups,
  filterGroups,
}: SaveCandidateButtonProps) => {
  const dispatch = useAppDispatch();
  const [saveSource, { isLoading }] = useSaveSourceMutation();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<HTMLDivElement | null>(null);

  const {
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm({
    values: {
      group_ids: userGroups.map((group) =>
        filterGroups.some((g) => g.id === group.id),
      ),
    },
  });

  const save = async (group_ids: number[]) => {
    const { error } = await saveSource({
      id: candidate.id,
      group_ids,
      refresh_source: false,
    });
    if (error) return false;
    const names = group_ids.flatMap(
      (id) => userGroups.find((g) => g.id === id)?.name ?? [],
    );
    dispatch(
      showNotification(
        `Candidate successfully saved to group${
          names.length > 1 ? "s" : ""
        }: ${names.join()}.`,
      ),
    );
    return true;
  };

  const onSubmit = handleSubmit(async ({ group_ids }) => {
    const selected = userGroups.filter((_, i) => group_ids[i]);
    if (await save(selected.map((g) => g.id))) {
      reset();
      setDialogOpen(false);
    }
  });

  const groupNames =
    filterGroups.length <= 3
      ? filterGroups.map((g) => (g.nickname || g.name).slice(0, 15)).join(", ")
      : "selected groups";
  const saveToFilterGroups = {
    label: `Save to ${groupNames}`,
    onClick: () => save(filterGroups.map((g) => g.id)),
  };
  const options = [
    saveToFilterGroups,
    { label: "Select groups & save", onClick: () => setDialogOpen(true) },
    ...(filterGroups.length > 1
      ? filterGroups.map((group) => ({
          label: `Save to ${group.nickname || group.name} only`,
          onClick: () => save([group.id]),
        }))
      : []),
  ];

  return (
    <>
      <ButtonGroup
        variant="contained"
        ref={setAnchorEl}
        aria-label="split button"
      >
        <Button
          onClick={saveToFilterGroups.onClick}
          name={`initialSaveCandidateButton${candidate.id}`}
          data-testid={`saveCandidateButton_${candidate.id}`}
          disabled={isLoading}
          size="small"
        >
          {saveToFilterGroups.label}
        </Button>
        <Button
          size="small"
          aria-controls={menuOpen ? "split-button-menu" : undefined}
          aria-expanded={menuOpen ? "true" : undefined}
          aria-label="Save as Source"
          aria-haspopup="menu"
          name={`saveCandidateButtonDropDownArrow${candidate.id}`}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <ArrowDropDownIcon />
        </Button>
      </ButtonGroup>
      <Popper
        open={menuOpen}
        anchorEl={anchorEl}
        role={undefined}
        transition
        disablePortal
        sx={{ zIndex: 1 }}
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
              <ClickAwayListener
                onClickAway={(event) => {
                  if (!anchorEl?.contains(event.target as Node)) {
                    setMenuOpen(false);
                  }
                }}
              >
                <MenuList id="split-button-menu">
                  {options.map(({ label, onClick }) => (
                    <MenuItem
                      key={label}
                      {...{ name: `buttonMenuOption${candidate.id}_${label}` }}
                      onClick={onClick}
                    >
                      {label}
                    </MenuItem>
                  ))}
                </MenuList>
              </ClickAwayListener>
            </Paper>
          </Grow>
        )}
      </Popper>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Select one or more groups:</DialogTitle>
        <DialogContent>
          <form onSubmit={onSubmit}>
            {errors.group_ids && (
              <FormValidationError message="Select at least one group." />
            )}
            {userGroups.map((userGroup, idx) => (
              <FormControlLabel
                key={userGroup.id}
                label={userGroup.name}
                control={
                  <Controller
                    name={`group_ids.${idx}`}
                    control={control}
                    rules={{
                      validate: (_, { group_ids }) => group_ids.some(Boolean),
                    }}
                    render={({ field: { onChange, value } }) => (
                      <Checkbox
                        checked={value}
                        onChange={(_, checked) => onChange(checked)}
                        data-testid={`saveCandGroupCheckbox-${userGroup.id}`}
                      />
                    )}
                  />
                }
              />
            ))}
            <Button
              secondary
              type="submit"
              name={`finalSaveCandidateButton${candidate.id}`}
              sx={{ display: "flex", mx: "auto" }}
            >
              Save
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default SaveCandidateButton;
