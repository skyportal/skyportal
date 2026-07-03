import React, { useState, createContext, useEffect } from "react";
import { useFilterManipulation, useFilterFactories } from "../hooks/useFilter";
import { useDialogStates } from "../hooks/useDialog";
import { fetchAllElements } from "../ducks/boom_filter_modules";
import {
  convertToMongoAggregation,
  formatMongoAggregation,
  isValidPipeline,
  convertArithmeticExpression,
} from "../utils/mongoPipelineBuilder";
import { flattenFieldOptions } from "../constants/filterConstants";
import { useAppDispatch, useAppSelector } from "../types/hooks";

export const UnifiedBuilderContext = createContext<any>(undefined);

interface UnifiedBuilderProviderProps {
  children: React.ReactNode;
  mode?: string;
}

export const UnifiedBuilderProvider = ({
  children,
  mode = "filter",
}: UnifiedBuilderProviderProps) => {
  const dispatch = useAppDispatch();

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

  // Local filters updater function reference (for FilterBuilderContent)
  const [localFiltersUpdater, setLocalFiltersUpdater] = useState<any>(null);

  const store_schema = useAppSelector(
    (state) => (state as any).filter_modules?.schema,
  );

  const [schema, setSchema] = useState<any>(null);
  const [fieldOptions, setFieldOptions] = useState<any[]>([]);

  useEffect(() => {
    if (store_schema) {
      setSchema(store_schema);
      setFieldOptions(flattenFieldOptions(store_schema));
    }
  }, [store_schema]);

  const currentStream = useAppSelector(
    (state) => (state as any).boom_filter_v.stream?.name,
  );

  // Load saved data on mount (similar to useFilterBuilderData)
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load all saved data in parallel using the same pattern as FilterBuilderData
        const blocks: any = await dispatch(
          fetchAllElements({ elements: "blocks" }),
        );
        const variables: any = await dispatch(
          fetchAllElements({ elements: "variables" }),
        );
        const listVariables: any = await dispatch(
          fetchAllElements({ elements: "listVariables" }),
        );
        const switchCases: any = await dispatch(
          fetchAllElements({ elements: "switchCases" }),
        );

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
    };

    loadData();
  }, [dispatch, mode, currentStream]);

  const currentData = filters;
  const setCurrentData = setFilters;

  // Get hook functionalities
  const dataManipulation = useFilterManipulation(currentData, setCurrentData);
  const factories = useFilterFactories();
  const dialogs = useDialogStates();

  // MongoDB aggregation conversion
  const generateMongoQuery = () => {
    // Determine if we're in annotation mode (projections exist)
    const hasAnnotations = projectionFields && projectionFields.length > 0;

    // Collect field names from annotation fields that need to be available
    const annotationFieldsSet = new Set<any>();

    if (projectionFields) {
      projectionFields.forEach((f: any) => {
        if (!f.fieldName || f.fieldName === "objectId") return;

        // Check if this is an arithmetic variable
        const arithVar = customVariables.find(
          (v: any) => v.name === f.fieldName,
        );

        if (arithVar) {
          // Arithmetic variable - scan its expression for variable references
          // that need to be materialized
          if (arithVar.variable) {
            const expression = arithVar.variable.includes("=")
              ? arithVar.variable.split("=")[1].trim()
              : arithVar.variable;

            // Scan for MongoDB-style variable references like $varname
            const fieldRefPattern = /\$([a-zA-Z_][a-zA-Z0-9_]*)/g;
            const matches = [...expression.matchAll(fieldRefPattern)];

            matches.forEach((match: any) => {
              const varName = match[1];

              // If it's a variable (not a schema field or MongoDB operator), add it
              const isVariable =
                customVariables.some((v: any) => v.name === varName) ||
                customListVariables.some((v: any) => v.name === varName) ||
                customSwitchCases.some((v: any) => v.name === varName);

              if (isVariable) {
                annotationFieldsSet.add(varName);
              }
            });
          }
        } else {
          // Not an arithmetic variable - include it directly
          annotationFieldsSet.add(f.fieldName);
        }
      });
    }

    const annotationFields = Array.from(annotationFieldsSet);

    // Always use filters as the base query, regardless of mode
    // This ensures annotations show both filters + projections
    const baseQuery: any = convertToMongoAggregation(
      filters,
      schema,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
      annotationFields, // Pass annotation fields so switch cases can be projected
      hasAnnotations, // Pass annotation mode flag
    );

    // If there are projection fields (annotations), adapt the final project stage
    if (hasAnnotations) {
      // Get the last stage (which is sempre a $project stage now)
      let lastStageIndex = baseQuery.length - 1;
      let lastStage = baseQuery[lastStageIndex];

      if (lastStage && lastStage.$project) {
        // Start with existing projection (includes _id and used fields)
        const enhancedProjection: any = { ...lastStage.$project };

        // Add objectId explicitly if not already there
        if (!enhancedProjection.objectId) {
          enhancedProjection.objectId = "$objectId";
        }

        // Build annotations object
        const annotations_object: any = {};

        projectionFields.forEach((field: any) => {
          if (!field.fieldName || field.fieldName === "objectId") return;
          const outputName = field.outputName || field.fieldName;

          // Check if this field is an arithmetic variable
          const arithVar = customVariables.find(
            (v: any) => v.name === field.fieldName,
          );

          // Handle different projection types
          switch (field.type) {
            case "include":
              if (arithVar) {
                // Inline the arithmetic expression instead of referencing it
                const expr = convertArithmeticExpression(
                  arithVar.variable,
                  customVariables,
                );
                if (expr) {
                  annotations_object[outputName] = expr;
                } else {
                  // Fallback to reference if conversion fails
                  annotations_object[outputName] = `$${field.fieldName}`;
                }
              } else {
                annotations_object[outputName] = `$${field.fieldName}`;
              }
              break;
            case "exclude":
              annotations_object[outputName] = 0;
              break;
            case "round":
              if (arithVar) {
                // Inline the arithmetic expression and wrap in $round
                const expr = convertArithmeticExpression(
                  arithVar.variable,
                  customVariables,
                );
                if (expr) {
                  annotations_object[outputName] = {
                    $round: [expr, field.roundDecimals || 4],
                  };
                } else {
                  // Fallback to reference if conversion fails
                  annotations_object[outputName] = {
                    $round: [`$${field.fieldName}`, field.roundDecimals || 4],
                  };
                }
              } else {
                annotations_object[outputName] = {
                  $round: [`$${field.fieldName}`, field.roundDecimals || 4],
                };
              }
              break;
            default:
              if (arithVar) {
                // Inline the arithmetic expression instead of referencing it
                const expr = convertArithmeticExpression(
                  arithVar.variable,
                  customVariables,
                );
                if (expr) {
                  annotations_object[outputName] = expr;
                } else {
                  // Fallback to reference if conversion fails
                  annotations_object[outputName] = `$${field.fieldName}`;
                }
              } else {
                annotations_object[outputName] = `$${field.fieldName}`;
              }
          }
        });

        // Add annotations_object to projection if there are any
        if (Object.keys(annotations_object).length > 0) {
          enhancedProjection.annotations = annotations_object;

          // IMPORTANT: Scan the annotation expressions for $variableName references
          // These need to be materialized before the $project stage
          const extractVariableRefsFromExpr = (expr: any, refs: any) => {
            if (typeof expr === "string" && expr.startsWith("$")) {
              // Field reference like "$jd_min_prv"
              const fieldName = expr.substring(1); // Remove $
              // Check if this is a custom variable, list variable, or switch case
              const isCustomVar = customVariables.some(
                (v: any) => v.name === fieldName,
              );
              const isListVar = customListVariables.some(
                (v: any) => v.name === fieldName,
              );
              const isSwitchCase = customSwitchCases.some(
                (v: any) => v.name === fieldName,
              );

              if (isCustomVar || isListVar || isSwitchCase) {
                refs.add(fieldName);
              }
            } else if (Array.isArray(expr)) {
              expr.forEach((item: any) =>
                extractVariableRefsFromExpr(item, refs),
              );
            } else if (typeof expr === "object" && expr !== null) {
              Object.values(expr).forEach((value: any) =>
                extractVariableRefsFromExpr(value, refs),
              );
            }
          };

          const additionalVarRefs = new Set<any>();
          Object.values(annotations_object).forEach((annotationExpr: any) => {
            extractVariableRefsFromExpr(annotationExpr, additionalVarRefs);
          });

          // Add these variable references to annotationFields so they get materialized
          additionalVarRefs.forEach((varName: any) => {
            if (!annotationFields.includes(varName)) {
              annotationFields.push(varName);
            }
          });

          // If we found new variables, rebuild the pipeline with them included
          if (additionalVarRefs.size > 0) {
            const rebuiltQuery: any = convertToMongoAggregation(
              filters,
              schema,
              fieldOptions,
              customVariables,
              customListVariables,
              customSwitchCases,
              annotationFields,
              hasAnnotations,
            );

            // Replace baseQuery entirely with rebuilt query, except keep our enhanced projection
            baseQuery.length = 0;
            baseQuery.push(...rebuiltQuery.slice(0, -1)); // All stages except final project
            // Update lastStageIndex after rebuild
            lastStageIndex = baseQuery.length;
          }
        }

        // Replace/add the last stage with the enhanced projection
        baseQuery[lastStageIndex] = { $project: enhancedProjection };
      }
    }

    return baseQuery;
  };

  const getFormattedMongoQuery = () => {
    const pipeline = generateMongoQuery();
    return formatMongoAggregation(pipeline);
  };

  const hasValidQuery = () => {
    // Use localFilterData if it exists and has been modified, otherwise use filters
    const dataToCheck =
      hasBeenModified && localFilterData ? localFilterData : filters;
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
