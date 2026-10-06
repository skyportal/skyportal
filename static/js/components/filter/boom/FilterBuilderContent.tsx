import { useMemo, useState, useEffect, useCallback, useRef } from "react";
import {
  Alert,
  Button,
  Box,
  CircularProgress,
  Link,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Code as CodeIcon,
  ContentPaste as ContentPasteIcon,
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
import ImportPipelineDialog from "./dialog/ImportPipelineDialog";
import SaveVersionDialog from "./dialog/SaveVersionDialog";
import ConfirmDeletionDialog from "../../ConfirmDeletionDialog";
import { VersionSelect } from "./FilterVersionLabel";
import { shortFid } from "./filterVersions";
import PipelineViewer from "./dialog/PipelineViewer";
import MongoPipelineEditor from "./MongoPipelineEditor";
import { isRawMongoPipeline } from "./pipelineFormat";
import { decompilePipeline } from "../../../utils/mongoPipelineDecompiler";
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
  const { data: filter_v, refetch: refetchFilterVersion } =
    useBoomFilterVersion();
  const [updateGroupFilter, { isLoading: saving }] =
    useUpdateBoomGroupFilterMutation();
  const {
    data: store_schema,
    isError: schemaError,
    isFetching: schemaFetching,
    survey: resolvedSurvey,
  } = useFilterSchema(survey);
  // The broker has no filter schema for this survey (e.g. WINTER on BOOM): the
  // field/operator vocabularies are empty, so the block builder can't work.
  const schemaUnavailable =
    !!resolvedSurvey && !schemaFetching && (schemaError || !store_schema);

  const [, setSchema] = useState<any>(null);
  const [fieldOptions, setFieldOptions] = useState<any[]>([]);

  // Read-only viewer state for raw Mongo pipelines that can't be rendered as blocks.
  const [showPipeline, setShowPipeline] = useState(true);
  const [pipelineView, setPipelineView] = useState("complete");
  // True when the active version carries no block tree, so the builder is
  // showing the broker's pipeline rather than an imported raw filter.
  const [noBlockTree, setNoBlockTree] = useState(false);
  // "mongo" edits the pipeline as raw JSON instead of blocks.
  const [editorMode, setEditorMode] = useState<"blocks" | "mongo">("blocks");
  const [expandedStages, setExpandedStages] = useState<Set<any>>(new Set());
  const [importOpen, setImportOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [shownFid, setShownFid] = useState<string | null>(null);
  const [pendingShowFid, setPendingShowFid] = useState<string | null>(null);
  const [lastActiveFid, setLastActiveFid] = useState(filter?.active_fid);
  if (filter?.active_fid !== lastActiveFid) {
    setLastActiveFid(filter?.active_fid);
    if (!hasBeenModified) setShownFid(null);
    else if (shownFid === null) setShownFid(lastActiveFid);
  }
  const displayedFid: string | undefined = shownFid ?? filter?.active_fid;
  const handleStageToggle = useCallback((index: number) => {
    setExpandedStages((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

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
    if (
      displayedFid &&
      filter?.fv &&
      !filter.fv.some((version: any) => version.fid === displayedFid)
    ) {
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
    if (filter && filter.filters && displayedFid) {
      // This seems to be the original working structure
      const activeFilters = filter.filters.filter(
        (version: any) => version.fid === displayedFid,
      );

      if (activeFilters.length > 0 && activeFilters[0].version) {
        const versionData = activeFilters[0].version;

        if (versionData.filters) {
          setNoBlockTree(false);
          setEditorMode(
            isRawMongoPipeline(versionData.filters) ? "mongo" : "blocks",
          );
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

          setNoBlockTree(false);
          setEditorMode("blocks");
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
    if (filter && filter.fv && displayedFid) {
      const activeVersion = filter.fv.find(
        (version: any) => version.fid === displayedFid,
      );

      if (activeVersion && activeVersion.pipeline) {
        try {
          const pipelineData = JSON.parse(activeVersion.pipeline);
          // Reached only when no block tree was stored for the active version,
          // which is a different situation from a filter imported as a raw
          // pipeline even though both end up read-only.
          setNoBlockTree(true);
          setEditorMode("blocks");
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
    } else {
      setLocalFilterData(
        (prev: any) => prev ?? createEmptyFilterWithDefaultCondition(),
      );
    }
  }, [
    filter,
    displayedFid,
    setFilters,
    hasBeenModified,
    createEmptyFilterWithDefaultCondition,
    setCollapsedBlocks,
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

  // Imported filters arrive as a raw Mongo pipeline the block builder can't render.
  const rawPipeline = isRawMongoPipeline(filtersToRender)
    ? filtersToRender
    : null;
  const mongoMode = editorMode === "mongo";
  const queryReady = mongoMode ? !!rawPipeline : hasValidQuery();

  // The newest version that still has a block tree, so a version saved without
  // one does not dead-end the user.
  const lastEditableVersion = useMemo(() => {
    if (!noBlockTree) return null;
    const withTree = new Set(
      ((filter as any)?.filters || [])
        .filter((v: any) => v?.version?.filters || Array.isArray(v?.version))
        .map((v: any) => v.fid),
    );
    const candidates = ((filter as any)?.fv || []).filter((v: any) =>
      withTree.has(v.fid),
    );
    candidates.sort(
      (a: any, b: any) => (a.created_at || 0) - (b.created_at || 0),
    );
    return candidates.length ? candidates[candidates.length - 1] : null;
  }, [noBlockTree, filter]);
  const openVersion = (fid: string) => {
    setPendingShowFid(null);
    setHasBeenModified(false);
    setShownFid(fid === filter?.active_fid ? null : fid);
  };

  const requestOpenVersion = (fid: string) => {
    if (fid === displayedFid) return;
    if (hasBeenModified) setPendingShowFid(fid);
    else openVersion(fid);
  };

  const handleCopy = useCallback(() => {
    navigator.clipboard?.writeText(JSON.stringify(rawPipeline, null, 2));
  }, [rawPipeline]);
  const handleCopyStage = useCallback(
    (stageName: string, stageContent: any) => {
      navigator.clipboard?.writeText(
        JSON.stringify({ [stageName]: stageContent }, null, 2),
      );
    },
    [],
  );

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

  // Blocks left when switching to MongoDB, restored if the pipeline is unchanged.
  const blocksStash = useRef<any>(null);

  const handleEditorModeChange = (mode: "blocks" | "mongo" | null) => {
    if (!mode || mode === editorMode) return;
    setEditorMode(mode);
    if (mode === "mongo") {
      // An untouched builder still compiles to a bare $project; start empty.
      const pipeline =
        hasBeenModified && queryReady ? generateMongoQuery() : [];
      blocksStash.current = {
        filters: filtersToRender,
        projectionFields,
        pipeline: JSON.stringify(pipeline),
      };
      setProjectionFields?.([]);
      handleFilterUpdate(pipeline);
      return;
    }
    const stash = blocksStash.current;
    blocksStash.current = null;
    if (stash && stash.pipeline === JSON.stringify(rawPipeline ?? [])) {
      setProjectionFields?.(stash.projectionFields ?? []);
      handleFilterUpdate(stash.filters);
      return;
    }
    // The builder appends its own $project, so drop a trailing one first.
    const matchOnly =
      rawPipeline && "$project" in rawPipeline[rawPipeline.length - 1]
        ? rawPipeline.slice(0, -1)
        : rawPipeline;
    const tree = matchOnly ? decompilePipeline(matchOnly) : null;
    handleFilterUpdate(tree ?? createEmptyFilterWithDefaultCondition());
    if (rawPipeline && !tree) {
      dispatch(
        showNotification(
          "This pipeline can't be shown as blocks, so the builder starts empty.",
          "warning",
        ),
      );
    }
  };

  const handleImportPipeline = (pipeline: any[]) => {
    const tree = decompilePipeline(pipeline);
    setNoBlockTree(false);
    setProjectionFields?.([]);
    handleFilterUpdate(tree ?? pipeline);
    dispatch(
      tree
        ? showNotification(
            "Pipeline converted to blocks. Click Save to keep it as a new version.",
          )
        : showNotification(
            "This pipeline can't be shown as blocks, so it stays read-only. Click Save to keep it as a new version.",
            "warning",
          ),
    );
  };

  const handleSaveFilter = async (comment: string, setAsActive: boolean) => {
    const mongoQuery = generateMongoQuery();
    if (!mongoQuery || (Array.isArray(mongoQuery) && mongoQuery.length === 0)) {
      dispatch(showNotification("No valid MongoDB query to save", "error"));
      return false;
    }

    try {
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
        comment: comment || null,
        set_as_active: setAsActive,
      });
      if (!result.error) {
        dispatch(
          result.data?.switch_error
            ? showNotification(result.data.switch_error, "warning")
            : showNotification(
                result.data?.pending_switch
                  ? "Version saved. The filter switches to it once it passes validation."
                  : "Filter saved to boom database!",
              ),
        );
        setHasBeenModified(false);
        setShownFid(result.data?.fid ?? null);
        refetchFilterVersion();
        setShowAnnotationBuilder?.(false);
        setSaveOpen(false);
        return true;
      }
    } catch (err) {
      console.error("Error saving filter:", err);
      const errorMessage =
        (err as any)?.message ||
        "Failed to save filter to boom database. Please try again.";
      dispatch(showNotification(errorMessage, "error"));
    }
    return false;
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
        position: "relative",
        height: "100%",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 2,
          mb: 2,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Typography variant="h6">Filter Builder</Typography>
          {filter && !filter.fv?.length && (
            <ToggleButtonGroup
              exclusive
              size="small"
              value={editorMode}
              onChange={(_, mode) => handleEditorModeChange(mode)}
            >
              <ToggleButton value="blocks">Filter UI</ToggleButton>
              <ToggleButton value="mongo">MongoDB</ToggleButton>
            </ToggleButtonGroup>
          )}
          {filter?.fv?.length > 0 && (
            <VersionSelect
              label="Version shown"
              value={displayedFid}
              versions={filter.fv}
              altdata={filter.altdata}
              activeFid={filter.active_fid}
              showActiveState
              minWidth="18rem"
              onChange={requestOpenVersion}
            />
          )}
        </Box>
        <Box sx={{ display: "flex", gap: 2 }}>
          <Tooltip
            describeChild
            title="Save the whole filter as a new version. It does not run on live alerts until that version is validated and activated."
          >
            <span>
              <Button
                type="button"
                data-testid="tour-filter-save"
                variant="contained"
                startIcon={
                  saving ? <CircularProgress size={16} /> : <SaveIcon />
                }
                onClick={() => setSaveOpen(true)}
                disabled={
                  saving || !queryReady || (!!rawPipeline && !hasBeenModified)
                }
              >
                {saving ? "Saving…" : "Save"}
              </Button>
            </span>
          </Tooltip>
          <Tooltip
            describeChild
            title={
              rawPipeline || mongoMode
                ? "Annotations can only be added to a filter built with blocks."
                : "Choose the values attached as annotations to each alert that passes this filter. They are saved with the filter when you click Save."
            }
          >
            <span>
              <Button
                type="button"
                variant="outlined"
                startIcon={<NoteIcon />}
                onClick={handleAddAnnotations}
                disabled={!!rawPipeline || mongoMode}
                sx={{
                  "&:hover": {
                    backgroundColor: "secondary.50",
                    borderColor: "secondary.main",
                  },
                }}
              >
                Add Annotations
              </Button>
            </span>
          </Tooltip>
          {!mongoMode && (
            <Tooltip
              describeChild
              title="Paste a MongoDB aggregation pipeline to replace what the builder shows. It becomes blocks when possible and is only saved when you click Save."
            >
              <Button
                type="button"
                variant="outlined"
                startIcon={<ContentPasteIcon />}
                onClick={() => setImportOpen(true)}
              >
                Import JSON
              </Button>
            </Tooltip>
          )}
          <Tooltip
            describeChild
            title={
              queryReady
                ? "See the MongoDB pipeline built from these blocks and run it on past alerts to check which ones pass. Nothing is saved."
                : "Add at least one complete condition to test the filter."
            }
          >
            <span>
              <Button
                type="button"
                variant="outlined"
                startIcon={<CodeIcon />}
                onClick={handleShowMongoQuery}
                disabled={!queryReady}
                sx={{
                  borderColor: queryReady ? "primary.main" : undefined,
                  color: queryReady ? "primary.main" : undefined,
                  "&:hover": {
                    borderColor: queryReady ? "primary.dark" : undefined,
                    backgroundColor: queryReady ? "primary.50" : undefined,
                  },
                }}
              >
                Test/Preview filter output
              </Button>
            </span>
          </Tooltip>
        </Box>
      </Box>

      {/* Filter Blocks */}
      <Box data-testid="tour-filter-blocks">
        {mongoMode ? (
          <MongoPipelineEditor
            key={displayedFid ?? "new"}
            pipeline={rawPipeline}
            onChange={(pipeline) => handleFilterUpdate(pipeline ?? [])}
          />
        ) : schemaUnavailable ? (
          <Alert severity="warning">
            No filter schema is available for <strong>{resolvedSurvey}</strong>{" "}
            from this broker, so there are no fields to build conditions with.
            Filtering isn&apos;t supported for this survey yet.
          </Alert>
        ) : rawPipeline ? (
          <>
            <Alert severity="info" sx={{ mb: 2 }}>
              {noBlockTree ? (
                <>
                  This version was saved without the block builder&apos;s
                  representation of it, so only the pipeline it produced can be
                  shown here. The pipeline below is read-only.
                  {lastEditableVersion ? (
                    <>
                      {` Version ${shortFid(lastEditableVersion.fid)} is the most recent one that is still editable: `}
                      <Link
                        component="button"
                        variant="body2"
                        onClick={() =>
                          requestOpenVersion(lastEditableVersion.fid)
                        }
                        sx={{ verticalAlign: "baseline" }}
                      >
                        open it in the builder
                      </Link>
                      .
                    </>
                  ) : (
                    " Use Import JSON to replace it with a new version."
                  )}
                </>
              ) : (
                <>
                  This filter is a raw MongoDB pipeline that the block builder
                  can&apos;t show as blocks, so it&apos;s shown read-only below.
                  Use Import JSON to replace it with a new version.
                </>
              )}
            </Alert>
            <PipelineViewer
              pipeline={rawPipeline}
              showPipeline={showPipeline}
              setShowPipeline={setShowPipeline}
              pipelineView={pipelineView}
              setPipelineView={setPipelineView}
              expandedStages={expandedStages}
              handleStageToggle={handleStageToggle}
              handleCopy={handleCopy}
              handleCopyStage={handleCopyStage}
            />
          </>
        ) : filtersToRender && filtersToRender.length > 0 ? (
          filtersToRender.map((block: any, index: number) => {
            return (
              <BlockComponent
                key={block.id || index}
                block={block}
                parentBlockId={null}
                isRoot={index === 0}
                sentencePrefix="Keep alerts that"
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
      </Box>

      {/* Dialogs */}
      <AddVariableDialog />
      <AddListConditionDialog />
      <AddSwitchDialog />
      <SaveBlockDialogMenu />
      <MongoQueryDialog />
      <ImportPipelineDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImport={handleImportPipeline}
      />
      <ConfirmDeletionDialog
        dialogOpen={pendingShowFid !== null}
        closeDialog={() => setPendingShowFid(null)}
        deleteFunction={() => pendingShowFid && openVersion(pendingShowFid)}
        resourceName="unsaved changes"
        message="Opening another version discards the changes that are not saved yet."
      />
      <SaveVersionDialog
        open={saveOpen}
        saving={saving}
        filter={filter}
        onClose={() => setSaveOpen(false)}
        onSave={handleSaveFilter}
      />
    </Box>
  );
};

export default FilterBuilderContent;
