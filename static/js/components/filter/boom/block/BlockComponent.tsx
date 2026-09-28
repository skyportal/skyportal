import { useState } from "react";
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
  const { collapsedBlocks } = useCurrentBuilder();

  if (!block?.id) return null;

  const customBlockName = block.customBlockName || null;
  const isCollapsed = !isRoot && !!collapsedBlocks?.[block.id];
  const isStickyHeader = block.id === stickyBlockId;
  const padding = isRoot && !isCollapsed ? 2 : 1;

  return (
    <Paper
      component="section"
      elevation={isRoot ? 1 : 0}
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: isStickyHeader || isCollapsed ? 0 : 1,
        p: padding,
        pt: isStickyHeader ? 0 : padding,
        borderRadius: 2,
        ...(!isRoot && {
          pr: 0,
          borderLeft: 3,
          borderColor: "primary.light",
          borderRadius: 0,
          backgroundColor: "transparent",
        }),
      }}
      aria-label={`${block.category} block${
        customBlockName ? ` - ${customBlockName}` : ""
      }`}
    >
      <BlockHeader
        block={block}
        parentBlockId={parentBlockId}
        isRoot={isRoot}
        blockState={{
          customBlockName,
          isCustomBlock: !!customBlockName,
          isCollapsed,
        }}
        uiState={{ activeBlockForAdd, setActiveBlockForAdd }}
        localFilters={localFilters}
        setLocalFilters={setLocalFilters}
        isStickyHeader={isStickyHeader}
        disableSwitchOption={disableSwitchOption}
      />
      {!isCollapsed && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {block.children
            ?.filter((child: any) => child?.id)
            .map((child: any) =>
              child.category === "block" ? (
                <BlockComponent
                  key={child.id}
                  block={child}
                  parentBlockId={block.id}
                  fieldOptionsList={fieldOptionsList}
                  isListDialogOpen={isListDialogOpen}
                  localFilters={localFilters}
                  setLocalFilters={setLocalFilters}
                  stickyBlockId={stickyBlockId}
                  disableSwitchOption={disableSwitchOption}
                />
              ) : (
                <ConditionComponent
                  key={child.id}
                  conditionOrBlock={child}
                  block={block}
                  isListDialogOpen={isListDialogOpen}
                  fieldOptionsList={fieldOptionsList}
                  localFilters={localFilters}
                  setLocalFilters={setLocalFilters}
                  setListConditionDialog={setListConditionDialog}
                />
              ),
            )}
        </Box>
      )}
    </Paper>
  );
};

export default BlockComponent;
