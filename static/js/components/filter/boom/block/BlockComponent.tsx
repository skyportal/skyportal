import { useState, useMemo } from "react";
import { Paper, Box } from "@mui/material";
import {
  useFilterBuilder,
  useCurrentBuilder,
} from "../../../../hooks/useContexts";
import BlockHeader from "./BlockHeader";
import ConditionComponent from "../condition/ConditionComponent";

interface BlockComponentProps {
  [key: string]: any;
  block: any;
  parentBlockId?: string | null;
  isRoot?: boolean;
  fieldOptionsList?: any[];
  isListDialogOpen?: boolean;
  localFilters?: any[] | null;
  setLocalFilters?: ((...a: any[]) => void) | null;
  stickyBlockId?: string | null;
  disableSwitchOption?: boolean;
}

const useBlockState = (block: any, isRoot: boolean) => {
  const { collapsedBlocks } = useCurrentBuilder();

  const customBlockName = useMemo(() => {
    if (!block) return null;
    return block.customBlockName || null;
  }, [block]);

  const isCustomBlock = useMemo(() => !!customBlockName, [customBlockName]);

  const isCollapsed = useMemo(() => {
    if (!collapsedBlocks || !block?.id || isRoot) return false;
    return !!collapsedBlocks[block.id];
  }, [collapsedBlocks, block, isRoot]);

  return {
    customBlockName,
    isCustomBlock,
    isCollapsed,
  };
};

const BlockComponent = ({
  block,
  parentBlockId = null,
  isRoot = false,
  fieldOptionsList = [],
  isListDialogOpen = false,
  localFilters = null,
  setLocalFilters = null,
  stickyBlockId = null,
  disableSwitchOption = false,
}: BlockComponentProps) => {
  const [activeBlockForAdd, setActiveBlockForAdd] = useState<any>(null);

  const { setListConditionDialog } = useFilterBuilder();

  const blockState = useBlockState(block, isRoot);

  const renderChildren = useMemo(() => {
    if (blockState.isCollapsed || !block?.children?.length) return null;

    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {block.children.map((conditionOrBlock: any) => {
          // Early return with error handling
          if (!conditionOrBlock?.id) {
            console.warn("BlockComponent: child missing ID", conditionOrBlock);
            return null;
          }

          if (conditionOrBlock.category === "block") {
            return (
              <BlockComponent
                key={conditionOrBlock.id}
                block={conditionOrBlock}
                parentBlockId={block.id}
                isRoot={false}
                fieldOptionsList={fieldOptionsList}
                isListDialogOpen={isListDialogOpen}
                localFilters={localFilters}
                setLocalFilters={setLocalFilters}
                stickyBlockId={stickyBlockId}
                disableSwitchOption={disableSwitchOption}
              />
            );
          }

          return (
            <ConditionComponent
              key={conditionOrBlock.id}
              conditionOrBlock={conditionOrBlock}
              block={block}
              isListDialogOpen={isListDialogOpen}
              fieldOptionsList={fieldOptionsList}
              localFilters={localFilters}
              setLocalFilters={setLocalFilters}
              setListConditionDialog={setListConditionDialog}
            />
          );
        })}
      </Box>
    );
  }, [
    blockState.isCollapsed,
    block,
    fieldOptionsList,
    isListDialogOpen,
    localFilters,
    setLocalFilters,
    setListConditionDialog,
    stickyBlockId,
    disableSwitchOption,
  ]);

  if (!block?.id) {
    console.warn("BlockComponent: Invalid block provided", block);
    return null;
  }

  // Determine if this specific block should have a sticky header
  const isStickyHeader = block.id === stickyBlockId;

  // Block UI interaction state - no need to memoize simple object
  const uiState = {
    activeBlockForAdd,
    setActiveBlockForAdd,
  };

  return (
    <Paper
      component="section"
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: isStickyHeader ? 0 : blockState.isCollapsed ? 0 : 1,
        p: blockState.isCollapsed ? 1 : 2,
        pt: isStickyHeader ? 0 : blockState.isCollapsed ? 1 : 2,
        borderColor: "grey.300",
        borderRadius: 2,
      }}
      aria-label={`${block.category} block${
        blockState.customBlockName ? ` - ${blockState.customBlockName}` : ""
      }`}
    >
      {/* Block Header - can be sticky */}
      <BlockHeader
        block={block}
        parentBlockId={parentBlockId}
        isRoot={isRoot}
        blockState={blockState}
        uiState={uiState}
        localFilters={localFilters}
        setLocalFilters={setLocalFilters}
        isStickyHeader={isStickyHeader}
        disableSwitchOption={disableSwitchOption}
      />

      {/* Content */}
      <Box>{renderChildren}</Box>
    </Paper>
  );
};

// Custom comparison function for React.memo to ensure it re-renders when stickyBlockId changes
BlockComponent.displayName = "BlockComponent";

export default BlockComponent;
