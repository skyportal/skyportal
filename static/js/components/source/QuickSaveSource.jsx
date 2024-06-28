import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import SaveIcon from "@mui/icons-material/Save";
import { showNotification } from "baselayer/components/Notifications";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";

import * as sourceActions from "../../ducks/source";
import Button from "../Button";

const QuickSaveButton = ({ sourceId, alreadySavedGroups }) => {
  const dispatch = useDispatch();
  const profile = useSelector((state) => state.profile);
  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible,
  );
  const { hydratedList } = useSelector((state) => state.hydration);

  const [isSaving, setIsSaving] = useState(false);

  const alreadySavedGroupsSet = new Set(alreadySavedGroups);
  const quickSaveGroupsSet = new Set(
    profile?.preferences?.quicksave_group_ids || [],
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
    dispatch(sourceActions.saveSource(data)).then((response) => {
      if (response.status === "success") {
        dispatch(
          showNotification(
            `Source quick saved to ${quickSaveGroupsSet.size} group(s)`,
          ),
        );
        setIsSaving(false);
      } else {
        setIsSaving(false);
        dispatch(showNotification("Error saving source", "error"));
      }
    });
  };

  if (!(profile?.preferences?.quicksave_group_ids?.length > 0)) {
    return null;
  }

  // if quickSaveGroupsSet alreadySavedGroupsSet contains all elements of quickSaveGroupsSet, return null
  if (
    alreadySavedGroupsSet.size > 0 &&
    [...quickSaveGroupsSet].every((group) => alreadySavedGroupsSet.has(group))
  ) {
    return null;
  }

  const groupsLoaded =
    typeof hydratedList === "object" &&
    Array.isArray(hydratedList) &&
    hydratedList.includes("groups");

  if (userAccessibleGroups?.length === 0) {
    return null;
  }

  const tooltipText = !groupsLoaded
    ? "Loading..."
    : `Quick Save Source to: ${[...quickSaveGroupsSet]
        .map((groupId) => {
          const group = userAccessibleGroups.find((g) => g.id === groupId);
          return group.nickname || group.name;
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

QuickSaveButton.propTypes = {
  sourceId: PropTypes.string.isRequired,
  alreadySavedGroups: PropTypes.arrayOf(PropTypes.number),
};

QuickSaveButton.defaultProps = {
  alreadySavedGroups: [],
};

export default QuickSaveButton;
