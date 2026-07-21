import { useMemo, useState, useEffect, useCallback } from "react";
import { Button, Box, Typography } from "@mui/material";
import {
  Code as CodeIcon,
  Note as NoteIcon,
  Save as SaveIcon,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useAppDispatch } from "../../../types/hooks";
import { useFilterBuilder } from "../../../hooks/useContexts";
import { flattenFieldOptions } from "../../../constants/filterConstants";
import AddVariableDialog from "./dialog/AddVariableDialog";
import BlockComponent from "./block/BlockComponent";
import AddListConditionDialog from "./dialog/AddListConditionDialog";
import AddSwitchDialog from "./dialog/AddSwitchDialog";
import SaveBlockDialogMenu from "./block/SaveBlockDialogMenu";
import MongoQueryDialog from "./dialog/MongoQueryDialog";
import { filterBuilderStyles } from "../../../styles/componentStyles";
import { showNotification } from "baselayer/components/Notifications";

import {
  useBoomFilterVersion,
  useUpdateBoomGroupFilterMutation,
} from "../../../ducks/boom_filter";
import { useFilterSchema } from "../../../ducks/boom_filter_modules";

interface FilterBuilderContentProps {
  onToggleAnnotationBuilder?: (...a: any[]) => void;
  filter?: any;
  setInlineNewVersion?: (...a: any[]) => void;
  setShowAnnotationBuilder?: (...a: any[]) => void;
  // Survey override for callers without a filter version (Lasair query builder).
  survey?: string;
}

// Helper function to recursively collect all block IDs (excluding root blocks)
const collectAllBlockIds = (blocks: any, isRoot = true): any[] => {
  const blockIds: any[] = [];

  if (!blocks || !Array.isArray(blocks)) return blockIds;

  blocks.forEach((block: any) => {
    if (!block || block.category !== "block") return;

    // Don't collect root block IDs, only nested ones
    if (!isRoot && block.id) {
      blockIds.push(block.id);
    }

    // Recursively collect from children
    if (block.children && block.children.length > 0) {
      const childBlockIds = collectAllBlockIds(block.children, false);
      blockIds.push(...childBlockIds);
    }
  });

  return blockIds;
};

const FilterBuilderContent = ({
  onToggleAnnotationBuilder,
  filter,
  setInlineNewVersion,
  setShowAnnotationBuilder,
  survey,
}: FilterBuilderContentProps) => {
  const {
    setMongoDialog,
    hasValidQuery,
    collapsedBlocks,
    setCollapsedBlocks,
    generateMongoQuery,
    setFilters,
    setLocalFiltersUpdater,
    // Use context state for local filter management
    localFilterData,
    setLocalFilterData,
    hasBeenModified,
    setHasBeenModified,
    // Get the factory function for creating default conditions
    createDefaultCondition,
    projectionFields,
    setProjectionFields,
  } = useFilterBuilder();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { data: filter_v } = useBoomFilterVersion();
  const [updateGroupFilter] = useUpdateBoomGroupFilterMutation();
  const { data: store_schema } = useFilterSchema(survey);

  const [, setSchema] = useState<any>(null);
  const [fieldOptions, setFieldOptions] = useState<any[]>([]);

  // Helper function to create an empty filter with a default empty condition
  const createEmptyFilterWithDefaultCondition = useCallback(
    () => [
      {
        id: "root-block",
        category: "block",
        operator: "and",
        children: [createDefaultCondition()],
      },
    ],
    [createDefaultCondition],
  );

  // Initialize local filter data when filter prop changes
  useEffect(() => {
    // Don't override if user has already made modifications
    if (hasBeenModified) {
      return;
    }

    // Helper to collapse all blocks after loading filter data
    const collapseAllBlocks = (filterData: any) => {
      if (setCollapsedBlocks && filterData) {
        const allBlockIds = collectAllBlockIds(filterData);
        if (allBlockIds.length > 0) {
          setCollapsedBlocks((prev: any) => {
            const newCollapsed = { ...prev };
            allBlockIds.forEach((id: any) => {
              newCollapsed[id] = true;
            });
            return newCollapsed;
          });
        }
      }
    };

    // First, check if we have filter data in the expected structure
    if (filter && filter.filters && filter.active_fid) {
      // This seems to be the original working structure
      const activeFilters = filter.filters.filter(
        (version: any) => version.fid === filter.active_fid,
      );

      if (activeFilters.length > 0 && activeFilters[0].version) {
        const versionData = activeFilters[0].version;

        if (versionData.filters) {
          setLocalFilterData(versionData.filters);
          if (setFilters) {
            setFilters(versionData.filters);
          }
          // Restore projection fields if they exist
          if (versionData.projectionFields && setProjectionFields) {
            setProjectionFields(versionData.projectionFields);
          }
          // Collapse blocks after loading
          collapseAllBlocks(versionData.filters);
          return;
        }

        // Fallback: handle old format where version[0] contains filter data
        if (Array.isArray(versionData) && versionData[0]) {
          // Convert the original structure to editable format
          // Extract the actual filter blocks from version[0]
          const editableData = versionData;

          setLocalFilterData(editableData);
          if (setFilters) {
            setFilters(editableData);
          }
          // Collapse blocks after loading
          collapseAllBlocks(editableData);
          return;
        }
      }
    }

    // Fallback: try the pipeline structure
    if (filter && filter.fv && filter.active_fid) {
      const activeVersion = filter.fv.find(
        (version: any) => version.fid === filter.active_fid,
      );

      if (activeVersion && activeVersion.pipeline) {
        try {
          const pipelineData = JSON.parse(activeVersion.pipeline);
          setLocalFilterData(pipelineData);
          if (setFilters && pipelineData) {
            setFilters(pipelineData);
          }
          // Collapse blocks after loading
          collapseAllBlocks(pipelineData);
        } catch (error) {
          console.error("Error parsing pipeline data:", error);
          const emptyFilter = createEmptyFilterWithDefaultCondition();
          setLocalFilterData(emptyFilter);
          if (setFilters) {
            setFilters(emptyFilter);
          }
        }
      } else {
        const emptyFilter = createEmptyFilterWithDefaultCondition();
        setLocalFilterData(emptyFilter);
        if (setFilters) {
          setFilters(emptyFilter);
        }
      }
    } else if (!localFilterData) {
      const emptyFilter = createEmptyFilterWithDefaultCondition();
      setLocalFilterData(emptyFilter);
      if (setFilters) {
        setFilters(emptyFilter);
      }
    }
  }, [
    filter,
    setFilters,
    hasBeenModified,
    createEmptyFilterWithDefaultCondition,
    setCollapsedBlocks,
    localFilterData,
    setLocalFilterData,
    setProjectionFields,
  ]);

  // Update context filters when local filter data changes
  useEffect(() => {
    if (localFilterData && setFilters) {
      setFilters(localFilterData);
    }
  }, [localFilterData, setFilters]);

  useEffect(() => {
    if (store_schema) {
      setSchema(store_schema);
      setFieldOptions(flattenFieldOptions(store_schema));
    }
  }, [store_schema]);

  // Callback to handle filter updates from child components
  const handleFilterUpdate = useCallback(
    (updatedFilters: any) => {
      setHasBeenModified(true); // Mark as modified to prevent useEffect override
      setLocalFilterData(updatedFilters);
      // Also update the context immediately for MongoDB generation
      if (setFilters) {
        setFilters(updatedFilters);
      }
    },
    [setHasBeenModified, setLocalFilterData, setFilters],
  );

  // Set the local filters updater in the context so dialogs can access it
  useEffect(() => {
    if (setLocalFiltersUpdater) {
      setLocalFiltersUpdater(() => handleFilterUpdate);
    }
  }, [setLocalFiltersUpdater, handleFilterUpdate]);

  // Use local filter data or fallback to context filters
  const { filters: contextFilters } = useFilterBuilder();
  const filtersToRender = localFilterData || contextFilters;

  // Find the most nested non-collapsed block to make its header sticky
  // Use useMemo to ensure this recalculates when filters or collapsedBlocks change
  const getMostNestedNonCollapsedBlock = useMemo(() => {
    if (!filtersToRender || filtersToRender.length === 0)
      return { blockId: null, path: [] };

    // Recursively find the deepest non-collapsed block
    const findDeepest = (blocks: any, path: any[] = [], depth = 0): any => {
      let deepestBlock: any = { blockId: null, path: [], depth: -1 };

      for (let i = 0; i < blocks.length; i++) {
        const block = blocks[i];
        if (!block || !block.id || block.category !== "block") continue;

        const currentPath = [...path, i];
        // Root blocks (depth 0) are never collapsed, only nested blocks can be collapsed
        const isCollapsed = depth > 0 && collapsedBlocks?.[block.id] === true;

        if (!isCollapsed) {
          // This block is not collapsed, it's a candidate for sticky header
          if (depth >= deepestBlock.depth) {
            deepestBlock = { blockId: block.id, path: currentPath, depth };
          }

          // If this block has children blocks, recursively search them
          if (block.children && block.children.length > 0) {
            const childBlocks = block.children.filter(
              (child: any) => child?.category === "block",
            );
            if (childBlocks.length > 0) {
              const deepestChild = findDeepest(
                childBlocks,
                currentPath,
                depth + 1,
              );
              // Only update if we found a deeper block
              if (
                deepestChild.blockId &&
                deepestChild.depth > deepestBlock.depth
              ) {
                deepestBlock = deepestChild;
              }
            }
          }
        }
      }

      return deepestBlock;
    };

    const result = findDeepest(filtersToRender);
    return result;
  }, [filtersToRender, collapsedBlocks]);

  const handleShowMongoQuery = () => {
    setMongoDialog({ open: true });
  };

  const handleSaveFilter = async () => {
    const mongoQuery = generateMongoQuery();
    if (!mongoQuery || (Array.isArray(mongoQuery) && mongoQuery.length === 0)) {
      dispatch(showNotification("No valid MongoDB query to save", "error"));
      return;
    }

    try {
      // Use the current local filter data (which includes user modifications)
      const currentFilters =
        localFilterData || contextFilters || filtersToRender;

      const versionData = {
        filters: currentFilters,
        projectionFields: projectionFields || [],
      };

      const result: any = await updateGroupFilter({
        filter_id: filter.id,
        altdata: mongoQuery,
        filters: versionData,
        name: filter_v?.name,
      });
      dispatch(showNotification("Filter saved to boom database!"));
      if (!result.error) {
        if (setInlineNewVersion) {
          setInlineNewVersion(false);
        }
        if (setShowAnnotationBuilder) {
          setShowAnnotationBuilder(false);
        }
      }
    } catch (err) {
      console.error("Error saving filter:", err);
      const errorMessage =
        (err as any)?.message ||
        "Failed to save filter to boom database. Please try again.";
      dispatch(showNotification(errorMessage, "error"));
    }
  };

  const handleAddAnnotations = () => {
    if (onToggleAnnotationBuilder) {
      onToggleAnnotationBuilder();
    } else {
      navigate("/annotations");
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        ...filterBuilderStyles.container,
        // Ensure this container allows sticky positioning
        position: "relative",
        height: "100%",
      }}
    >
      {/* Header with buttons */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Typography variant="h2" sx={{ color: "text.primary" }}>
          Filter Builder
        </Typography>
        <Box sx={{ display: "flex", gap: 2 }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSaveFilter}
            disabled={!hasValidQuery()}
            sx={{
              backgroundColor: hasValidQuery() ? "primary.main" : undefined,
              "&:hover": {
                backgroundColor: hasValidQuery() ? "primary.dark" : undefined,
              },
            }}
          >
            Save
          </Button>
          <Button
            variant="outlined"
            startIcon={<NoteIcon />}
            onClick={handleAddAnnotations}
            sx={{
              "&:hover": {
                backgroundColor: "secondary.50",
                borderColor: "secondary.main",
              },
            }}
          >
            Add Annotations
          </Button>
          <Button
            variant="outlined"
            startIcon={<CodeIcon />}
            onClick={handleShowMongoQuery}
            disabled={!hasValidQuery()}
            sx={{
              borderColor: hasValidQuery() ? "primary.main" : undefined,
              color: hasValidQuery() ? "primary.main" : undefined,
              "&:hover": {
                borderColor: hasValidQuery() ? "primary.dark" : undefined,
                backgroundColor: hasValidQuery() ? "primary.50" : undefined,
              },
            }}
          >
            Test/Preview filter output
          </Button>
        </Box>
      </Box>

      {/* Filter Blocks */}
      {filtersToRender && filtersToRender.length > 0 ? (
        filtersToRender.map((block: any, index: number) => {
          return (
            <BlockComponent
              key={block.id || index}
              block={block}
              parentBlockId={null}
              isRoot={index === 0}
              fieldOptionsList={fieldOptions}
              stickyBlockId={getMostNestedNonCollapsedBlock.blockId}
              localFilters={filtersToRender}
              setLocalFilters={handleFilterUpdate}
            />
          );
        })
      ) : (
        <Typography variant="body2" color="text.secondary">
          No filter blocks to display. Add conditions to get started.
        </Typography>
      )}

      {/* Dialogs */}
      <AddVariableDialog />
      <AddListConditionDialog />
      <AddSwitchDialog />
      <SaveBlockDialogMenu />
      <MongoQueryDialog />
    </Box>
  );
};

export default FilterBuilderContent;
