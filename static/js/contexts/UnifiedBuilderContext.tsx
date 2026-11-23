import React, { useState, createContext, useEffect } from "react";
import { useFilterManipulation, useFilterFactories } from "../hooks/useFilter";
import { useDialogStates } from "../hooks/useDialog";
import {
  useLazyGetFilterElementsQuery,
  useFilterSchema,
} from "../ducks/boom_filter_modules";
import { useBoomFilterVersion } from "../ducks/boom_filter";
import {
  convertToMongoAggregation,
  formatMongoAggregation,
  isValidPipeline,
} from "../utils/mongoPipelineBuilder";
import { compileFilterPipeline } from "../utils/compileFilterPipeline";
import { flattenFieldOptions } from "../constants/filterConstants";
import { isRawMongoPipeline } from "../components/filter/boom/pipelineFormat";

export const UnifiedBuilderContext = createContext<any>(undefined);

interface UnifiedBuilderProviderProps {
  children: React.ReactNode;
  mode?: string;
}

export const UnifiedBuilderProvider = ({
  children,
  mode = "filter",
}: UnifiedBuilderProviderProps) => {
  const [fetchAllElements] = useLazyGetFilterElementsQuery();

  // Core state
  const [filters, setFilters] = useState<any[]>([]);
  const [collapsedBlocks, setCollapsedBlocks] = useState<any>({});
  const [hasInitialized, setHasInitialized] = useState(false);

  // Local filter state management to persist across view changes
  const [localFilterData, setLocalFilterData] = useState<any>(null);
  const [hasBeenModified, setHasBeenModified] = useState(false);

  // Projection fields state (primarily for annotations)
  const [projectionFields, setProjectionFields] = useState<any[]>([]);

  // Custom data state
  const [customBlocks, setCustomBlocks] = useState<any[]>([]);
  const [customVariables, setCustomVariables] = useState<any[]>([]);
  const [customListVariables, setCustomListVariables] = useState<any[]>([]);
  const [customSwitchCases, setCustomSwitchCases] = useState<any[]>([]);
  const [catalogLoaded, setCatalogLoaded] = useState(false);
  const [catalogNames, setCatalogNames] = useState<string[]>([]);

  // Local filters updater function reference (for FilterBuilderContent)
  const [localFiltersUpdater, setLocalFiltersUpdater] = useState<any>(null);

  const { data: store_schema } = useFilterSchema();

  const [schema, setSchema] = useState<any>(null);
  const [fieldOptions, setFieldOptions] = useState<any[]>([]);

  useEffect(() => {
    if (store_schema) {
      setSchema(store_schema);
      setFieldOptions(flattenFieldOptions(store_schema));
    }
  }, [store_schema]);

  const { data: boomFilterVersion } = useBoomFilterVersion();
  const currentStream = boomFilterVersion?.stream?.name;

  // Load saved data on mount (similar to useFilterBuilderData)
  useEffect(() => {
    const loadData = async () => {
      setCatalogLoaded(false);
      try {
        // Load all saved data in parallel using the same pattern as FilterBuilderData
        const blocks: any = await fetchAllElements({ elements: "blocks" });
        const variables: any = await fetchAllElements({
          elements: "variables",
        });
        const listVariables: any = await fetchAllElements({
          elements: "listVariables",
        });
        const switchCases: any = await fetchAllElements({
          elements: "switchCases",
        });

        // Filter variables by stream - only show variables matching current stream or with no stream set
        // If no current stream is set, show all variables
        const filterByStream = (items: any) => {
          if (!items) return [];
          if (!currentStream) return items; // Show all variables if no current stream
          const streamName = currentStream.split(" ")[0];
          return items.filter(
            (item: any) =>
              !item.streams ||
              item.streams.length === 0 ||
              item.streams.includes(streamName),
          );
        };

        setCatalogNames(
          [
            variables.data.variables,
            listVariables.data.listVariables,
            switchCases.data.switchCases,
          ].flatMap((items: any) => (items || []).map((v: any) => v.name)),
        );
        setCustomBlocks(filterByStream(blocks.data.blocks));
        setCustomVariables(filterByStream(variables.data.variables));
        setCustomListVariables(
          filterByStream(listVariables.data.listVariables),
        );
        setCustomSwitchCases(filterByStream(switchCases.data.switchCases));
      } catch (error) {
        console.error("Error loading unified builder data:", error);
        // Set empty arrays as fallback
        setCustomBlocks([]);
        setCustomVariables([]);
        setCustomListVariables([]);
        setCustomSwitchCases([]);
      }
      setCatalogLoaded(true);
    };

    loadData();
  }, [fetchAllElements, mode, currentStream]);

  const currentData = filters;
  const setCurrentData = setFilters;

  // Get hook functionalities
  const dataManipulation = useFilterManipulation(currentData, setCurrentData);
  const factories = useFilterFactories();
  const dialogs = useDialogStates();

  const generateMongoQuery = () =>
    compileFilterPipeline({
      filters,
      projectionFields,
      schema,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
    });

  const getFormattedMongoQuery = () => {
    const pipeline = generateMongoQuery();
    return formatMongoAggregation(pipeline);
  };

  const hasValidQuery = () => {
    // Use localFilterData if it exists and has been modified, otherwise use filters
    const dataToCheck =
      hasBeenModified && localFilterData ? localFilterData : filters;
    // Already a raw pipeline (active in boom); no need to re-run the
    // block-tree validator over it.
    if (isRawMongoPipeline(dataToCheck)) {
      return true;
    }
    const pipeline = convertToMongoAggregation(
      dataToCheck,
      schema,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
      [], // No annotation fields for validation
      false, // Not in annotation mode for validation
    );
    return isValidPipeline(pipeline);
  };

  const value = {
    mode,
    schema,
    fieldOptions,

    filters: currentData,
    setFilters: setCurrentData,
    collapsedBlocks,
    setCollapsedBlocks,
    hasInitialized,
    setHasInitialized,

    // Local filter state management
    localFilterData,
    setLocalFilterData,
    hasBeenModified,
    setHasBeenModified,

    // Projection fields state
    projectionFields,
    setProjectionFields,

    // Custom data
    customBlocks,
    setCustomBlocks,
    customVariables,
    setCustomVariables,
    customListVariables,
    setCustomListVariables,
    customSwitchCases,
    setCustomSwitchCases,
    catalogLoaded,
    catalogNames,

    // Local filters updater (for filter mode)
    localFiltersUpdater,
    setLocalFiltersUpdater,

    // Spread hook functionalities
    ...dataManipulation,
    ...factories,
    ...dialogs,

    // MongoDB aggregation functions
    generateMongoQuery,
    getFormattedMongoQuery,
    hasValidQuery,
  };

  return (
    <UnifiedBuilderContext.Provider value={value}>
      {children}
    </UnifiedBuilderContext.Provider>
  );
};
