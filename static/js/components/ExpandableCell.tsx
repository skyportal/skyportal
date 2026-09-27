import { createContext, ReactNode, useContext, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import ExpandLess from "@mui/icons-material/ExpandLess";

export const ExpandAllContext = createContext({
  expandAll: false,
  setExpandAll: (_expandAll: boolean) => {},
});

export const ExpandAllProvider = ({ children }: { children: ReactNode }) => {
  const [expandAll, setExpandAll] = useState(false);
  const value = useMemo(() => ({ expandAll, setExpandAll }), [expandAll]);
  return (
    <ExpandAllContext.Provider value={value}>
      {children}
    </ExpandAllContext.Provider>
  );
};

interface ExpandableCellProps {
  items: ReactNode[];
  maxVisible?: number;
}

const ExpandableCell = ({ items, maxVisible = 3 }: ExpandableCellProps) => {
  const { expandAll } = useContext(ExpandAllContext);
  const [override, setOverride] = useState<{
    expanded: boolean;
    expandAll: boolean;
  } | null>(null);
  const expanded =
    override?.expandAll === expandAll ? override.expanded : expandAll;

  return (
    <Box
      sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}
    >
      {expanded ? items : items.slice(0, maxVisible)}
      {items.length > maxVisible && (
        <IconButton
          size="small"
          aria-label={expanded ? "Show less" : "Show more"}
          onClick={() => setOverride({ expanded: !expanded, expandAll })}
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
