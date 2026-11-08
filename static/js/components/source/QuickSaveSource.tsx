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

interface QuickSaveButtonsProps {
  sourceId: string;
  alreadySavedGroups?: number[];
}

const QuickSaveButtons = ({
  sourceId,
  alreadySavedGroups = [],
}: QuickSaveButtonsProps) => {
  const dispatch = useAppDispatch();
  const [saveSource] = useSaveSourceMutation();
  const { data: profile } = useGetProfileQuery();
  const { data: groupsData } = useGetGroupsQuery();
  const userAccessibleGroups = groupsData?.userAccessible ?? [];

  const [savingButton, setSavingButton] = useState<string | null>(null);

  const quickSaveButtons: Record<string, number[]> =
    (profile?.preferences as any)?.quickSaveButtons ?? {};
  const buttons = Object.entries(quickSaveButtons)
    .map(
      ([name, groupIds]) =>
        [
          name,
          userAccessibleGroups.filter(
            (group) =>
              groupIds.includes(group.id) &&
              !alreadySavedGroups.includes(group.id),
          ),
        ] as const,
    )
    .filter(([, groups]) => groups.length > 0);

  if (buttons.length === 0) {
    return null;
  }

  const quickSave = (name: string, groupIds: number[]) => {
    setSavingButton(name);
    saveSource({ id: sourceId, group_ids: groupIds })
      .unwrap()
      .then(() => {
        dispatch(
          showNotification(`Source quick saved to ${groupIds.length} group(s)`),
        );
      })
      .catch(() => {
        dispatch(showNotification("Error saving source", "error"));
      })
      .finally(() => setSavingButton(null));
  };

  return (
    <>
      {buttons.map(([name, groups]) => (
        <Tooltip
          key={name}
          title={`Save to ${groups.map((g) => g["nickname"] || g.name).join(", ")}`}
        >
          <span>
            <Button
              variant="contained"
              color="primary"
              size="small"
              onClick={() =>
                quickSave(
                  name,
                  groups.map((g) => g.id),
                )
              }
              disabled={savingButton !== null}
              endIcon={
                savingButton === name ? (
                  <CircularProgress size="1rem" />
                ) : (
                  <SaveIcon />
                )
              }
            >
              {name}
            </Button>
          </span>
        </Tooltip>
      ))}
    </>
  );
};

export default QuickSaveButtons;
