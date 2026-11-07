import { useState } from "react";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import EditIcon from "@mui/icons-material/Edit";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useUpdateSourceGroupsMutation } from "../../ducks/source";

interface GroupOption {
  id: number;
  name?: string;
}

interface EditSourceGroupsProps {
  source: {
    id?: string;
    currentGroupIds: number[];
  };
  groups: GroupOption[];
  icon?: boolean;
}

interface GroupChecklistProps {
  title: string;
  groups: GroupOption[];
  selected: number[];
  onToggle: (id: number) => void;
  testIdPrefix: string;
  requestIds?: Set<number>;
  children?: React.ReactNode;
}

const byName = (a: GroupOption, b: GroupOption) =>
  (a.name ?? "").localeCompare(b.name ?? "", undefined, {
    sensitivity: "base",
  });

const GroupChecklist = ({
  title,
  groups,
  selected,
  onToggle,
  testIdPrefix,
  requestIds,
  children,
}: GroupChecklistProps) => (
  <Box>
    <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
      {title}
    </Typography>
    <Box sx={{ columnWidth: "15rem", columnGap: 2 }}>
      {groups.map((group) => (
        <FormControlLabel
          key={group.id}
          sx={{ display: "flex", breakInside: "avoid", mr: 0 }}
          control={
            <Checkbox
              size="small"
              checked={selected.includes(group.id)}
              onChange={() => onToggle(group.id)}
              data-testid={`${testIdPrefix}_${group.id}`}
            />
          }
          label={
            <>
              {group.name}
              {requestIds?.has(group.id) && (
                <Typography
                  component="span"
                  variant="caption"
                  color="text.secondary"
                  sx={{ ml: 1 }}
                >
                  request
                </Typography>
              )}
            </>
          }
        />
      ))}
    </Box>
    {children}
  </Box>
);

const EditSourceGroups = ({
  source,
  groups,
  icon = false,
}: EditSourceGroupsProps) => {
  const dispatch = useAppDispatch();
  const [updateSourceGroups, { isLoading }] = useUpdateSourceGroupsMutation();
  const { data: groupsData } = useGetGroupsQuery();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [toSave, setToSave] = useState<number[]>([]);
  const [toRemove, setToRemove] = useState<number[]>([]);

  const accessibleIds = new Set(
    (groupsData?.userAccessible ?? []).map((g) => g.id),
  );
  const matches = (group: GroupOption) =>
    (group.name ?? "").toLowerCase().includes(search.trim().toLowerCase());
  const unsavedGroups = groups
    .filter((g) => !source.currentGroupIds.includes(g.id))
    .sort(byName);
  const savedGroups = groups
    .filter((g) => source.currentGroupIds.includes(g.id))
    .sort(byName);
  const shownUnsaved = unsavedGroups.filter(matches);
  const shownSaved = savedGroups.filter(matches);
  const requestIds = new Set(
    unsavedGroups.filter((g) => !accessibleIds.has(g.id)).map((g) => g.id),
  );

  const toggle =
    (setIds: React.Dispatch<React.SetStateAction<number[]>>) => (id: number) =>
      setIds((ids) =>
        ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id],
      );

  const closeDialog = () => {
    setDialogOpen(false);
    setSearch("");
    setToSave([]);
    setToRemove([]);
  };

  const onSubmit = async () => {
    try {
      await updateSourceGroups({
        objId: source.id,
        inviteGroupIds: toSave,
        unsaveGroupIds: toRemove,
      }).unwrap();
      dispatch(showNotification("Source groups updated successfully", "info"));
      closeDialog();
    } catch {
      return;
    }
  };

  return (
    <>
      {icon ? (
        <Tooltip title="Manage source groups">
          <span>
            <IconButton
              aria-label="manage-groups"
              data-testid={`editGroups_${source.id}`}
              onClick={() => setDialogOpen(true)}
              size="small"
            >
              <EditIcon style={{ fontSize: "1rem" }} />
            </IconButton>
          </span>
        </Tooltip>
      ) : (
        <Button
          variant="outlined"
          color="primary"
          data-testid={`editGroups_${source.id}`}
          size="small"
          onClick={() => setDialogOpen(true)}
        >
          Save to
        </Button>
      )}

      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Groups</DialogTitle>
        <DialogContent
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <TextField
            label="Search"
            size="small"
            fullWidth
            autoFocus
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="searchGroupsInput"
            sx={{ mt: 1 }}
          />
          {shownUnsaved.length > 0 && (
            <GroupChecklist
              title="Save to"
              groups={shownUnsaved}
              selected={toSave}
              onToggle={toggle(setToSave)}
              testIdPrefix="inviteGroupCheckbox"
              requestIds={requestIds}
            />
          )}
          {shownSaved.length > 0 && (
            <GroupChecklist
              title="Remove from"
              groups={shownSaved}
              selected={toRemove}
              onToggle={toggle(setToRemove)}
              testIdPrefix="unsaveGroupCheckbox"
            >
              {toRemove.length > 0 && (
                <Typography variant="caption" color="warning.main">
                  Removed for all members of these groups.
                </Typography>
              )}
            </GroupChecklist>
          )}
          {shownUnsaved.length === 0 && shownSaved.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No group found.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>Cancel</Button>
          <Button
            primary
            name={`editSourceGroupsButton_${source.id}`}
            onClick={onSubmit}
            disabled={
              isLoading || (toSave.length === 0 && toRemove.length === 0)
            }
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default EditSourceGroups;
