import { useState } from "react";
import type { MouseEvent } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Checkbox from "@mui/material/Checkbox";
import ButtonGroup from "@mui/material/ButtonGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Tooltip from "@mui/material/Tooltip";
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

const compactSx = {
  minWidth: 0,
  py: 0,
  px: 1.25,
  fontSize: "0.75rem",
  lineHeight: "1.5rem",
};

const SaveCandidateButton = ({
  candidate,
  userGroups,
  filterGroups,
}: SaveCandidateButtonProps) => {
  const dispatch = useAppDispatch();
  const [saveSource, { isLoading }] = useSaveSourceMutation();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);

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
    if (isLoading) return false;
    const { error } = await saveSource({ id: candidate.id, group_ids });
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

  const quickSave = filterGroups.length > 0;
  const groupName = (group: GroupOption) => group.nickname || group.name;
  const options = [
    ...(filterGroups.length > 1
      ? filterGroups.map((group) => ({
          label: `Save to ${groupName(group)} only`,
          onClick: () => save([group.id]),
        }))
      : []),
    { label: "Choose groups", onClick: () => setDialogOpen(true) },
  ];

  return (
    <>
      <ButtonGroup
        variant={quickSave ? "contained" : "outlined"}
        size="small"
        disableElevation
      >
        <Tooltip
          title={
            quickSave
              ? `Save to ${filterGroups.map(groupName).join(", ")}`
              : "Save to other groups"
          }
        >
          <Button
            onClick={() =>
              quickSave
                ? save(filterGroups.map((g) => g.id))
                : setDialogOpen(true)
            }
            name={`initialSaveCandidateButton${candidate.id}`}
            data-testid={`saveCandidateButton_${candidate.id}`}
            sx={compactSx}
          >
            Save
          </Button>
        </Tooltip>
        {quickSave && (
          <Button
            aria-haspopup="menu"
            aria-label="More save options"
            name={`saveCandidateButtonDropDownArrow${candidate.id}`}
            onClick={(event: MouseEvent<HTMLElement>) =>
              setMenuAnchor(event.currentTarget)
            }
            sx={{ ...compactSx, px: 0 }}
          >
            <ArrowDropDownIcon fontSize="small" />
          </Button>
        )}
      </ButtonGroup>
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={() => setMenuAnchor(null)}
      >
        {options.map(({ label, onClick }) => (
          <MenuItem
            key={label}
            dense
            {...{ name: `buttonMenuOption${candidate.id}_${label}` }}
            onClick={() => {
              setMenuAnchor(null);
              onClick();
            }}
          >
            {label}
          </MenuItem>
        ))}
      </Menu>

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
