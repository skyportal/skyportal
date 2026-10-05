import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import {
  Box,
  Button,
  Select,
  MenuItem,
  Chip,
  IconButton,
  InputBase,
  Tooltip,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import AddIcon from "@mui/icons-material/Add";
import ClearIcon from "@mui/icons-material/Clear";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import { blockHeaderStyles } from "../../../../styles/componentStyles";
import { useFilterBuilder } from "../../../../hooks/useContexts";
import SaveBlockComponent from "./SaveBlockComponent";
import { mapBlock } from "./blockTree";

const InlineSelect = ({
  value,
  onChange,
  options,
  label,
  onOpen,
}: {
  value: string;
  onChange: (value: string) => void;
  options: [string, string][];
  label: string;
  onOpen?: () => void;
}) => (
  <Select
    value={value}
    onChange={(e: any) => onChange(e.target.value)}
    onOpen={onOpen}
    input={<InputBase />}
    inputProps={{ "aria-label": label }}
    sx={{
      fontSize: "0.875rem",
      fontWeight: 600,
      color: "primary.main",
      bgcolor: (theme) => alpha(theme.palette.primary.main, 0.08),
      borderRadius: 1,
      "& .MuiSelect-select": { py: 0.25, pl: 1 },
    }}
  >
    {options.map(([optionValue, optionLabel]) => (
      <MenuItem key={optionValue} value={optionValue}>
        {optionLabel}
      </MenuItem>
    ))}
  </Select>
);

interface BlockHeaderProps {
  block: any;
  parentBlockId?: string | null;
  isRoot: boolean;
  blockState: {
    customBlockName?: string | null;
    isCollapsed?: boolean;
    isCustomBlock?: boolean;
  };
  localFilters?: any[] | null;
  setLocalFilters?: ((...a: any[]) => void) | null;
  isStickyHeader?: boolean;
  sentencePrefix?: string | undefined;
}

const BlockHeader = ({
  block,
  parentBlockId,
  isRoot,
  blockState: { customBlockName, isCollapsed, isCustomBlock },
  localFilters = null,
  setLocalFilters = null,
  isStickyHeader = false,
  sentencePrefix,
}: BlockHeaderProps) => {
  const {
    filters: contextFilters,
    setFilters: contextSetFilters,
    setCollapsedBlocks,
    setSaveDialog,
    setSaveName,
    setSaveError,
    createDefaultCondition,
    customBlocks,
    updateBlockLogic,
    removeBlock,
  } = useFilterBuilder();

  // Use local filters if provided, otherwise use context filters
  const filters = localFilters || contextFilters;
  const setFilters = setLocalFilters || contextSetFilters;

  // Keyboard shortcut to add a condition
  useEffect(() => {
    const handleKeyDown = (e: any) => {
      const isShortcut = e.metaKey && e.shiftKey && e.key === "C";

      if (!isShortcut) return;

      // Prevent default browser behavior
      e.preventDefault();
      e.stopPropagation();

      // Add a condition to this block
      const defaultCondition = createDefaultCondition();
      setFilters((prevFilters: any[]) => {
        return prevFilters.map((rootBlock: any) => {
          const updateBlock = (currentBlock: any): any => {
            if (currentBlock.id === block.id) {
              return {
                ...currentBlock,
                children: [...currentBlock.children, defaultCondition],
              };
            }
            if (currentBlock.children) {
              return {
                ...currentBlock,
                children: currentBlock.children.map((child: any) =>
                  child.category === "block" ? updateBlock(child) : child,
                ),
              };
            }
            return currentBlock;
          };
          return updateBlock(rootBlock);
        });
      });
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [block.id, createDefaultCondition, setFilters]);

  // Create a wrapper for removeBlock that works with both local and context filters
  const handleRemoveBlock = (blockId: string) => {
    if (localFilters && setLocalFilters) {
      // Use local filter handling
      if (parentBlockId === null) return;

      const updatedFilters = localFilters.map((currentBlock: any) => {
        const removeBlockFromTree = (blockToUpdate: any): any => {
          if (blockToUpdate.id !== parentBlockId) {
            return {
              ...blockToUpdate,
              children: blockToUpdate.children.map((child: any) =>
                child.category === "block" ? removeBlockFromTree(child) : child,
              ),
            };
          }
          return {
            ...blockToUpdate,
            children: blockToUpdate.children.filter(
              (child: any) => child.id !== blockId,
            ),
          };
        };
        return removeBlockFromTree(currentBlock);
      });
      setLocalFilters(updatedFilters);
    } else {
      // Use context removeBlock function
      removeBlock(blockId, parentBlockId);
    }
  };

  const resetBlockToOriginal = (blockId: string) => {
    // Find the custom block - need to match with or without "Custom." prefix
    const customBlock = customBlocks.find(
      (cb: any) =>
        cb.name === customBlockName ||
        cb.name === `Custom.${customBlockName}` ||
        cb.name.replace(/^Custom\./, "") === customBlockName,
    );
    if (!customBlock) {
      console.error("Custom block not found:", customBlockName);
      return;
    }

    // Collect all nested block IDs that will be created
    const nestedBlockIds: string[] = [];

    // Deep clone the original block, but keep the current block id and parent linkage
    const cloneWithId = (b: any, newId: string, isTopLevel = true): any => {
      const { ...rest } = b;
      const clonedBlock = {
        ...rest,
        id: newId,
        createdAt: Date.now(),
        children: b.children
          ? b.children.map((child: any) =>
              child.category === "block"
                ? cloneWithId(child, uuidv4(), false) // Pass false for nested blocks
                : { ...child, id: uuidv4() },
            )
          : [],
        // Only set customBlockName on the top level block, preserve existing names for nested blocks
        customBlockName: isTopLevel ? customBlockName : b.customBlockName,
        // Preserve isTrue for root custom blocks
        isTrue: isTopLevel ? true : b.isTrue,
      };

      // If this is a nested block, add its ID to the list for collapsing
      if (clonedBlock.category === "block" && !isTopLevel) {
        nestedBlockIds.push(clonedBlock.id);
      }

      return clonedBlock;
    };

    setFilters((prevFilters: any[]) => {
      const updateBlock = (b: any): any => {
        if (b.id !== blockId) {
          return {
            ...b,
            children: b.children.map((child: any) =>
              child.category === "block" ? updateBlock(child) : child,
            ),
          };
        }
        // Replace block with original, but keep the same id
        const original = cloneWithId(customBlock.block, blockId, true);
        return { ...original };
      };
      return prevFilters.map(updateBlock);
    });

    // Set all nested blocks as collapsed
    if (nestedBlockIds.length > 0) {
      setCollapsedBlocks((prev: any) => {
        const newCollapsed = { ...prev };
        nestedBlockIds.forEach((id: string) => {
          newCollapsed[id] = true;
        });
        return newCollapsed;
      });
    }
  };

  // Deep comparison function that ignores metadata fields and key order
  const deepCompareBlocks = (block1: any, block2: any) => {
    // Add validation to ensure we're comparing compatible blocks
    if (!block1 || !block2) {
      return block1 === block2;
    }

    // Check if both blocks have the same basic structure
    if (block1.category !== block2.category) {
      return false;
    }

    // Helper function to create a copy without metadata fields
    const stripMetadata = (obj: any): any => {
      if (obj === null || obj === undefined) return obj;
      if (Array.isArray(obj)) {
        return obj.map(stripMetadata);
      }
      if (typeof obj === "object") {
        const {
          id,
          createdAt,
          customBlockName: _customBlockName,
          isTrue,
          booleanSwitch,
          blockValue,
          ...rest
        } = obj;
        const stripped: Record<string, any> = {};
        for (const [key, value] of Object.entries(rest)) {
          stripped[key] = stripMetadata(value);
        }
        return stripped;
      }
      return obj;
    };

    // Deep equality comparison that ignores key order
    const deepEqual = (obj1: any, obj2: any): boolean => {
      if (obj1 === obj2) return true;
      if (obj1 == null || obj2 == null) return obj1 === obj2;

      // Handle string vs number comparison for values
      // (e.g., "123" should equal 123 for condition values)
      if (typeof obj1 === "string" && typeof obj2 === "number") {
        const num = parseFloat(obj1);
        return !isNaN(num) && num === obj2;
      }
      if (typeof obj1 === "number" && typeof obj2 === "string") {
        const num = parseFloat(obj2);
        return !isNaN(num) && num === obj1;
      }

      if (typeof obj1 !== typeof obj2) return false;
      if (typeof obj1 !== "object") return obj1 === obj2;
      if (Array.isArray(obj1) !== Array.isArray(obj2)) return false;

      if (Array.isArray(obj1)) {
        if (obj1.length !== obj2.length) return false;
        for (let i = 0; i < obj1.length; i++) {
          if (!deepEqual(obj1[i], obj2[i])) return false;
        }
        return true;
      }

      const keys1 = Object.keys(obj1);
      const keys2 = Object.keys(obj2);

      if (keys1.length !== keys2.length) return false;

      for (const key of keys1) {
        if (!keys2.includes(key)) return false;
        if (!deepEqual(obj1[key], obj2[key])) return false;
      }

      return true;
    };

    return deepEqual(stripMetadata(block1), stripMetadata(block2));
  };

  const normalizeCustomBlockName = (name: any) => {
    if (!name || typeof name !== "string") {
      return "";
    }
    return name.replace(/^Custom\./, "").trim();
  };

  const findCustomBlockDefinition = (name: any) => {
    const normalizedName = normalizeCustomBlockName(name);
    if (!normalizedName) {
      return null;
    }

    const match = customBlocks.find(
      (cb: any) => normalizeCustomBlockName(cb.name) === normalizedName,
    );

    return match?.block || null;
  };

  const isBlockEdited = (b: any, isNestedCustomBlock = false): boolean => {
    const isTopLevelCustomBlock = "isTrue" in b && b.customBlockName;
    const hasCustomBlockName = !!b.customBlockName;

    if (!isTopLevelCustomBlock && !isNestedCustomBlock) {
      return false;
    }

    if (!hasCustomBlockName) {
      return false;
    }

    const originalDefinition = findCustomBlockDefinition(b.customBlockName);
    if (!originalDefinition) {
      return false;
    }

    const coreContentMatches = deepCompareBlocks(b, originalDefinition);

    if (coreContentMatches) {
      return false;
    }

    let comparisonTarget = originalDefinition;

    if (isNestedCustomBlock) {
      comparisonTarget = { ...originalDefinition };
      delete comparisonTarget.isTrue;

      if (deepCompareBlocks(b, comparisonTarget)) {
        return false;
      }
    }

    const isCurrentBlockModified = !deepCompareBlocks(b, comparisonTarget);

    if (isCurrentBlockModified) {
      return true;
    }

    const hasModifiedChildren = checkChildrenForModifications(
      b,
      comparisonTarget,
    );

    return hasModifiedChildren;
  };

  const checkChildrenForModifications = (
    currentBlock: any,
    originalBlock: any,
  ): boolean => {
    const currentChildren = currentBlock?.children || [];
    const originalChildren = originalBlock?.children || [];

    if (currentChildren.length === 0) {
      return false;
    }

    if (currentChildren.length !== originalChildren.length) {
      return true;
    }

    for (let i = 0; i < currentChildren.length; i++) {
      const currentChild = currentChildren[i];
      const originalChild = originalChildren[i];

      if (currentChild?.category !== originalChild?.category) {
        return true;
      }

      if (currentChild.category === "block") {
        const currentName = normalizeCustomBlockName(
          currentChild.customBlockName,
        );
        const originalName = normalizeCustomBlockName(
          originalChild?.customBlockName,
        );

        if (currentName) {
          if (originalName && currentName !== originalName) {
            return true;
          }

          if (isBlockEdited(currentChild, true)) {
            return true;
          }
        } else {
          if (originalName) {
            return true;
          }

          if (
            !originalChild ||
            !deepCompareBlocks(currentChild, originalChild)
          ) {
            return true;
          }

          if (checkChildrenForModifications(currentChild, originalChild)) {
            return true;
          }
        }
      } else {
        if (!originalChild || !deepCompareBlocks(currentChild, originalChild)) {
          return true;
        }
      }
    }

    return false;
  };

  const handleToggleIsTrue = (checked: boolean) => {
    setFilters((prevFilters: any[]) => {
      const updateBlock = (b: any): any => {
        if (b.id !== block.id) {
          return {
            ...b,
            children: b.children
              ? b.children.map((child: any) =>
                  child.category === "block" ? updateBlock(child) : child,
                )
              : [],
          };
        }
        return { ...b, isTrue: checked };
      };
      return prevFilters.map(updateBlock);
    });
  };

  const [operatorTipOpen, setOperatorTipOpen] = useState(false);

  const handleAddCondition = () =>
    setFilters(
      mapBlock(filters, block.id, (current) => ({
        ...current,
        children: [...current.children, createDefaultCondition()],
      })),
    );

  const handleOperatorChange = (value: string) => {
    if (!localFilters || !setLocalFilters) {
      updateBlockLogic(block.id, `$${value}`);
      return;
    }
    setLocalFilters(
      mapBlock(localFilters, block.id, (current) => ({
        ...current,
        operator: `$${value}`,
        logic: value,
      })),
    );
  };

  const prefix = isRoot ? sentencePrefix : undefined;
  const isRootCustomBlock = "isTrue" in block && isCustomBlock;
  const edited = isBlockEdited(block) && isRootCustomBlock;
  const showContent = !(isRootCustomBlock && isCollapsed);
  const operator = (block?.operator || block?.logic || "$and")
    .replace("$", "")
    .toLowerCase();

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        position: isStickyHeader ? "sticky" : "relative",
        top: isStickyHeader ? 0 : "auto",
        zIndex: isStickyHeader ? 3 : "auto",
        backgroundColor: isStickyHeader ? "background.paper" : "transparent",
        borderRadius: isStickyHeader ? "8px 8px 0 0" : "0",
        p: isStickyHeader ? 2 : 1,
        mx: isStickyHeader ? -2 : 0,
        mt: isStickyHeader ? -2 : 0,
        mb: isStickyHeader ? 1 : 0,
        border: isStickyHeader ? 1 : 0,
        borderColor: isStickyHeader ? "grey.300" : "transparent",
        justifyContent: "space-between",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          flexWrap: "wrap",
          minWidth: 0,
        }}
      >
        {!isRoot && (
          <>
            <Button
              size="small"
              onClick={() =>
                setCollapsedBlocks((prev: any) => ({
                  ...prev,
                  [block.id]: !prev[block.id],
                }))
              }
              style={blockHeaderStyles.collapseButton}
            >
              {isCollapsed ? <ExpandMoreIcon /> : <ExpandLessIcon />}
            </Button>
            <IconButton
              size="small"
              color="error"
              onClick={() => handleRemoveBlock(block.id)}
              sx={{ p: 0.5 }}
            >
              <ClearIcon fontSize="small" />
            </IconButton>
          </>
        )}
        {isRootCustomBlock && (
          <>
            <Chip
              size="small"
              label={customBlockName}
              onClick={
                edited ? () => resetBlockToOriginal(block.id) : undefined
              }
              title={edited ? "Click to reset to original values" : undefined}
              sx={{
                fontWeight: 600,
                cursor: edited ? "pointer" : "default",
                bgcolor: edited ? "warning.light" : "info.light",
                color: edited ? "warning.contrastText" : "primary.contrastText",
              }}
            />
            {edited && (
              <Box
                component="span"
                sx={{ ...blockHeaderStyles.editedIndicator }}
              >
                (edited)
              </Box>
            )}
          </>
        )}
        {prefix && (
          <Typography variant="body2" color="text.secondary">
            {prefix}
          </Typography>
        )}
        <InlineSelect
          label="Whether alerts must match this block"
          value={block?.isTrue !== false ? "match" : "not"}
          onChange={(value) => handleToggleIsTrue(value === "match")}
          options={[
            ["match", prefix ? "match" : "Match"],
            ["not", prefix ? "don't match" : "Don't match"],
          ]}
        />
        {showContent && (
          <>
            <Tooltip
              placement="top"
              open={operatorTipOpen}
              onOpen={() => setOperatorTipOpen(true)}
              onClose={() => setOperatorTipOpen(false)}
              title={isRoot ? "all = AND, any = OR" : ""}
            >
              <Box data-testid="tour-filter-operator">
                <InlineSelect
                  label="How many conditions must match"
                  value={operator}
                  onChange={handleOperatorChange}
                  onOpen={() => setOperatorTipOpen(false)}
                  options={[
                    ["and", "all"],
                    ["or", "any"],
                  ]}
                />
              </Box>
            </Tooltip>
            <Typography variant="body2" color="text.secondary">
              of these conditions
            </Typography>
            <Tooltip title="Add a condition">
              <Button
                data-testid="tour-filter-add"
                variant="contained"
                size="small"
                endIcon={<AddIcon />}
                onClick={handleAddCondition}
                sx={{ ml: 1, py: 0, minWidth: 0 }}
              >
                Add
              </Button>
            </Tooltip>
          </>
        )}
      </Box>

      <SaveBlockComponent
        setSaveDialog={setSaveDialog}
        setSaveName={setSaveName}
        setSaveError={setSaveError}
        setFilters={setFilters}
        isCustomBlock={isCustomBlock}
        isCollapsed={isCollapsed}
        block={block}
      />
    </Box>
  );
};

export default BlockHeader;
