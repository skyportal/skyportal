import { ReactNode, useState } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import ExpandLess from "@mui/icons-material/ExpandLess";

interface ExpandableCellProps {
  items: ReactNode[];
  maxVisible?: number;
}

const ExpandableCell = ({ items, maxVisible = 3 }: ExpandableCellProps) => {
  const [expanded, setExpanded] = useState(false);
  return (
    <Box
      sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}
    >
      {expanded ? items : items.slice(0, maxVisible)}
      {items.length > maxVisible && (
        <IconButton
          size="small"
          aria-label={expanded ? "Show less" : "Show more"}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? (
            <ExpandLess fontSize="small" />
          ) : (
            <MoreHorizIcon fontSize="small" />
          )}
        </IconButton>
      )}
    </Box>
  );
};

export default ExpandableCell;
