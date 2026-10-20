import { createContext, ReactNode, useContext, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import ExpandLess from "@mui/icons-material/ExpandLess";
import UnfoldMoreIcon from "@mui/icons-material/UnfoldMore";
import UnfoldLessIcon from "@mui/icons-material/UnfoldLess";

export const ExpandAllContext = createContext({
  expandAll: false,
  setExpandAll: (_expandAll: boolean) => {},
  expandedColumns: [] as string[],
  toggleColumn: (_column: string) => {},
});

export const ExpandAllProvider = ({ children }: { children: ReactNode }) => {
  const [expandAll, setExpandAll] = useState(false);
  const [expandedColumns, setExpandedColumns] = useState<string[]>([]);
  const value = useMemo(
    () => ({
      expandAll,
      setExpandAll,
      expandedColumns,
      toggleColumn: (column: string) =>
        setExpandedColumns((previous) =>
          previous.includes(column)
            ? previous.filter((c) => c !== column)
            : [...previous, column],
        ),
    }),
    [expandAll, expandedColumns],
  );
  return (
    <ExpandAllContext.Provider value={value}>
      {children}
    </ExpandAllContext.Provider>
  );
};

export const ExpandableColumnHeader = ({
  column,
  label,
}: {
  column: string;
  label: string;
}) => {
  const { expandedColumns, toggleColumn } = useContext(ExpandAllContext);
  const expanded = expandedColumns.includes(column);
  const action = expanded ? "Collapse all" : "Expand all";
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
      <Box component="span" sx={{ fontWeight: 500 }}>
        {label}
      </Box>
      <Tooltip title={`${action} ${label.toLowerCase()}`}>
        <IconButton
          size="small"
          aria-label={`${action} ${label.toLowerCase()}`}
          onClick={(event) => {
            event.stopPropagation();
            toggleColumn(column);
          }}
        >
          {expanded ? (
            <UnfoldLessIcon fontSize="small" />
          ) : (
            <UnfoldMoreIcon fontSize="small" />
          )}
        </IconButton>
      </Tooltip>
    </Box>
  );
};

type ExpandableCellProps = { maxVisible?: number; column?: string } & (
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
  column,
}: ExpandableCellProps) => {
  const context = useContext(ExpandAllContext);
  const expandAll =
    context.expandAll ||
    (column !== undefined && context.expandedColumns.includes(column));
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
