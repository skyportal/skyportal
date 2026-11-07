import { useState } from "react";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

import type { Group } from "../../types/domain";

interface SavedGroupChipsProps {
  groups: Group[];
  max: number;
}

const SavedGroupChips = ({ groups, max }: SavedGroupChipsProps) => {
  const [expanded, setExpanded] = useState(false);
  const hiddenCount = groups.length - max;
  return (
    <>
      {(expanded ? groups : groups.slice(0, max)).map((group) => {
        const chip = (
          <Chip
            key={group.id}
            size="small"
            label={(group.nickname || group.name).substring(0, 15)}
            data-testid={`groupChip_${group.id}`}
          />
        );
        return group.saved_at ? (
          <Tooltip
            key={group.id}
            title={`Saved at ${group.saved_at} by ${group.saved_by?.username}`}
          >
            {chip}
          </Tooltip>
        ) : (
          chip
        );
      })}
      {hiddenCount > 0 && (
        <Chip
          size="small"
          variant="outlined"
          color="primary"
          label={expanded ? "Show less" : `+${hiddenCount} more`}
          onClick={() => setExpanded(!expanded)}
        />
      )}
    </>
  );
};

export default SavedGroupChips;
