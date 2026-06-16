import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useState } from "react";

import SaveIcon from "@mui/icons-material/Save";
import { showNotification } from "baselayer/components/Notifications";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";

import { useAppDispatch } from "../../types/hooks";
import { useSaveSourceMutation } from "../../ducks/source";
import Button from "../Button";

interface QuickSaveButtonProps {
  sourceId: string;
  alreadySavedGroups?: number[];
}

const QuickSaveButton = ({
  sourceId,
  alreadySavedGroups = [],
}: QuickSaveButtonProps) => {
  const dispatch = useAppDispatch();
  const [saveSource] = useSaveSourceMutation();
  const { data: profile } = useGetProfileQuery();
  const { data: groupsData, isSuccess: groupsLoaded } = useGetGroupsQuery();
  const userAccessibleGroups = groupsData?.userAccessible ?? [];

  const [isSaving, setIsSaving] = useState(false);

  const alreadySavedGroupsSet = new Set(alreadySavedGroups);
  const quickSaveGroupsSet = new Set<number>(
    (profile?.preferences as any)?.quicksave_group_ids || [],
  );

  const quickSaveSource = () => {
    setIsSaving(true);
    const saveGroups = [...quickSaveGroupsSet].filter(
      (x) => !alreadySavedGroupsSet.has(x),
    );
    const data = {
      id: sourceId,
      group_ids: saveGroups,
    };
    saveSource(data)
      .unwrap()
      .then(() => {
        dispatch(
          showNotification(
            `Source quick saved to ${quickSaveGroupsSet.size} group(s)`,
          ),
        );
        setIsSaving(false);
      })
      .catch(() => {
        setIsSaving(false);
        dispatch(showNotification("Error saving source", "error"));
      });
  };

  if (!((profile?.preferences as any)?.quicksave_group_ids?.length > 0)) {
    return null;
  }

  // if quickSaveGroupsSet alreadySavedGroupsSet contains all elements of quickSaveGroupsSet, return null
  if (
    alreadySavedGroupsSet.size > 0 &&
    [...quickSaveGroupsSet].every((group) => alreadySavedGroupsSet.has(group))
  ) {
    return null;
  }

  if (userAccessibleGroups?.length === 0) {
    return null;
  }

  const tooltipText = !groupsLoaded
    ? "Loading..."
    : `Quick Save Source to: ${[...quickSaveGroupsSet]
        .map((groupId) => {
          const group = userAccessibleGroups.find((g) => g.id === groupId);
          return group?.["nickname"] || group?.name;
        })
        .join(", ")}`;

  return (
    <Tooltip title={tooltipText}>
      <span>
        <Button
          variant="contained"
          color="primary"
          size="small"
          onClick={quickSaveSource}
          disabled={isSaving || !groupsLoaded}
          endIcon={
            isSaving || !groupsLoaded ? (
              <CircularProgress size="1rem" />
            ) : (
              <SaveIcon />
            )
          }
        >
          {groupsLoaded ? "Quick Save" : "Loading..."}
        </Button>
      </span>
    </Tooltip>
  );
};

export default QuickSaveButton;
