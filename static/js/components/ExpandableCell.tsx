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

type ExpandableCellProps = { maxVisible?: number } & (
  | { items: ReactNode[]; count?: never; render?: never }
  | {
      items?: never;
      count: number;
      render: (visible: number, collapsible: boolean) => ReactNode;
    }
);

const ExpandableCell = ({
  items,
  count = items?.length ?? 0,
  render = (visible) => items?.slice(0, visible),
  maxVisible = 3,
}: ExpandableCellProps) => {
  const { expandAll } = useContext(ExpandAllContext);
  const [override, setOverride] = useState<{
    expanded: boolean;
    expandAll: boolean;
  } | null>(null);
  const expanded =
    override?.expandAll === expandAll ? override.expanded : expandAll;

  return (
    <Box
      sx={
        items
          ? {
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: 0.5,
            }
          : { position: "relative" }
      }
    >
      {render(expanded ? count : maxVisible, count > maxVisible)}
      {count > maxVisible && (
        <IconButton
          size="small"
          aria-label={expanded ? "Show less" : "Show more"}
          sx={
            items
              ? {}
              : {
                  position: "absolute",
                  bottom: "0.5em",
                  left: "50%",
                  transform: "translateX(-50%)",
                  color: "grey.400",
                }
          }
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
