import { Paper, Box } from "@mui/material";
import { alpha } from "@mui/material/styles";
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
  depth?: number;
  sentencePrefix?: string;
}

const NESTING_COLORS = [
  "primary",
  "secondary",
  "success",
  "warning",
  "info",
] as const;

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
  depth = 1,
  sentencePrefix,
}: BlockComponentProps) => {
  const { setListConditionDialog } = useFilterBuilder();
  const { collapsedBlocks } = useCurrentBuilder();

  if (!block?.id) return null;

  const customBlockName = block.customBlockName || null;
  const isCollapsed = !isRoot && !!collapsedBlocks?.[block.id];
  const isStickyHeader = block.id === stickyBlockId;
  const padding = isRoot && !isCollapsed ? 2 : 1;
  const nestingColor =
    NESTING_COLORS[(depth - 1) % NESTING_COLORS.length] ?? "primary";

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
          ml: 1.5,
          border: 1,
          borderColor: "divider",
          borderLeft: 4,
          borderLeftColor: `${nestingColor}.main`,
          borderRadius: 1,
          backgroundColor: (theme: any) =>
            alpha(theme.palette[nestingColor].main, 0.04),
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
        localFilters={localFilters}
        setLocalFilters={setLocalFilters}
        isStickyHeader={isStickyHeader}
        sentencePrefix={sentencePrefix}
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
                  depth={isRoot ? 1 : depth + 1}
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
                  disableSwitchOption={disableSwitchOption}
                />
              ),
            )}
        </Box>
      )}
    </Paper>
  );
};

export default BlockComponent;
