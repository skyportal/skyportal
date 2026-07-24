import { latexToMongoConverter } from "./robustLatexConverter.js";

/**
 * Helper function to extract field name from various formats
 * Supports:
 * - String values (legacy): "fieldName"
 * - Object with metadata (new): { name: "fieldName", _meta: {...} }
 * - Object with type (list condition): { type: "array", field: "fieldName", name: "listName" }
 * - Old object format: { value: "fieldName" }
 *
 * @param {*} field - Field value in any supported format
 * @returns {string} Extracted field name
 */
const normalizeFieldName = (field) => {
  if (!field) return "";
  if (typeof field === "string") return field;
  if (typeof field === "object") {
    // New format with metadata
    if (field.name) return field.name;
    // Old formats
    if (field.value) return field.value;
    if (field.field) return field.field;
  }
  return String(field);
};

/**
 * Helper function to extract value from various formats
 * Handles the same formats as normalizeFieldName
 *
 * @param {*} value - Value in any supported format
 * @returns {*} Extracted value (preserves objects for list conditions)
 */
const normalizeValue = (value) => {
  // List condition objects should be preserved
  if (value && typeof value === "object" && value.type === "array") {
    return value;
  }
  // New format with metadata - extract name
  if (value && typeof value === "object" && value.name && value._meta) {
    return value.name;
  }
  // Otherwise return as-is
  return value;
};

/**
 * Recursively collects $-prefixed field names from a MongoDB expression object.
 * @param {*} obj - Expression to scan
 * @param {boolean} filterNested - If true, exclude names with "$$" prefix or containing "."
 */
const collectDollarRefs = (obj, filterNested = false) => {
  const refs = [];
  const collect = (o) => {
    if (typeof o === "string" && o.startsWith("$")) {
      const name = o.substring(1);
      if (!filterNested || (!name.startsWith("$") && !name.includes("."))) {
        refs.push(name);
      }
    } else if (typeof o === "object" && o !== null) {
      Object.values(o).forEach(collect);
    }
  };
  collect(obj);
  return refs;
};

/**
 * Increments list variable usage count in the dependency graph.
 */
const trackListVarUsage = (
  graph,
  name,
  customListVariables,
  mustMaterialize = false,
) => {
  const listVar = customListVariables.find((v) => v.name === name);
  if (!listVar) return;
  const current = graph.listVariableUsage.get(name) || {
    count: 0,
    variable: listVar,
    mustMaterialize: false,
  };
  graph.listVariableUsage.set(name, {
    count: current.count + 1,
    variable: listVar,
    mustMaterialize: current.mustMaterialize || mustMaterialize,
  });
};

/**
 * Builds a field-based MongoDB condition: { [fieldName]: { $op: value } }
 * Used for list variables, switch cases, and arithmetic variable fallback.
 */
const makeFieldCondition = (fieldName, operator, value) => {
  switch (operator) {
    case "$eq":
    case "equals":
      return typeof value === "boolean"
        ? { [fieldName]: value }
        : { [fieldName]: { $eq: value } };
    case "$ne":
    case "not equals":
      return { [fieldName]: { $ne: value } };
    case "$gt":
      return { [fieldName]: { $gt: value } };
    case "$gte":
      return { [fieldName]: { $gte: value } };
    case "$lt":
      return { [fieldName]: { $lt: value } };
    case "$lte":
      return { [fieldName]: { $lte: value } };
    case "$in":
      return {
        [fieldName]: { $in: Array.isArray(value) ? value : [value] },
      };
    case "$exists":
      return {
        [fieldName]: {
          $exists: typeof value === "boolean" ? value : true,
        },
      };
    case "$lengthGt":
      return value < 0
        ? { [fieldName]: { $exists: true } }
        : { [`${fieldName}.${value}`]: { $exists: true } };
    case "$lengthLt":
      return value <= 0
        ? { [`${fieldName}.0`]: { $exists: false } }
        : { [`${fieldName}.${value - 1}`]: { $exists: false } };
    default:
      return { [fieldName]: { $eq: value } };
  }
};

/**
 * Builds an aggregation-expression-style condition: { $op: [fieldExpr, value] }
 * Used in $expr, $filter/$map, and $switch contexts.
 */
const makeExprArrayCondition = (fieldExpr, operator, value) => {
  switch (operator) {
    case "$eq":
    case "equals":
      return { $eq: [fieldExpr, value] };
    case "$ne":
    case "not equals":
      return { $ne: [fieldExpr, value] };
    case "$gt":
      return { $gt: [fieldExpr, value] };
    case "$gte":
      return { $gte: [fieldExpr, value] };
    case "$lt":
      return { $lt: [fieldExpr, value] };
    case "$lte":
      return { $lte: [fieldExpr, value] };
    case "$in":
      return { $in: [fieldExpr, Array.isArray(value) ? value : [value]] };
    case "$exists":
      return { $ne: [{ $type: fieldExpr }, "missing"] };
    case "$isNumber":
      return { $isNumber: fieldExpr };
    case "$lengthGt":
    case "length >":
      return { $gt: [{ $size: fieldExpr }, value] };
    case "$lengthLt":
    case "length <":
      return { $lt: [{ $size: fieldExpr }, value] };
    default:
      return { $eq: [fieldExpr, value] };
  }
};

/**
 * Main pipeline builder function
 * @param {Array} filters - Filter conditions
 * @param {Object} schema - Schema definition
 * @param {Array} fieldOptions - Available fields
 * @param {Array} customVariables - Arithmetic variables
 * @param {Array} customListVariables - List variables
 * @param {Array} customSwitchCases - Switch cases
 * @param {Array} additionalFieldsToProject - Extra fields to project
 * @param {Boolean} annotationMode - If true, only project mandatory fields and additionalFieldsToProject
 * @returns {Array} MongoDB aggregation pipeline
 */
export const buildMongoAggregationPipeline = (
  filters,
  schema = {},
  fieldOptions = [],
  customVariables = [],
  customListVariables = [],
  customSwitchCases = [],
  additionalFieldsToProject = [],
  annotationMode = false,
) => {
  try {
    const pipeline = [];

    // Analyze dependencies
    const dependencyGraph = buildDependencyGraph(
      filters,
      customVariables,
      customListVariables,
      customSwitchCases,
      fieldOptions,
    );

    // In annotation mode, mark source fields as used so they're available for $field references
    if (annotationMode && additionalFieldsToProject.length > 0) {
      additionalFieldsToProject.forEach((field) => {
        // Check if it's a custom variable
        if (customVariables.some((v) => v.name === field)) {
          dependencyGraph.usedFields.customVariables.add(field);

          // IMPORTANT: When an arithmetic variable is used in annotations, we need to ensure
          // all variables referenced in its expression are also materialized
          // Scan the expression for variable references
          const arithVar = customVariables.find((v) => v.name === field);
          if (arithVar && arithVar.variable) {
            const expression = arithVar.variable.includes("=")
              ? arithVar.variable.split("=")[1].trim()
              : arithVar.variable;

            // Scan for MongoDB field references like $varname
            const fieldRefPattern = /\$([a-zA-Z_][a-zA-Z0-9_]*)/g;
            const fieldMatches = [...expression.matchAll(fieldRefPattern)];

            fieldMatches.forEach((match) => {
              const refName = match[1];

              // Check if this reference is to another variable that needs materialization
              if (customVariables.some((v) => v.name === refName)) {
                dependencyGraph.usedFields.customVariables.add(refName);
              } else if (customListVariables.some((v) => v.name === refName)) {
                dependencyGraph.usedFields.listVariables.add(refName);
                trackListVarUsage(
                  dependencyGraph,
                  refName,
                  customListVariables,
                  true,
                );
              } else if (customSwitchCases.some((v) => v.name === refName)) {
                dependencyGraph.usedFields.switchCases.add(refName);
              } else if (
                fieldOptions.some(
                  (f) => f.value === refName || f.label === refName,
                )
              ) {
                dependencyGraph.usedFields.baseFields.add(refName);
              }
            });
          }
        }
        // Check if it's a list variable
        else if (customListVariables.some((v) => v.name === field)) {
          dependencyGraph.usedFields.listVariables.add(field);
          trackListVarUsage(dependencyGraph, field, customListVariables);
        }
        // Check if it's a switch case
        else if (customSwitchCases.some((v) => v.name === field)) {
          dependencyGraph.usedFields.switchCases.add(field);
        }
        // Otherwise it's a base field
        else {
          dependencyGraph.usedFields.baseFields.add(field);
        }
      });

      // Re-run dependency marking to ensure dependencies of these fields are also marked as used
      markDependenciesAsUsed(
        dependencyGraph,
        customVariables,
        customListVariables,
        customSwitchCases,
      );
    }

    // Determine pipeline stages needed
    const stages = determineRequiredStages(dependencyGraph);

    // Extract early match conditions (simple filters on base fields)
    const { earlyMatch, remainingFilters } = extractEarlyMatchConditions(
      filters,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
    );

    // Insert early $match stage if we have simple conditions
    if (earlyMatch && Object.keys(earlyMatch).length > 0) {
      pipeline.push({ $match: earlyMatch });
    }

    // Build initial project stage for base variables
    // Skip if we only have early match (no variables to compute)
    const hasVariablesOrSwitches =
      dependencyGraph.usedFields.customVariables.size > 0 ||
      dependencyGraph.usedFields.listVariables.size > 0 ||
      dependencyGraph.usedFields.switchCases.size > 0;

    if (stages.needsInitialProject && hasVariablesOrSwitches) {
      const initialProject = buildInitialProjectStage(
        dependencyGraph,
        customVariables,
        customListVariables,
        customSwitchCases,
        fieldOptions,
      );
      if (Object.keys(initialProject.$project).length > 1) {
        // More than just _id
        pipeline.push(initialProject);
      }
    }

    // Build stages for variables in dependency order
    const variableStages = buildVariableStagesByLevel(
      dependencyGraph,
      customVariables,
      customListVariables,
      customSwitchCases,
      fieldOptions,
      additionalFieldsToProject,
      annotationMode,
    );
    pipeline.push(...variableStages);

    // Build custom block definitions (only for blocks used 2+ times)
    const customBlockStage = buildCustomBlockStage(
      dependencyGraph,
      schema,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
    );
    if (customBlockStage) {
      pipeline.push(customBlockStage);
    }

    // Build match stages for remaining filters
    const matchStages = buildMatchStages(
      remainingFilters,
      dependencyGraph,
      schema,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
    );
    pipeline.push(...matchStages);

    // Determine if we need a final project stage
    // Skip if: only early match exists (no variables, no custom blocks, no complex filters)
    // and not in annotation mode
    const hasVariableStages = variableStages.length > 0;
    const hasCustomBlocks = customBlockStage !== null;
    const hasComplexFilters = remainingFilters.length > 0;
    const hasOnlyEarlyMatch =
      earlyMatch &&
      Object.keys(earlyMatch).length > 0 &&
      !hasVariableStages &&
      !hasCustomBlocks &&
      !hasComplexFilters;

    // Build final project stage only if needed
    const needsFinalProject = annotationMode || !hasOnlyEarlyMatch;

    if (needsFinalProject) {
      const finalProject = buildFinalProjectStage(
        dependencyGraph,
        additionalFieldsToProject,
        fieldOptions,
        annotationMode,
      );
      if (finalProject) {
        pipeline.push(finalProject);
      }
    }

    // Validate that all field references in the pipeline are defined
    const validationErrors = validatePipelineFieldReferences(
      pipeline,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
    );

    return pipeline;
  } catch (error) {
    console.error("Failed to build MongoDB aggregation pipeline:", error);
    return [];
  }
};

/**
 * Builds a comprehensive dependency graph for all variables
 */
const buildDependencyGraph = (
  filters,
  customVariables,
  customListVariables,
  customSwitchCases,
  fieldOptions,
) => {
  // Validate that custom variable names don't conflict with schema fields
  const schemaFieldNames = new Set(
    fieldOptions.map((f) => f.value).concat(fieldOptions.map((f) => f.label)),
  );

  const nameCollisions = [];

  [...customVariables, ...customListVariables, ...customSwitchCases].forEach(
    (varDef) => {
      if (schemaFieldNames.has(varDef.name)) {
        nameCollisions.push({
          variableName: varDef.name,
          variableType: customVariables.includes(varDef)
            ? "arithmetic variable"
            : customListVariables.includes(varDef)
              ? "list variable"
              : "switch case",
        });
      }
    },
  );

  if (nameCollisions.length > 0) {
    console.error(
      "Variable name collision detected! The following custom variables have the same names as schema fields:",
      nameCollisions,
    );
    console.error(
      "This will cause the custom variable to overwrite the schema field in the pipeline.",
      "Please rename your custom variables to avoid conflicts.",
    );
    // Optionally throw an error to prevent pipeline generation
    // throw new Error(`Variable name collisions: ${nameCollisions.map(c => c.variableName).join(', ')}`);
  }

  const graph = {
    variables: new Map(), // variable name -> dependencies
    reverseDeps: new Map(), // variable name -> variables that depend on it
    levels: new Map(), // variable name -> dependency level
    usedFields: {
      baseFields: new Set(),
      customVariables: new Set(),
      listVariables: new Set(),
      switchCases: new Set(),
    },
    customBlockUsage: new Map(), // custom block name -> { count, block }
    listVariableUsage: new Map(), // list variable name -> { count, variable, mustMaterialize }
    nameCollisions: nameCollisions, // Track collisions for later reference
  };

  // Initialize all variables in graph
  [...customVariables, ...customListVariables, ...customSwitchCases].forEach(
    (varDef) => {
      graph.variables.set(varDef.name, new Set());
      graph.reverseDeps.set(varDef.name, new Set());
    },
  );

  // Analyze filters to find used fields
  analyzeFiltersForUsage(
    filters,
    graph,
    customVariables,
    customListVariables,
    customSwitchCases,
    fieldOptions,
  );

  // Build dependencies for each variable type
  buildArithmeticDependencies(
    customVariables,
    graph,
    customListVariables,
    customSwitchCases,
    fieldOptions,
  );
  buildListDependencies(
    customListVariables,
    graph,
    customVariables,
    customSwitchCases,
    fieldOptions,
  );
  buildSwitchDependencies(
    customSwitchCases,
    graph,
    customVariables,
    customListVariables,
    fieldOptions,
  );

  // Recursively mark dependencies as used
  markDependenciesAsUsed(
    graph,
    customVariables,
    customListVariables,
    customSwitchCases,
  );

  // Calculate dependency levels using topological sort.
  // Arithmetic variables are always inlined into the expressions that reference
  // them, so they never produce a separate $addFields stage. Excluding them
  // from the level calculation prevents list variables from being artificially
  // pushed to higher levels just because they reference an arithmetic variable.
  const arithmeticVarNames = new Set(customVariables.map((v) => v.name));
  calculateDependencyLevels(graph, arithmeticVarNames);

  return graph;
};

/**
 * Recursively marks dependencies of used variables as used
 */
const markDependenciesAsUsed = (
  graph,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  const visited = new Set();

  const markDeps = (varName) => {
    if (visited.has(varName)) return;
    visited.add(varName);

    const deps = graph.variables.get(varName) || new Set();
    for (const dep of deps) {
      // If it's a variable (not a schema field), mark it as used in the appropriate category
      if (graph.variables.has(dep)) {
        if (customVariables.some((v) => v.name === dep)) {
          graph.usedFields.customVariables.add(dep);
        } else if (customListVariables.some((lv) => lv.name === dep)) {
          graph.usedFields.listVariables.add(dep);
          // If this is a list variable dependency, ensure it's tracked for usage
          const listVar = customListVariables.find((lv) => lv.name === dep);
          if (listVar) {
            const current = graph.listVariableUsage.get(dep) || {
              count: 0,
              variable: listVar,
              mustMaterialize: false,
            };
            // Mark as must materialize because it's a dependency
            graph.listVariableUsage.set(dep, {
              count: Math.max(current.count, 1),
              variable: listVar,
              mustMaterialize: true,
            });
          }
        } else if (customSwitchCases.some((v) => v.name === dep)) {
          graph.usedFields.switchCases.add(dep);
        }
        markDeps(dep); // Recursively mark dependencies
      } else {
        // It's a schema field - mark it as used since this variable is used
        graph.usedFields.baseFields.add(dep);
      }
    }
  };

  // Mark dependencies for all initially used variables
  graph.usedFields.customVariables.forEach(markDeps);
  graph.usedFields.listVariables.forEach(markDeps);
  graph.usedFields.switchCases.forEach(markDeps);
};

/**
 * Analyzes filters to determine which fields/variables are used
 */
const analyzeFiltersForUsage = (
  filters,
  graph,
  customVariables,
  customListVariables,
  customSwitchCases,
  fieldOptions,
) => {
  const analyzeBlock = (block, parentCustomBlockName = null) => {
    if (!block) return;

    // Track custom block usage for optimization
    // Only count blocks that are actual block types (not conditions inside the block)
    // AND are not the same custom block as the parent (those are part of the parent block's definition)
    if (
      block.customBlockName &&
      (block.type === "block" || block.category === "block")
    ) {
      // Only count if this is a different custom block than the parent
      // (same customBlockName means it's part of the parent's internal structure)
      if (block.customBlockName !== parentCustomBlockName) {
        const blockName = block.customBlockName;
        const current = graph.customBlockUsage.get(blockName) || {
          count: 0,
          block: block,
        };
        graph.customBlockUsage.set(blockName, {
          count: current.count + 1,
          block: block,
        });

        // Analyze children, passing this block's customBlockName so children with the same name are skipped
        if (block.children) {
          block.children.forEach((child) =>
            analyzeBlock(child, block.customBlockName),
          );
        }
      } else {
        // Still analyze children for field/variable dependencies
        if (block.children) {
          block.children.forEach((child) =>
            analyzeBlock(child, parentCustomBlockName),
          );
        }
      }
      return;
    }

    // For non-custom blocks, analyze children and propagate parent's customBlockName
    if (block.children) {
      block.children.forEach((child) =>
        analyzeBlock(child, parentCustomBlockName),
      );
    }

    if (block.field) {
      // Normalize field to handle both string and object formats
      const fieldName = normalizeFieldName(block.field);
      const fieldType = block.fieldType;

      // If fieldType is explicitly set, use it
      if (fieldType) {
        switch (fieldType) {
          case "schema":
            graph.usedFields.baseFields.add(fieldName);
            break;
          case "variable":
            graph.usedFields.customVariables.add(fieldName);
            break;
          case "listVariable":
            graph.usedFields.listVariables.add(fieldName);
            break;
          case "switchCase":
            graph.usedFields.switchCases.add(fieldName);
            break;
        }
      }
      // Check if field has metadata (new format: {name: "...", _meta: {...}})
      // Use metadata to determine exact field type when available (solves name collision issues)
      else if (
        block.field &&
        typeof block.field === "object" &&
        block.field._meta
      ) {
        const meta = block.field._meta;

        // Route based on metadata flags
        if (meta.isSwitchCase) {
          graph.usedFields.switchCases.add(fieldName);
        } else if (meta.isListVariable) {
          graph.usedFields.listVariables.add(fieldName);
          trackListVarUsage(graph, fieldName, customListVariables);
        } else if (meta.isVariable) {
          graph.usedFields.customVariables.add(fieldName);
        } else if (meta.isSchemaField) {
          graph.usedFields.baseFields.add(fieldName);
        }
        // If no metadata flags match, fall through to legacy resolution below
        else {
          // Fallback: check what type it actually is
          if (
            fieldOptions.some(
              (f) => f.value === fieldName || f.label === fieldName,
            )
          ) {
            graph.usedFields.baseFields.add(fieldName);
          } else if (customVariables.some((v) => v.name === fieldName)) {
            graph.usedFields.customVariables.add(fieldName);
          } else if (customListVariables.some((v) => v.name === fieldName)) {
            graph.usedFields.listVariables.add(fieldName);
            trackListVarUsage(graph, fieldName, customListVariables);
          } else if (customSwitchCases.some((v) => v.name === fieldName)) {
            graph.usedFields.switchCases.add(fieldName);
          }
        }
      }
      // Fallback to legacy precedence-based resolution if no fieldType and no metadata
      else {
        // Check if it's a schema field first (prefer over variables)
        if (
          fieldOptions.some(
            (f) => f.value === fieldName || f.label === fieldName,
          )
        ) {
          graph.usedFields.baseFields.add(fieldName);
        }
        // Check if it's a custom variable
        else if (customVariables.some((v) => v.name === fieldName)) {
          graph.usedFields.customVariables.add(fieldName);
        }
        // Check if it's a list variable
        else if (customListVariables.some((v) => v.name === fieldName)) {
          graph.usedFields.listVariables.add(fieldName);
          trackListVarUsage(graph, fieldName, customListVariables);
        }
        // Check if it's a switch case
        else if (customSwitchCases.some((v) => v.name === fieldName)) {
          graph.usedFields.switchCases.add(fieldName);
        }
      }
    }

    // Check values for field references
    if (block.value) {
      // Check if value has metadata (new format: {name: "...", _meta: {...}})
      if (
        block.value &&
        typeof block.value === "object" &&
        block.value._meta &&
        block.value.name
      ) {
        const valueName = block.value.name;
        const meta = block.value._meta;

        // Route based on metadata flags
        if (meta.isSwitchCase) {
          graph.usedFields.switchCases.add(valueName);
        } else if (meta.isListVariable) {
          graph.usedFields.listVariables.add(valueName);
          trackListVarUsage(graph, valueName, customListVariables);
        } else if (meta.isVariable) {
          graph.usedFields.customVariables.add(valueName);
        } else if (meta.isSchemaField) {
          graph.usedFields.baseFields.add(valueName);
        }
      }
      // Fallback: normalize and check by string name
      else {
        const normalizedVal = normalizeValue(block.value);
        if (typeof normalizedVal === "string") {
          const value = normalizedVal;
          // Check schema fields first
          if (
            fieldOptions.some((f) => f.value === value || f.label === value)
          ) {
            graph.usedFields.baseFields.add(value);
          }
          // Then check variables
          else if (customVariables.some((v) => v.name === value)) {
            graph.usedFields.customVariables.add(value);
          } else if (customListVariables.some((v) => v.name === value)) {
            graph.usedFields.listVariables.add(value);
            trackListVarUsage(graph, value, customListVariables);
          } else if (customSwitchCases.some((v) => v.name === value)) {
            graph.usedFields.switchCases.add(value);
          }
        }
      }
    }

    // Scan for variable references in raw MongoDB expressions
    // This handles cases where filters contain operators like $filter, $map with inline expressions
    // that reference variables directly (e.g., "$jd_min_prv" in a $subtract expression)
    if (block.operator && block.value && typeof block.value === "object") {
      const allVarNames = collectDollarRefs(block.value, true);

      allVarNames.forEach((varName) => {
        if (customVariables.some((v) => v.name === varName)) {
          graph.usedFields.customVariables.add(varName);
        } else if (customListVariables.some((v) => v.name === varName)) {
          graph.usedFields.listVariables.add(varName);
          trackListVarUsage(graph, varName, customListVariables, true);
        } else if (customSwitchCases.some((v) => v.name === varName)) {
          graph.usedFields.switchCases.add(varName);
        } else if (
          fieldOptions.some((f) => f.value === varName || f.label === varName)
        ) {
          graph.usedFields.baseFields.add(varName);
        }
      });
    }
  };

  filters.forEach(analyzeBlock);
};

/**
 * Builds dependencies for arithmetic variables
 */
const buildArithmeticDependencies = (
  customVariables,
  graph,
  customListVariables,
  customSwitchCases,
  fieldOptions,
) => {
  customVariables.forEach((varDef) => {
    const deps = new Set();

    // Parse the arithmetic expression to find dependencies
    if (varDef.variable && varDef.variable.includes("=")) {
      const expression = varDef.variable.split("=")[1].trim();

      // First, check for MongoDB field references (e.g., $10days, $candidate.magpsf)
      // This handles expressions with MongoDB operators like $map, $ifNull, etc.
      const fieldRefPattern = /\$([a-zA-Z_][a-zA-Z0-9_]*)/g;
      const fieldMatches = [...expression.matchAll(fieldRefPattern)];

      fieldMatches.forEach((match) => {
        const fieldName = match[1];

        // Check if it's a custom variable
        if (
          customVariables.some(
            (v) => v.name === fieldName && v.name !== varDef.name,
          )
        ) {
          deps.add(fieldName);
        }
        // Check if it's a list variable
        else if (customListVariables.some((v) => v.name === fieldName)) {
          deps.add(fieldName);
        }
        // Check if it's a switch case
        else if (customSwitchCases.some((v) => v.name === fieldName)) {
          deps.add(fieldName);
        }
        // Check if it's a schema field
        else if (
          fieldOptions.some(
            (f) => f.value === fieldName || f.label === fieldName,
          )
        ) {
          deps.add(fieldName);
        }
      });

      // Also check for variable references without $ prefix (for LaTeX-style expressions)
      const allVars = [
        ...customVariables,
        ...customListVariables,
        ...customSwitchCases,
      ];
      allVars.forEach((otherVar) => {
        if (otherVar.name !== varDef.name) {
          // Use word boundary regex to avoid substring matches
          const regex = new RegExp(`\\b${otherVar.name}\\b`, "g");
          if (regex.test(expression)) {
            deps.add(otherVar.name);
          }
        }
      });

      // Check for schema field references using the LaTeX converter's field extraction
      // This properly handles fields inside complex expressions, functions, and operators
      const extractedFields =
        latexToMongoConverter.extractFieldDependencies(expression);

      extractedFields.forEach((extractedField) => {
        // Verify this is actually a schema field (not a variable or function name)
        const isSchemaField = fieldOptions.some(
          (f) => f.value === extractedField || f.label === extractedField,
        );
        const isVariable = allVars.some((v) => v.name === extractedField);

        // Only add if it's a schema field and not already added as a variable
        if (isSchemaField && !isVariable) {
          deps.add(extractedField);
          // NOTE: Don't mark field as used here - only mark fields as used if the variable
          // that references them is actually used in filter conditions
          // graph.usedFields.baseFields.add(extractedField);
        }
      });
    }

    graph.variables.set(varDef.name, deps);
    deps.forEach((dep) => {
      if (graph.reverseDeps.has(dep)) {
        graph.reverseDeps.get(dep).add(varDef.name);
      }
    });
  });
};

/**
 * Builds dependencies for list variables
 */
const buildListDependencies = (
  customListVariables,
  graph,
  customVariables,
  customSwitchCases,
  fieldOptions,
) => {
  customListVariables.forEach((varDef) => {
    const deps = new Set();

    if (varDef.listCondition) {
      const condition = varDef.listCondition;

      // Normalize field to handle both legacy string format and new object format with metadata
      const normalizedField = normalizeFieldName(condition.field);

      // IMPORTANT: Add the array field itself as a dependency
      // This is the actual data source that needs to be projected (e.g., cross_matches.NED_BetaV3, prv_candidates)
      if (normalizedField) {
        deps.add(normalizedField);
      }

      // Check field reference in condition.field (used in filter/map conditions)
      if (normalizedField) {
        if (
          fieldOptions.some(
            (f) => f.value === normalizedField || f.label === normalizedField,
          )
        ) {
          // Already added above
        } else {
          // Check if it's a variable name
          const allVars = [
            ...customVariables,
            ...customListVariables,
            ...customSwitchCases,
          ];
          if (allVars.some((v) => v.name === normalizedField)) {
            deps.add(normalizedField);
          }
        }
      }

      // Check for dependencies in map expressions
      if (condition.operator === "$map") {
        const normalizedValue = normalizeValue(condition.value);
        const mapExpr =
          normalizedValue?.mapExpression ||
          condition.mapExpression ||
          normalizedValue;
        if (mapExpr) {
          collectDollarRefs(mapExpr).forEach((varName) => {
            if (customVariables.some((v) => v.name === varName)) {
              deps.add(varName);
            }
            if (
              varName !== varDef.name &&
              customListVariables.some((v) => v.name === varName)
            ) {
              deps.add(varName);
            }
            if (
              varName !== varDef.name &&
              customSwitchCases.some((v) => v.name === varName)
            ) {
              deps.add(varName);
            }
          });
        }
      }

      // Check for dependencies in filter/any/all element conditions
      if (
        (condition.operator === "$filter" ||
          condition.operator === "$anyElementTrue" ||
          condition.operator === "$allElementTrue") &&
        condition.value
      ) {
        // If the condition has a children structure (block format), analyze it
        if (condition.value.children) {
          analyzeBlockForDeps(
            { children: condition.value.children },
            deps,
            customVariables,
            customListVariables,
            customSwitchCases,
            fieldOptions,
            varDef.name,
          );
        }

        // Also scan for direct MongoDB expression references
        collectDollarRefs(condition.value).forEach((varName) => {
          if (customVariables.some((v) => v.name === varName)) {
            deps.add(varName);
          }
          if (
            varName !== varDef.name &&
            customListVariables.some((v) => v.name === varName)
          ) {
            deps.add(varName);
          }
          if (
            varName !== varDef.name &&
            customSwitchCases.some((v) => v.name === varName)
          ) {
            deps.add(varName);
          }
        });
      }

      // Check for subfield dependencies in aggregations
      if (
        ["$min", "$max", "$avg", "$sum"].includes(condition.operator) &&
        condition.subField
      ) {
        // subField might reference other variables
        const subField = condition.subField;
        [
          ...customVariables,
          ...customListVariables,
          ...customSwitchCases,
        ].forEach((otherVar) => {
          if (
            otherVar.name !== varDef.name &&
            subField.includes(otherVar.name)
          ) {
            deps.add(otherVar.name);
          }
        });
      }
    }

    graph.variables.set(varDef.name, deps);
    deps.forEach((dep) => {
      if (graph.reverseDeps.has(dep)) {
        graph.reverseDeps.get(dep).add(varDef.name);
      }
    });
  });
};

/**
 * Builds dependencies for switch cases
 */
const buildSwitchDependencies = (
  customSwitchCases,
  graph,
  customVariables,
  customListVariables,
  fieldOptions,
) => {
  customSwitchCases.forEach((varDef) => {
    const deps = new Set();

    const switchDef = varDef.switchCondition || varDef.switch;
    // switchCondition has structure: { operator: "$switch", value: { cases: [...], default: ... } }
    // Extract the value if it exists, otherwise use switchDef directly (for backward compatibility)
    const switchValue = switchDef?.value || switchDef;

    if (switchValue?.cases) {
      switchValue.cases.forEach((caseItem) => {
        // Analyze the condition block
        if (caseItem.block) {
          analyzeBlockForDeps(
            caseItem.block,
            deps,
            customVariables,
            customListVariables,
            customSwitchCases,
            fieldOptions,
            varDef.name,
          );
        }

        // Analyze the 'then' value
        if (caseItem.then) {
          // Check if it's an object with metadata
          if (
            typeof caseItem.then === "object" &&
            caseItem.then._meta &&
            caseItem.then.name
          ) {
            const thenName = caseItem.then.name;
            const meta = caseItem.then._meta;

            // Add as dependency based on type
            if (meta.isSchemaField) {
              deps.add(thenName);
            } else if (meta.isListVariable || meta.isSwitchCase) {
              if (thenName !== varDef.name) {
                deps.add(thenName);
              }
            } else {
              // Fallback: check if it's actually a schema field even without the flag
              if (isSchemaField(thenName, fieldOptions)) {
                deps.add(thenName);
              }
            }
          }
          // Check if it's a string
          else if (typeof caseItem.then === "string") {
            // Check if it's a variable reference
            const isVariable = [
              ...customVariables,
              ...customListVariables,
              ...customSwitchCases,
            ].some(
              (otherVar) =>
                otherVar.name === caseItem.then &&
                otherVar.name !== varDef.name,
            );

            if (isVariable) {
              deps.add(caseItem.then);
            }
            // Check if it's a schema field
            else if (isSchemaField(caseItem.then, fieldOptions)) {
              deps.add(caseItem.then);
            }
          }
        }
      });

      // Check default value
      if (switchValue.default) {
        // Check if it's an object with metadata
        if (
          typeof switchValue.default === "object" &&
          switchValue.default._meta &&
          switchValue.default.name
        ) {
          const defaultName = switchValue.default.name;
          const meta = switchValue.default._meta;

          // Add as dependency based on type
          if (meta.isSchemaField) {
            deps.add(defaultName);
          } else if (meta.isListVariable || meta.isSwitchCase) {
            if (defaultName !== varDef.name) {
              deps.add(defaultName);
            }
          } else {
            // Fallback: check if it's actually a schema field even without the flag
            if (isSchemaField(defaultName, fieldOptions)) {
              deps.add(defaultName);
            }
          }
        }
        // Check if it's a string
        else if (typeof switchValue.default === "string") {
          // Check if it's a variable reference
          const isVariable = [
            ...customVariables,
            ...customListVariables,
            ...customSwitchCases,
          ].some(
            (otherVar) =>
              otherVar.name === switchValue.default &&
              otherVar.name !== varDef.name,
          );

          if (isVariable) {
            deps.add(switchValue.default);
          }
          // Check if it's a schema field
          else if (isSchemaField(switchValue.default, fieldOptions)) {
            deps.add(switchValue.default);
          }
        }
      }
    }
    graph.variables.set(varDef.name, deps);
    deps.forEach((dep) => {
      if (graph.reverseDeps.has(dep)) {
        graph.reverseDeps.get(dep).add(varDef.name);
      }
    });
  });
};

/**
 * Analyzes a block for dependencies
 */
const analyzeBlockForDeps = (
  block,
  deps,
  customVariables,
  customListVariables,
  customSwitchCases,
  fieldOptions,
  currentVarName = null,
) => {
  if (!block) return;

  if (block.children) {
    block.children.forEach((child) =>
      analyzeBlockForDeps(
        child,
        deps,
        customVariables,
        customListVariables,
        customSwitchCases,
        fieldOptions,
        currentVarName,
      ),
    );
  }

  if (block.field) {
    // Check if field has metadata (new format: {name: "...", _meta: {...}})
    if (block.field && typeof block.field === "object" && block.field._meta) {
      const fieldName = normalizeFieldName(block.field);
      const meta = block.field._meta;

      // Route based on metadata flags to avoid adding wrong dependencies when names collide
      if (meta.isListVariable) {
        deps.add(fieldName);
      } else if (meta.isSwitchCase && fieldName !== currentVarName) {
        deps.add(fieldName);
      } else if (meta.isSwitchCase && fieldName === currentVarName) {
        // Special case: switch case referencing itself
        // Check if it's also a schema field - if so, we need it as a dependency
        // because we're reading from the original schema field
        if (isSchemaField(fieldName, fieldOptions)) {
          deps.add(fieldName);
        }
      } else if (meta.isSchemaField) {
        deps.add(fieldName);
      } else if (meta.isVariable) {
        // Arithmetic variables need to be defined as fields when used in list variable contexts
        deps.add(fieldName);
      } else {
        // Fallback: metadata exists but no flags are set to true
        // Check if it's actually a schema field (the metadata might be incorrect)
        if (isSchemaField(fieldName, fieldOptions)) {
          deps.add(fieldName);
        }
      }
    }
    // Fallback: legacy string-based checking (may add multiple if names collide)
    else {
      // Normalize field to handle both string and object formats
      const fieldName = normalizeFieldName(block.field);
      // Add arithmetic variables as dependencies when used in list variable filters
      if (customVariables.some((v) => v.name === fieldName))
        deps.add(fieldName);
      if (customListVariables.some((v) => v.name === fieldName))
        deps.add(fieldName);
      // For switch cases, don't add self-references as dependencies...
      // UNLESS it's also a schema field (meaning we're reading from the original field)
      const isSwitchCase = customSwitchCases.some((v) => v.name === fieldName);
      const isCurrentVar = fieldName === currentVarName;
      if (isSwitchCase && !isCurrentVar) {
        deps.add(fieldName);
      }
      // Always check if it's a schema field (even if it matches a switch case name)
      if (
        fieldOptions.some((f) => f.value === fieldName || f.label === fieldName)
      ) {
        deps.add(fieldName);
      }
    }
  }

  if (block.value) {
    // Check if value has metadata (new format: {name: "...", _meta: {...}})
    if (
      block.value &&
      typeof block.value === "object" &&
      block.value._meta &&
      block.value.name
    ) {
      const valueName = block.value.name;
      const meta = block.value._meta;

      // Route based on metadata flags to avoid adding wrong dependencies when names collide
      if (meta.isListVariable) {
        deps.add(valueName);
      } else if (meta.isSwitchCase && valueName !== currentVarName) {
        deps.add(valueName);
      } else if (meta.isSwitchCase && valueName === currentVarName) {
        // Special case: switch case referencing itself
        // Check if it's also a schema field - if so, we need it as a dependency
        // because we're reading from the original schema field
        if (isSchemaField(valueName, fieldOptions)) {
          deps.add(valueName);
        }
      } else if (meta.isSchemaField) {
        deps.add(valueName);
      } else if (meta.isVariable) {
        // Arithmetic variables need to be defined as fields when used in list variable contexts
        deps.add(valueName);
      } else {
        // Fallback: metadata exists but no flags are set to true
        // Check if it's actually a schema field (the metadata might be incorrect)
        if (isSchemaField(valueName, fieldOptions)) {
          deps.add(valueName);
        }
      }
    }
    // Fallback: legacy string-based checking
    else {
      // Normalize value to handle both string and object formats
      const normalizedVal = normalizeValue(block.value);
      if (typeof normalizedVal === "string") {
        const value = normalizedVal;
        // Add arithmetic variables as dependencies when used in list variable filters
        if (customVariables.some((v) => v.name === value)) deps.add(value);
        if (customListVariables.some((v) => v.name === value)) deps.add(value);
        // For switch cases, don't add self-references as dependencies...
        // UNLESS it's also a schema field (meaning we're reading from the original field)
        const isSwitchCase = customSwitchCases.some((v) => v.name === value);
        const isCurrentVar = value === currentVarName;
        if (isSwitchCase && !isCurrentVar) deps.add(value);
        // Always check if it's a schema field (even if it matches a switch case name)
        if (fieldOptions.some((f) => f.value === value || f.label === value))
          deps.add(value);
      }
    }
  }
};

/**
 * Calculates dependency levels using topological sort.
 * @param {object} graph - The dependency graph.
 * @param {Set<string>} arithmeticVarNames - Names of arithmetic variables.
 *   These are always inlined at expression-build time, so a dependency on one
 *   does NOT require the dependent variable to be placed in a later $addFields
 *   stage. Passing this set prevents artificial level inflation.
 */
const calculateDependencyLevels = (graph, arithmeticVarNames = new Set()) => {
  const visited = new Set();
  const visiting = new Set();
  const levels = new Map();

  const visit = (node, currentLevel = 0) => {
    if (visiting.has(node)) {
      // Circular dependency detected - assign a high level to break the cycle
      return currentLevel + 10; // Assign high level to process later
    }
    if (visited.has(node)) {
      return Math.max(currentLevel, levels.get(node) || 0);
    }

    visiting.add(node);
    let maxDepLevel = 0;

    const deps = graph.variables.get(node) || new Set();
    for (const dep of deps) {
      if (graph.variables.has(dep)) {
        if (arithmeticVarNames.has(dep)) {
          // Arithmetic vars are inlined: they don't add a stage (+0 not +1).
          // But we still recurse through them so that transitive list-var
          // dependencies (e.g. arith var references $jd_min_prv) are counted.
          maxDepLevel = Math.max(maxDepLevel, visit(dep, currentLevel));
        } else {
          // List vars and switch cases create a real stage boundary.
          maxDepLevel = Math.max(maxDepLevel, visit(dep, currentLevel) + 1);
        }
      }
    }

    visiting.delete(node);
    visited.add(node);
    levels.set(node, maxDepLevel);
    return maxDepLevel;
  };

  // Calculate levels for all variables
  for (const varName of graph.variables.keys()) {
    if (!visited.has(varName)) {
      visit(varName);
    }
  }

  graph.levels = levels;
};

/**
 * Determines what stages are needed in the pipeline
 */
const determineRequiredStages = (dependencyGraph) => {
  const usedFields = dependencyGraph.usedFields;

  return {
    needsInitialProject:
      usedFields.baseFields.size > 0 ||
      usedFields.customVariables.size > 0 ||
      usedFields.switchCases.size > 0,
    needsListStages: usedFields.listVariables.size > 0,
    needsMatchStages: true, // Always include match stages for filters
    needsFinalProject: true, // Always include final project
  };
};

/**
 * Builds the initial project stage for base variables
 */
const buildInitialProjectStage = (
  dependencyGraph,
  customVariables,
  customListVariables,
  customSwitchCases,
  fieldOptions,
) => {
  const project = { objectId: 1, "candidate.jd": 1 };

  // Add base fields only - computed variables will be added in separate $addFields stages
  // Filter out redundant parent paths when children are projected (e.g., exclude "prv_candidates" if "prv_candidates.isdiffpos" is projected)
  const baseFieldsArray = Array.from(dependencyGraph.usedFields.baseFields);
  const fieldsToProject = baseFieldsArray.filter((field) => {
    // Check if any other field is a child of this field
    // If this field has children being projected, exclude this parent path
    return !baseFieldsArray.some((otherField) => {
      return otherField !== field && otherField.startsWith(`${field}.`);
    });
  });

  fieldsToProject.forEach((field) => {
    project[field] = 1;
  });

  // Add dependencies of switch cases that are schema fields
  // This is needed when a switch case reads from and overwrites the same field
  dependencyGraph.usedFields.switchCases.forEach((switchCaseName) => {
    const deps = dependencyGraph.variables.get(switchCaseName);
    if (deps) {
      deps.forEach((dep) => {
        // Check if this dependency is a schema field
        // It might also be a variable name, but if it's a schema field, we need it in the projection
        const isSchemaFieldDep = fieldOptions.some(
          (f) => f.value === dep || f.label === dep,
        );

        if (isSchemaFieldDep) {
          // It's a schema field, add it to the projection
          project[dep] = 1;
        }
      });
    }
  });

  // Add dependencies of list variables that are schema fields
  dependencyGraph.usedFields.listVariables.forEach((listVarName) => {
    const deps = dependencyGraph.variables.get(listVarName);
    if (deps) {
      deps.forEach((dep) => {
        // Check if this dependency is a schema field
        // It might also be a variable name, but if it's a schema field, we need it in the projection
        const isSchemaFieldDep = fieldOptions.some(
          (f) => f.value === dep || f.label === dep,
        );

        if (isSchemaFieldDep) {
          // It's a schema field, add it to the projection
          project[dep] = 1;
        }
      });
    }
  });

  // Note: Level 0 list variables and switch cases are now added via $addFields
  // in buildVariableStagesByLevel to ensure proper stage separation

  // Final pass: Remove parent paths if any of their children are in the project
  // This handles cases where dependencies might conflict with already projected fields
  const allProjectedFields = Object.keys(project);
  const filteredProject = {};

  allProjectedFields.forEach((field) => {
    // Check if any other projected field is a child of this field
    const hasChildProjected = allProjectedFields.some((otherField) => {
      return otherField !== field && otherField.startsWith(`${field}.`);
    });

    // Only add this field if it doesn't have children being projected
    if (!hasChildProjected) {
      filteredProject[field] = project[field];
    }
  });

  return { $project: filteredProject };
};

/**
 * Builds stages for variables (list, arithmetic, switch) in dependency order by level
 */
const buildVariableStagesByLevel = (
  dependencyGraph,
  customVariables,
  customListVariables,
  customSwitchCases,
  fieldOptions,
  additionalFieldsToProject = [],
  annotationMode = false,
) => {
  const stages = [];
  const maxLevel = Math.max(...Array.from(dependencyGraph.levels.values()), 0);
  const materializedListVars = new Set(); // Track which list variables are actually materialized
  const materializedArithmeticVars = new Set(); // Track which arithmetic variables are materialized

  // In annotation mode, arithmetic variables in additionalFieldsToProject must be materialized
  const arithmeticVarsToMaterialize = new Set();
  if (annotationMode) {
    const toProcess = [];
    additionalFieldsToProject.forEach((field) => {
      if (customVariables.some((v) => v.name === field)) {
        arithmeticVarsToMaterialize.add(field);
        toProcess.push(field);
      }
    });

    // Also materialize any arithmetic variables that these depend on
    while (toProcess.length > 0) {
      const current = toProcess.pop();
      const deps = dependencyGraph.variables.get(current);
      if (deps) {
        deps.forEach((dep) => {
          // If this dependency is an arithmetic variable and not already materialized
          if (
            customVariables.some((v) => v.name === dep) &&
            !arithmeticVarsToMaterialize.has(dep)
          ) {
            arithmeticVarsToMaterialize.add(dep);
            toProcess.push(dep);
          }
        });
      }
    }
  }

  // Start from level 0 to include all variables (including those with no dependencies)
  for (let level = 0; level <= maxLevel; level++) {
    // NOTE: Arithmetic variables are USUALLY inlined, never materialized in $addFields
    // EXCEPTION: In annotation mode, if an arithmetic variable is in additionalFieldsToProject,
    // it must be materialized so it can be referenced in the final project stage

    // Build arithmetic variables at this level if they need to be materialized
    const levelArithmeticVars = customVariables.filter((varDef) => {
      const varLevel = dependencyGraph.levels.get(varDef.name) || 0;
      const isUsed = dependencyGraph.usedFields.customVariables.has(
        varDef.name,
      );
      const needsMaterialization = arithmeticVarsToMaterialize.has(varDef.name);
      return varLevel === level && isUsed && needsMaterialization;
    });

    if (levelArithmeticVars.length > 0) {
      const addFields = { $addFields: {} };

      levelArithmeticVars.forEach((varDef) => {
        try {
          const expr = convertArithmeticExpression(
            varDef.variable,
            customVariables,
          );
          if (expr) {
            addFields.$addFields[varDef.name] = expr;
            materializedArithmeticVars.add(varDef.name);
          }
        } catch (error) {
          // Skip invalid arithmetic expression
        }
      });

      if (Object.keys(addFields.$addFields).length > 0) {
        stages.push(addFields);
      }
    }

    // Build switch variables at this level (use $addFields)
    const levelSwitchVars = customSwitchCases.filter(
      (varDef) =>
        (dependencyGraph.levels.get(varDef.name) || 0) === level &&
        dependencyGraph.usedFields.switchCases.has(varDef.name),
    );

    if (levelSwitchVars.length > 0) {
      const addFields = { $addFields: {} };

      levelSwitchVars.forEach((varDef) => {
        try {
          const switchDef = varDef.switchCondition || varDef.switch;
          // switchCondition has structure: { operator: "$switch", value: { cases: [...], default: ... } }
          // convertSwitchExpression expects: { cases: [...], default: ... }
          const switchValue = switchDef?.value || switchDef;
          const switchExpr = convertSwitchExpression(
            switchValue,
            fieldOptions,
            customVariables,
            customListVariables,
            customSwitchCases,
          );
          addFields.$addFields[varDef.name] = switchExpr;
        } catch (error) {
          // Skip invalid switch case
        }
      });

      if (Object.keys(addFields.$addFields).length > 0) {
        stages.push(addFields);
      }
    }

    // Then, build list variables at this level (use $addFields)
    // Always define list variables at their level, regardless of usage count
    const levelListVars = customListVariables.filter((varDef) => {
      const varLevel = dependencyGraph.levels.get(varDef.name) || 0;
      const isUsed = dependencyGraph.usedFields.listVariables.has(varDef.name);
      return varLevel === level && isUsed;
    });

    if (levelListVars.length > 0) {
      const addFields = { $addFields: {} };

      levelListVars.forEach((varDef) => {
        addFields.$addFields[varDef.name] = generateListVariableExpression(
          varDef.listCondition,
          customListVariables,
          dependencyGraph,
          fieldOptions,
          customVariables,
          customSwitchCases,
        );
        // Track that this list variable was materialized
        materializedListVars.add(varDef.name);
      });

      stages.push(addFields);
    }
  }

  // Store materialized variables in the dependency graph for later use
  dependencyGraph.materializedListVars = materializedListVars;
  dependencyGraph.materializedArithmeticVars = materializedArithmeticVars;

  return stages;
};

/**
 * Builds custom block definitions stage (only for blocks used 2+ times)
 * Custom blocks used multiple times are defined as boolean variables to avoid duplication
 */
const buildCustomBlockStage = (
  dependencyGraph,
  schema,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  if (
    !dependencyGraph.customBlockUsage ||
    dependencyGraph.customBlockUsage.size === 0
  ) {
    return null;
  }

  const addFields = { $addFields: {} };

  // Only define blocks that are used 2 or more times
  for (const [blockName, usage] of dependencyGraph.customBlockUsage.entries()) {
    if (usage.count >= 2 && usage.block) {
      // Convert the block's children to a boolean expression
      // Pass null for dependencyGraph to prevent infinite recursion (inline child blocks)
      const blockCondition = convertBlockToMongoExpr(
        usage.block,
        null, // Don't reference custom blocks within custom block definitions
        fieldOptions,
        customVariables,
        customListVariables,
        customSwitchCases,
        null,
        null,
        true, // expressionContext - $expr requires expression syntax
      );

      if (blockCondition && Object.keys(blockCondition).length > 0) {
        // Wrap in $expr to make it a boolean field
        addFields.$addFields[blockName] = { $expr: blockCondition };
      }
    }
  }

  if (Object.keys(addFields.$addFields).length === 0) {
    return null;
  }

  return addFields;
};

/**
 * Extracts simple conditions that can be moved to an early $match stage
 * Simple conditions only reference base fields and use basic operators
 * Respects block atomicity - doesn't split mixed blocks
 * For custom blocks at root, unwraps one level and extracts simple children
 */
const extractEarlyMatchConditions = (
  filters,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  if (!filters || filters.length === 0) {
    return { earlyMatch: {}, remainingFilters: [] };
  }

  const simpleConditions = [];
  const remainingFilters = [];

  filters.forEach((filter, index) => {
    // Check if this is a block at root level (custom or regular)
    if (
      (filter.type === "block" || filter.category === "block") &&
      filter.children &&
      filter.children.length > 0
    ) {
      const parentLogic = (
        filter.logic ||
        filter.operator ||
        "and"
      ).toLowerCase();

      // If this block has isTrue === false, don't unwrap it - keep it intact
      // It needs special handling in the main match stage
      if (filter.isTrue === false) {
        remainingFilters.push(filter);
        return;
      }

      // Check if any child has isTrue === false
      // If so, keep the entire parent block intact to preserve the logical structure
      const hasInvertedChild = filter.children.some(
        (child) => child.isTrue === false,
      );
      if (hasInvertedChild && parentLogic !== "and") {
        remainingFilters.push(filter);
        return;
      }

      const simpleChildren = [];
      const complexChildren = [];

      // Unwrap two levels: root block and its immediate child blocks
      filter.children.forEach((child, childIndex) => {
        // If child is also a block, unwrap it one level
        if (
          (child.type === "block" || child.category === "block") &&
          child.children &&
          child.children.length > 0
        ) {
          // Never unwrap inverted child blocks; keep them in remaining filters
          if (child.isTrue === false) {
            complexChildren.push(child);
            return;
          }

          const childLogic = (
            child.logic ||
            child.operator ||
            "and"
          ).toLowerCase();

          // If logical operators differ, check if the entire block is simple
          // and keep it intact (can't split conditions across different logical operators)
          if (childLogic !== parentLogic) {
            const childBlockIsSimple = isSimpleBlock(
              child,
              fieldOptions,
              customVariables,
              customListVariables,
              customSwitchCases,
            );

            if (childBlockIsSimple) {
              simpleChildren.push(child);
            } else {
              complexChildren.push(child);
            }
          } else {
            // Same logical operator - ALWAYS unwrap to grandchild level and check each individually
            // This ensures we properly unwrap 2 levels (root + imported custom block)
            const simpleGrandchildren = [];
            const complexGrandchildren = [];

            child.children.forEach((grandchild, grandchildIndex) => {
              const isSimple = isSimpleBlock(
                grandchild,
                fieldOptions,
                customVariables,
                customListVariables,
                customSwitchCases,
              );

              if (isSimple) {
                simpleGrandchildren.push(grandchild);
              } else {
                complexGrandchildren.push(grandchild);
              }
            });

            // Add simple grandchildren directly
            simpleChildren.push(...simpleGrandchildren);

            // If there are complex grandchildren, reconstruct child block with only them
            if (complexGrandchildren.length > 0) {
              complexChildren.push({
                ...child,
                children: complexGrandchildren,
              });
            }
          }
        } else {
          // It's a direct condition
          const isSimple = isSimpleBlock(
            child,
            fieldOptions,
            customVariables,
            customListVariables,
            customSwitchCases,
          );

          if (isSimple) {
            simpleChildren.push(child);
          } else {
            complexChildren.push(child);
          }
        }
      });

      // Add simple children directly to early match
      if (simpleChildren.length > 0) {
        simpleConditions.push(...simpleChildren);
      }

      // If there are complex children, reconstruct the block with only complex children
      if (complexChildren.length > 0) {
        const remainingBlock = {
          ...filter,
          children: complexChildren,
        };
        remainingFilters.push(remainingBlock);
      }
    }
    // Check if this is a simple block/condition
    else if (
      isSimpleBlock(
        filter,
        fieldOptions,
        customVariables,
        customListVariables,
        customSwitchCases,
      )
    ) {
      simpleConditions.push(filter);
    } else {
      remainingFilters.push(filter);
    }
  });

  // Convert simple conditions to MongoDB match expression
  let earlyMatch = {};
  if (simpleConditions.length > 0) {
    earlyMatch = convertFiltersToMatch(
      simpleConditions,
      null, // No dependency graph needed for simple conditions
      {}, // No schema needed
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
    );
  }

  return { earlyMatch, remainingFilters };
};

/**
 * Checks if a block/condition is simple (only uses base fields and basic operators)
 * Treats blocks as atomic - if any child is not simple, the whole block is not simple
 */
const isSimpleBlock = (
  block,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  if (!block) return false;

  // Blocks with isTrue === false require special handling ($nor wrapping)
  // and cannot be extracted to early match stage
  if (block.isTrue === false) {
    return false;
  }

  // If it has children, check all children recursively
  if (block.children && block.children.length > 0) {
    return block.children.every((child) =>
      isSimpleBlock(
        child,
        fieldOptions,
        customVariables,
        customListVariables,
        customSwitchCases,
      ),
    );
  }

  // For leaf conditions, check if simple
  return isSimpleCondition(
    block,
    fieldOptions,
    customVariables,
    customListVariables,
    customSwitchCases,
  );
};

const isSimpleCondition = (
  condition,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  if (!condition || !condition.field || !condition.operator) {
    return false;
  }

  // Normalize field to handle both string and object formats
  const fieldName = normalizeFieldName(condition.field);
  const { operator, value, fieldType } = condition;

  // Check if operator is a basic operator (MongoDB operators and friendly names)
  const basicOperators = [
    "$eq",
    "equals",
    "=",
    "==",
    "$ne",
    "not equals",
    "!=",
    "<>",
    "$gt",
    "greater than",
    ">",
    "$gte",
    "greater than or equal to",
    ">=",
    "$lt",
    "less than",
    "<",
    "$lte",
    "less than or equal to",
    "<=",
    "$in",
    "in",
    "$exists",
    "exists",
  ];
  if (!basicOperators.includes(operator)) {
    return false;
  }

  // Check field type
  if (fieldType) {
    // Explicit field type - only 'schema' is simple
    if (fieldType !== "schema") {
      return false;
    }
  }
  // Check if field has metadata (new format: {name: "...", _meta: {...}})
  else if (
    condition.field &&
    typeof condition.field === "object" &&
    condition.field._meta
  ) {
    const meta = condition.field._meta;

    // Only schema fields are simple
    if (meta.isSchemaField) {
      // Continue to schema field validation below
    } else {
      // It's a variable/list variable/switch case - not simple
      return false;
    }
  }
  // Fallback: check by name (may be incorrect if names collide)
  else {
    // Implicit field type - check if it's a computed variable or list
    if (customVariables.some((v) => v.name === fieldName)) {
      return false; // Arithmetic variable - not simple
    }
    if (customListVariables.some((v) => v.name === fieldName)) {
      return false; // List variable - not simple
    }
    if (customSwitchCases.some((v) => v.name === fieldName)) {
      return false; // Switch case - not simple
    }
  }

  // Check if field exists in schema
  let fieldDef = fieldOptions.find(
    (f) => f.value === fieldName || f.label === fieldName,
  );

  // For array subfields (e.g., "fp_hists.procstatus"), also try just the field name ("procstatus")
  if (!fieldDef && fieldName.includes(".")) {
    const simpleFieldName = fieldName.split(".").pop();
    fieldDef = fieldOptions.find(
      (f) => f.value === simpleFieldName || f.label === simpleFieldName,
    );
  }

  if (!fieldDef && fieldOptions.length > 0) {
    // For nested fields (e.g., "candidate.rb"), check if the parent path exists
    if (fieldName.includes(".")) {
      const parts = fieldName.split(".");
      // Check progressively: "candidate.rb" -> check "candidate" or "candidate.rb"
      let found = false;
      for (let i = parts.length; i > 0; i--) {
        const partialPath = parts.slice(0, i).join(".");
        if (
          fieldOptions.some(
            (f) => f.value === partialPath || f.label === partialPath,
          )
        ) {
          found = true;
          break;
        }
      }
      if (!found) {
        return false; // Neither full path nor parent path found in schema
      }
    } else {
      // Simple field not found in fieldOptions
      return false;
    }
  }
  // If fieldOptions is empty, we can't validate, so assume it might be valid
  // (This happens in tests without full field metadata)

  // Check if value references computed fields
  if (typeof value === "string") {
    // Allow field references to other schema fields (these are valid in $expr)
    const valueFieldDef = fieldOptions.find(
      (f) => f.value === value || f.label === value,
    );
    if (valueFieldDef) {
      // It's a reference to another schema field - this is OK for early match
      return true;
    }

    // Check if value is a variable reference (not allowed)
    if (customVariables.some((v) => v.name === value)) {
      return false;
    }
    if (customListVariables.some((v) => v.name === value)) {
      return false;
    }
    if (customSwitchCases.some((v) => v.name === value)) {
      return false;
    }
  }

  return true;
};

/**
 * Builds match stages for filters
 */
const buildMatchStages = (
  filters,
  dependencyGraph,
  schema,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  const stages = [];

  // Convert filters to MongoDB match conditions
  const matchConditions = convertFiltersToMatch(
    filters,
    dependencyGraph,
    schema,
    fieldOptions,
    customVariables,
    customListVariables,
    customSwitchCases,
  );

  if (matchConditions && Object.keys(matchConditions).length > 0) {
    stages.push({ $match: matchConditions });
  }

  return stages;
};

/**
 * Builds the final project stage
 *
 * Annotation mode behavior:
 * - When annotations exist: Project mandatory fields + annotation fields.
 *   Annotation fields are available in final stage for use by higher-level code.
 * - Without annotations: Project mandatory fields + all used fields and variables.
 */
const buildFinalProjectStage = (
  dependencyGraph,
  additionalFieldsToProject,
  fieldOptions,
  annotationMode = false,
) => {
  const hasAnnotations = annotationMode && additionalFieldsToProject.length > 0;
  const project = { objectId: 1, "candidate.jd": 1 };

  if (hasAnnotations) {
    // Annotation mode: project mandatory fields + materialized variables needed for annotations
    const materializedListVars =
      dependencyGraph.materializedListVars || new Set();
    const materializedArithmeticVars =
      dependencyGraph.materializedArithmeticVars || new Set();

    // Project materialized list variables that are used
    dependencyGraph.usedFields.listVariables.forEach((varName) => {
      if (materializedListVars.has(varName)) {
        project[varName] = 1;
      }
    });

    // Project materialized arithmetic variables (from additionalFieldsToProject)
    materializedArithmeticVars.forEach((varName) => {
      project[varName] = 1;
    });

    // Project switch cases that are used
    dependencyGraph.usedFields.switchCases.forEach((varName) => {
      project[varName] = 1;
    });

    // Also project base fields that are used as dependencies
    dependencyGraph.usedFields.baseFields.forEach((field) => {
      project[field] = 1;
    });
  } else {
    // Non-annotation mode: project all used fields and variables

    // Add used base fields, filtering out child paths when parent is projected
    const baseFieldsArray = Array.from(dependencyGraph.usedFields.baseFields);
    const fieldsToProject = baseFieldsArray.filter((field) => {
      return !baseFieldsArray.some((otherField) => {
        return otherField !== field && field.startsWith(`${otherField}.`);
      });
    });

    fieldsToProject.forEach((field) => {
      project[field] = 1;
    });

    // Project materialized list variables
    const materializedListVars =
      dependencyGraph.materializedListVars || new Set();
    dependencyGraph.usedFields.listVariables.forEach((varName) => {
      if (materializedListVars.has(varName)) {
        project[varName] = 1;
      }
    });

    // Project switch cases
    dependencyGraph.usedFields.switchCases.forEach((varName) => {
      project[varName] = 1;
    });

    // Add additional fields
    additionalFieldsToProject.forEach((field) => {
      project[field] = 1;
    });
  }

  // Remove parent paths if their children are in the project
  const allProjectedFields = Object.keys(project);
  const filteredProject = {};

  allProjectedFields.forEach((field) => {
    const hasChildProjected = allProjectedFields.some((otherField) => {
      return otherField !== field && otherField.startsWith(`${field}.`);
    });

    if (!hasChildProjected) {
      filteredProject[field] = project[field];
    }
  });

  return { $project: filteredProject };
};

/**
 * Converts arithmetic expression to MongoDB expression with variable inlining
 * @export
 */
export const convertArithmeticExpression = (
  variableDefinition,
  customVariables = [],
  processedVars = new Set(),
) => {
  if (!variableDefinition || !variableDefinition.includes("=")) {
    return null;
  }

  const expression = variableDefinition.split("=")[1].trim();

  try {
    // First, inline any variable references in the expression
    let inlinedExpression = inlineVariablesInExpression(
      expression,
      customVariables,
      processedVars,
    );
    return latexToMongoConverter.convertToMongo(inlinedExpression);
  } catch (error) {
    return null;
  }
};

/**
 * Inlines variable references in an expression recursively
 * Variables prefixed with $ (e.g., $varname) are treated as MongoDB field references and NOT inlined
 */
const inlineVariablesInExpression = (
  expression,
  customVariables,
  processedVars = new Set(),
) => {
  if (!expression || typeof expression !== "string") {
    return expression;
  }

  let result = expression;

  // Find all variable references (word characters that are not numbers)
  const varPattern = /\b([a-zA-Z_][a-zA-Z0-9_]*)\b/g;
  const matches = [...result.matchAll(varPattern)];

  for (const match of matches) {
    const varName = match[1];
    const matchIndex = match.index;

    // Skip if it's a number or if we've already processed this variable (to prevent infinite recursion)
    if (!isNaN(varName) || processedVars.has(varName)) {
      continue;
    }

    // Check if this variable is preceded by a $ symbol (MongoDB field reference)
    // If so, don't inline it - it should be materialized as a field
    const charBefore = matchIndex > 0 ? result[matchIndex - 1] : "";
    if (charBefore === "$") {
      continue; // Skip inlining - this is a field reference like $varName
    }

    // Check if it's a custom variable
    const varDef = customVariables.find((v) => v.name === varName);
    if (varDef && varDef.variable) {
      // Prevent infinite recursion
      processedVars.add(varName);

      // Get the variable's expression
      const varExpr = varDef.variable.split("=")[1]?.trim();
      if (varExpr) {
        // Recursively inline variables in the variable's expression
        const inlinedVarExpr = inlineVariablesInExpression(
          varExpr,
          customVariables,
          processedVars,
        );

        // Replace the variable reference with the inlined expression, wrapped in parentheses
        // Use a more precise regex that matches word boundaries but not after $
        result = result.replace(
          new RegExp(`(?<!\\$)\\b${varName}\\b`, "g"),
          `(${inlinedVarExpr})`,
        );
      }

      processedVars.delete(varName);
    }
  }

  return result;
};

/**
 * Resolves a field name to a MongoDB reference, using $$this for array subfields
 */
const resolveFieldReference = (fieldName, arrayField) => {
  if (!arrayField) return `$${fieldName}`;
  if (fieldName.startsWith(`${arrayField}.`)) {
    return `$$this.${fieldName.substring(arrayField.length + 1)}`;
  }
  return `$${fieldName}`;
};

/**
 * Replaces references to arrayField with $$this in a MongoDB expression
 */
const replaceArrayFieldInExpr = (expr, arrayField) => {
  if (!expr || !arrayField) return expr;

  if (typeof expr === "string") {
    // Replace $arrayField.subfield with $$this.subfield
    if (expr.startsWith(`$${arrayField}.`)) {
      const subfield = expr.substring(arrayField.length + 2); // +2 for $ and .
      return `$$this.${subfield}`;
    }
    return expr;
  }

  if (Array.isArray(expr)) {
    return expr.map((item) => replaceArrayFieldInExpr(item, arrayField));
  }

  if (typeof expr === "object") {
    const newObj = {};
    for (const key in expr) {
      newObj[key] = replaceArrayFieldInExpr(expr[key], arrayField);
    }
    return newObj;
  }

  return expr;
};

/**
 * Inlines arithmetic variables in MongoDB expressions recursively
 */
const inlineVariablesInMongoExpr = (
  expr,
  customVariables,
  processedVars = new Set(),
  arrayField = null,
) => {
  if (!expr) return expr;

  if (typeof expr === "string") {
    // Check if it's a field/variable reference like "$varName" or "$varName.field"
    if (expr.startsWith("$")) {
      const refName = expr.substring(1);

      // Check if this is a reference to the array field being mapped over (e.g., $10days.magpsf)
      if (arrayField && refName.startsWith(`${arrayField}.`)) {
        // Replace $arrayField.subfield with $$this.subfield
        const subfield = refName.substring(arrayField.length + 1);
        return `$$this.${subfield}`;
      }

      // Check if it's a variable reference ($$varName in some contexts, but here $varName)
      const arithVar = customVariables.find((v) => v.name === refName);
      if (arithVar && !processedVars.has(refName)) {
        processedVars.add(refName);
        const inlined = convertArithmeticExpression(
          arithVar.variable,
          customVariables,
          processedVars,
        );
        processedVars.delete(refName);
        // If we're in an array context, replace arrayField references in the inlined expression
        if (arrayField && inlined) {
          return replaceArrayFieldInExpr(inlined, arrayField);
        }
        return inlined;
      }
    }
    return expr;
  }

  if (Array.isArray(expr)) {
    return expr.map((item) =>
      inlineVariablesInMongoExpr(
        item,
        customVariables,
        processedVars,
        arrayField,
      ),
    );
  }

  if (typeof expr === "object") {
    const newObj = {};
    for (const key in expr) {
      newObj[key] = inlineVariablesInMongoExpr(
        expr[key],
        customVariables,
        processedVars,
        arrayField,
      );
    }
    return newObj;
  }

  return expr;
};

/**
 * Helper to check if a field name is a schema field
 * Handles nested fields by checking partial paths
 */
const isSchemaField = (fieldName, fieldOptions) => {
  if (!fieldName || typeof fieldName !== "string") {
    return false;
  }

  // Check exact match first (works when fieldOptions is populated)
  if (fieldOptions && fieldOptions.length > 0) {
    if (
      fieldOptions.some((f) => f.value === fieldName || f.label === fieldName)
    ) {
      return true;
    }

    // For nested fields (e.g., "candidate.magap"), check partial paths
    if (fieldName.includes(".")) {
      const parts = fieldName.split(".");
      // Check progressively: "candidate.magap" -> check "candidate" or "candidate.magap"
      for (let i = parts.length; i > 0; i--) {
        const partialPath = parts.slice(0, i).join(".");
        if (
          fieldOptions.some(
            (f) => f.value === partialPath || f.label === partialPath,
          )
        ) {
          return true;
        }
      }
    }
  }

  // Fallback: If it looks like a schema field path, assume it is
  // Common prefixes for schema fields in this application
  if (fieldName.includes(".")) {
    const prefix = fieldName.split(".")[0];
    const knownPrefixes = [
      "candidate",
      "annotations",
      "cross_matches",
      "fp_hists",
      "prv_candidates",
    ];
    if (knownPrefixes.includes(prefix)) {
      return true;
    }
  }

  return false;
};

/**
 * Resolves a switch case then/default value to a MongoDB expression.
 * Handles both new {name, _meta} format and legacy string format.
 */
const resolveSwitchCaseValue = (
  val,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  // Object with metadata (new format: {name: "...", _meta: {...}})
  if (val && typeof val === "object" && val._meta && val.name) {
    const name = val.name;
    const meta = val._meta;
    if (meta.isSwitchCase || meta.isListVariable || meta.isSchemaField) {
      return `$${name}`;
    }
    if (meta.isVariable) {
      const arithVar = customVariables.find((v) => v.name === name);
      if (arithVar) {
        return convertArithmeticExpression(arithVar.variable, customVariables);
      }
      return name;
    }
    // Fallback: check if it's actually a schema field
    if (isSchemaField(name, fieldOptions)) return `$${name}`;
    return isNaN(name) ? name : parseFloat(name);
  }
  // String (legacy format)
  if (typeof val === "string") {
    // Arithmetic variable → inline expression
    const arithVar = customVariables.find((v) => v.name === val);
    if (arithVar) {
      return convertArithmeticExpression(arithVar.variable, customVariables);
    }
    // Other variable types (list variable, switch case) → field reference
    if (
      customListVariables.find((v) => v.name === val) ||
      customSwitchCases.find((v) => v.name === val)
    ) {
      return `$${val}`;
    }
    // Schema field
    if (isSchemaField(val, fieldOptions)) return `$${val}`;
    // Literal value
    return isNaN(val) ? val : parseFloat(val);
  }
  // Fallback: number, boolean, etc.
  return val;
};

/**
 * Unwraps $expr wrappers to get pure aggregation expressions
 * This is needed for contexts like $switch where expressions should not be wrapped
 */
const unwrapExprForAggregation = (condition) => {
  if (!condition || typeof condition !== "object") return condition;
  if (condition.$expr) return condition.$expr;
  for (const op of ["$and", "$or", "$nor"]) {
    if (Array.isArray(condition[op])) {
      return { [op]: condition[op].map(unwrapExprForAggregation) };
    }
  }
  return condition;
};

const convertSwitchExpression = (
  switchValue,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  if (!switchValue || !switchValue.cases || switchValue.cases.length === 0) {
    throw new Error(
      `Invalid switch expression: missing or empty cases for switch variable`,
    );
  }

  const branches = [];

  switchValue.cases.forEach((caseItem, index) => {
    if (caseItem.block && caseItem.then) {
      let condition = convertBlockToMongoExpr(
        caseItem.block,
        null, // dependencyGraph not available in switch expression context
        fieldOptions,
        customVariables,
        customListVariables,
        customSwitchCases,
        null, // arrayField
        null, // subFieldOptions
        true, // expressionContext - use expression syntax for $switch
      );

      // Unwrap $expr for switch case context (in case any conditions still have it)
      // MongoDB $switch expects unwrapped aggregation expressions in the case field
      condition = unwrapExprForAggregation(condition);

      const thenValue = resolveSwitchCaseValue(
        caseItem.then,
        fieldOptions,
        customVariables,
        customListVariables,
        customSwitchCases,
      );

      branches.push({
        case: condition,
        then: thenValue,
      });
    }
  });

  const switchExpr = {
    $switch: {
      branches,
    },
  };

  if (switchValue.default !== undefined && switchValue.default !== null) {
    switchExpr.$switch.default = resolveSwitchCaseValue(
      switchValue.default,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
    );
  }

  return switchExpr;
};

const getBooleanSwitch = (condition, value) => {
  if (typeof value === "boolean") return value;

  if (value && typeof value === "object" && value.children) {
    for (const key of [
      "booleanSwitch",
      "isTrue",
      "switchValue",
      "booleanValue",
    ]) {
      if (condition[key] !== undefined) return condition[key];
    }
    if (condition.not !== undefined) return !condition.not;
    if (condition.negate !== undefined) return !condition.negate;
    return true;
  }

  return condition?.booleanSwitch ?? true;
};

const parseNumberIfNeeded = (value) => {
  if (typeof value === "string" && !isNaN(value) && !isNaN(parseFloat(value))) {
    return parseFloat(value);
  }
  return value;
};

/**
 * Generates MongoDB expression for list variables
 */
const generateListVariableExpression = (
  listCondition,
  customListVariables,
  dependencyGraph,
  fieldOptions,
  customVariables,
  customSwitchCases,
) => {
  if (!listCondition) return null;

  const { operator, field, value, subField, subFieldOptions } = listCondition;
  switch (operator) {
    case "$anyElementTrue":
      if (value && value.children) {
        const condition = convertBlockToMongoExpr(
          { children: value.children },
          null, // dependencyGraph not available in list condition context
          fieldOptions,
          customVariables,
          customListVariables,
          customSwitchCases,
          field, // arrayField
          subFieldOptions, // array subFieldOptions
        );
        if (condition && Object.keys(condition).length > 0) {
          return {
            $anyElementTrue: {
              $map: {
                input: { $ifNull: [`$${field}`, []] },
                in: condition,
              },
            },
          };
        }
      }
      return { $anyElementTrue: { $ifNull: [`$${field}`, []] } };

    case "$allElementTrue":
      if (value && value.children) {
        const condition = convertBlockToMongoExpr(
          { children: value.children },
          null, // dependencyGraph not available in list condition context
          fieldOptions,
          customVariables,
          customListVariables,
          customSwitchCases,
          field, // arrayField,
          subFieldOptions, // array subFieldOptions
        );
        if (condition && Object.keys(condition).length > 0) {
          return {
            $allElementTrue: {
              $map: {
                input: { $ifNull: [`$${field}`, []] },
                in: condition,
              },
            },
          };
        }
      }
      return { $allElementTrue: { $ifNull: [`$${field}`, []] } };

    case "$filter":
      if (value && value.children) {
        const condition = convertBlockToMongoExpr(
          { children: value.children },
          null, // dependencyGraph not available in list condition context
          fieldOptions,
          customVariables,
          customListVariables,
          customSwitchCases,
          field, // arrayField
          subFieldOptions, // array subFieldOptions
        );
        return {
          $filter: {
            input: `$${field}`,
            cond: condition,
          },
        };
      }
      return { $ifNull: [`$${field}`, []] };

    case "$map":
      if (value && value.mapExpression) {
        const inlinedMapExpression = inlineVariablesInMongoExpr(
          value.mapExpression,
          customVariables,
          new Set(),
          field,
        );
        // Only create $map if the inlined expression is valid
        if (
          inlinedMapExpression &&
          (typeof inlinedMapExpression === "object" ||
            typeof inlinedMapExpression === "string")
        ) {
          return {
            $map: {
              input: { $ifNull: [`$${field}`, []] },
              in: inlinedMapExpression,
            },
          };
        }
      }
      return { $ifNull: [`$${field}`, []] };

    case "$min":
    case "$max":
    case "$avg":
    case "$sum":
    case "$stdDevPop": {
      const fieldRef = subField ? `$${field}.${subField}` : `$${field}`;
      return { [operator]: fieldRef };
    }

    case "$median": {
      const fieldRef = subField ? `$${field}.${subField}` : `$${field}`;
      return { $median: { input: fieldRef, method: "approximate" } };
    }

    case "$size":
      return { $size: { $ifNull: [`$${field}`, []] } };

    default:
      return { $ifNull: [`$${field}`, []] };
  }
};

/**
 * Converts filters to MongoDB match conditions
 */
const convertFiltersToMatch = (
  filters,
  dependencyGraph,
  schema,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  if (!filters || filters.length === 0) {
    return {};
  }

  const conditions = [];

  filters.forEach((filter) => {
    const condition = convertBlockToMongoExpr(
      filter,
      dependencyGraph,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
    );
    if (condition && Object.keys(condition).length > 0) {
      conditions.push(condition);
    }
  });

  if (conditions.length === 0) {
    return {};
  }

  if (conditions.length === 1) {
    return conditions[0];
  }

  return { $and: conditions };
};

/**
 * Converts a block to MongoDB expression
 */
const convertBlockToMongoExpr = (
  block,
  dependencyGraph,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
  arrayField = null,
  subFieldOptions = null,
  expressionContext = false,
) => {
  if (!block) {
    return {};
  }

  // If this is a custom block that's been defined (used 2+ times), reference it by name
  if (block.customBlockName && dependencyGraph?.customBlockUsage) {
    const usage = dependencyGraph.customBlockUsage.get(block.customBlockName);
    if (usage && usage.count >= 2) {
      // Return a simple field reference with the boolean value
      const fieldValue = block.isTrue !== false;
      return { [block.customBlockName]: fieldValue };
    }
  }

  if (block.type === "condition" || block.category === "condition") {
    return convertConditionToMongoExpr(
      block,
      dependencyGraph,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
      arrayField,
      subFieldOptions,
      expressionContext,
    );
  }

  if (!block.children || block.children.length === 0) {
    return {};
  }

  const conditions = [];
  const args = [
    dependencyGraph,
    fieldOptions,
    customVariables,
    customListVariables,
    customSwitchCases,
    arrayField,
    subFieldOptions,
    expressionContext,
  ];

  block.children.forEach((child) => {
    const converter =
      child.category === "block" || child.type === "block"
        ? convertBlockToMongoExpr
        : convertConditionToMongoExpr;
    const result = converter(child, ...args);
    if (result && Object.keys(result).length > 0) {
      conditions.push(result);
    }
  });

  if (conditions.length === 0) {
    return {};
  }

  let result;
  if (conditions.length === 1) {
    result = conditions[0];
  } else {
    const logic = (block.logic || "and").toLowerCase();
    if (logic === "or") {
      result = { $or: conditions };
    } else {
      result = { $and: conditions };
    }
  }

  // Handle blocks with isTrue === false (inverted logic)
  // For custom blocks defined as variables (usage.count >= 2), this is already handled above
  if (block.isTrue === false) {
    // For custom blocks, only apply $nor if NOT defined as a variable (used < 2 times)
    if (block.customBlockName) {
      const usage = dependencyGraph?.customBlockUsage?.get(
        block.customBlockName,
      );
      if (!usage || usage.count < 2) {
        // Wrap the result in $nor to invert the logic
        return { $nor: [result] };
      }
    } else {
      // For non-custom blocks, always apply $nor to invert the logic
      return { $nor: [result] };
    }
  }

  return result;
};

/**
 * Converts a condition to MongoDB expression
 */
const convertConditionToMongoExpr = (
  condition,
  dependencyGraph,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
  arrayField = null,
  subFieldOptions = null,
  expressionContext = false,
) => {
  const operator = condition.operator;
  // Normalize field to handle both string and object formats
  const field = normalizeFieldName(condition.field);
  const fieldType = condition.fieldType;
  const value = condition.value;
  const booleanSwitch = condition.booleanSwitch;

  // Special handling for MongoDB expression operators ($expr, $filter)
  // These operators wrap raw MongoDB expressions and should pass through as-is
  if (operator === "$expr" && value && typeof value === "object") {
    return { $expr: value };
  }
  if (operator === "$filter" && value && typeof value === "object") {
    // For $filter, if there's a field, treat it as the input
    // The value should contain the filter spec
    if (field && value.cond) {
      return {
        $expr: {
          $filter: {
            input: `$${field}`,
            cond: value.cond,
          },
        },
      };
    }
    // If value is already a complete $filter spec, pass it through in $expr
    if (value.input || value.cond) {
      return { $expr: value };
    }
  }

  if (!field || !operator) {
    return {};
  }

  // If fieldType is explicitly set, use it to determine field resolution
  if (fieldType) {
    let listVar, arithVar, switchVar;
    switch (fieldType) {
      case "listVariable":
        listVar = customListVariables.find((v) => v.name === field);
        if (listVar) {
          return convertListVariableCondition(
            listVar,
            operator,
            value,
            fieldOptions,
            customVariables,
            customListVariables,
            customSwitchCases,
            field,
            subFieldOptions,
            condition,
            dependencyGraph,
          );
        }
        break;
      case "variable":
        arithVar = customVariables.find((v) => v.name === field);
        if (arithVar) {
          return convertArithmeticVariableCondition(
            arithVar,
            operator,
            value,
            arrayField,
            customVariables,
          );
        }
        break;
      case "switchCase":
        switchVar = customSwitchCases.find((v) => v.name === field);
        if (switchVar) {
          return convertSwitchVariableCondition(switchVar, operator, value);
        }
        break;
      case "schema":
      default:
        return convertSchemaFieldCondition(
          field,
          operator,
          value,
          fieldOptions,
          customVariables,
          customListVariables,
          customSwitchCases,
          arrayField,
          subFieldOptions,
          expressionContext,
          condition,
        );
    }
  }

  // Check if field has metadata (new format: {name: "...", _meta: {...}})
  // Use metadata to determine exact field type when available (solves name collision issues)
  if (
    condition.field &&
    typeof condition.field === "object" &&
    condition.field._meta
  ) {
    const meta = condition.field._meta;

    // Route based on metadata flags - check in priority order
    if (meta.isSwitchCase) {
      const switchVar = customSwitchCases.find((v) => v.name === field);
      if (switchVar) {
        return convertSwitchVariableCondition(switchVar, operator, value);
      }
    }

    if (meta.isListVariable) {
      const listVar = customListVariables.find((v) => v.name === field);
      if (listVar) {
        return convertListVariableCondition(
          listVar,
          operator,
          value,
          fieldOptions,
          customVariables,
          customListVariables,
          customSwitchCases,
          field,
          subFieldOptions,
          condition,
          dependencyGraph,
        );
      }
    }

    if (meta.isVariable) {
      const arithVar = customVariables.find((v) => v.name === field);
      if (arithVar) {
        return convertArithmeticVariableCondition(
          arithVar,
          operator,
          value,
          arrayField,
          customVariables,
        );
      }
    }

    if (meta.isSchemaField) {
      return convertSchemaFieldCondition(
        field,
        operator,
        value,
        fieldOptions,
        customVariables,
        customListVariables,
        customSwitchCases,
        arrayField,
        subFieldOptions,
        expressionContext,
        condition,
      );
    }
  }

  // Fallback to legacy precedence-based resolution if fieldType is not set and no metadata
  // Handle list variables
  const listVar = customListVariables.find((v) => v.name === field);
  if (listVar) {
    return convertListVariableCondition(
      listVar,
      operator,
      value,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
      field,
      null,
      condition,
      dependencyGraph,
    );
  }

  // Handle arithmetic variables
  const arithVar = customVariables.find((v) => v.name === field);
  if (arithVar) {
    return convertArithmeticVariableCondition(
      arithVar,
      operator,
      value,
      arrayField,
      customVariables,
    );
  }

  // Check if this is a schema field first (prefer regular fields over switch cases)
  const fieldDef = fieldOptions.find(
    (f) => f.value === field || f.label === field,
  );
  if (fieldDef) {
    return convertSchemaFieldCondition(
      field,
      operator,
      value,
      fieldOptions,
      customVariables,
      customListVariables,
      customSwitchCases,
      arrayField,
      subFieldOptions,
      expressionContext,
      condition,
    );
  }

  // Handle switch cases (only if not a schema field)
  const switchVar = customSwitchCases.find((v) => v.name === field);
  if (switchVar) {
    return convertSwitchVariableCondition(switchVar, operator, value);
  }

  // Fallback to schema field handling if nothing else matches
  return convertSchemaFieldCondition(
    field,
    operator,
    value,
    fieldOptions,
    customVariables,
    customListVariables,
    customSwitchCases,
    arrayField,
    subFieldOptions,
    expressionContext,
    condition,
  );
};

/**
 * Converts list variable condition. Different from list variable creation.
 */
const convertListVariableCondition = (
  listVar,
  operator,
  value,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
  field,
  subFieldOptions,
  condition,
  dependencyGraph = null,
) => {
  let compareValue = parseValueForComparison(
    value,
    customVariables,
    customSwitchCases,
    customListVariables,
    fieldOptions,
    null, // arrayField - not in array context for list variables
    subFieldOptions, // Pass subFieldOptions so subfield references can be resolved
  );

  // If value is undefined or empty string AND this is a boolean-type variable, check for boolean switch properties
  if (
    (compareValue === undefined ||
      (typeof compareValue === "string" && compareValue.trim() === "")) &&
    condition &&
    (listVar?.listCondition?.operator === "$anyElementTrue" ||
      listVar?.listCondition?.operator === "$allElementTrue")
  ) {
    compareValue = getBooleanSwitch(condition, value);
  }

  // For list variables with $anyElementTrue or $allElementTrue, handle boolean comparisons
  // Only convert to boolean for equality checks, not for numeric comparisons
  if (
    (listVar?.listCondition?.operator === "$anyElementTrue" ||
      listVar?.listCondition?.operator === "$allElementTrue") &&
    (operator === "$eq" || operator === "equals")
  ) {
    if (compareValue === "true") {
      compareValue = true;
    } else if (compareValue === "false") {
      compareValue = false;
    }
    // If compareValue is already a boolean (from getBooleanSwitch), leave it as-is
  }

  // Skip condition if value is null or empty string
  // For boolean variables, compareValue should be a boolean at this point
  // Don't skip if compareValue is a boolean (including false)
  if (
    compareValue === null ||
    (typeof compareValue === "string" && compareValue.trim() === "") ||
    (compareValue === undefined &&
      listVar?.listCondition?.operator !== "$anyElementTrue" &&
      listVar?.listCondition?.operator !== "$allElementTrue")
  ) {
    // Allow boolean false values through
    if (typeof compareValue !== "boolean") {
      return {};
    }
  }

  // Always reference the field name (it should be defined in $addFields)
  return makeFieldCondition(listVar.name, operator, compareValue);
};

/**
 * Converts switch variable condition
 */
const convertSwitchVariableCondition = (switchVar, operator, value) => {
  return makeFieldCondition(
    switchVar.name,
    operator,
    parseNumberIfNeeded(value),
  );
};

/**
 * Converts arithmetic variable condition
 */
const convertArithmeticVariableCondition = (
  arithVar,
  operator,
  value,
  arrayField = null,
  customVariables = [],
) => {
  // Skip condition if value is empty or invalid
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    (typeof value === "string" && value.trim() === "")
  ) {
    return {};
  }

  const compareValue = !isNaN(value) ? parseFloat(value) : value;

  // Skip condition if compareValue is NaN (invalid number)
  if (typeof compareValue === "number" && isNaN(compareValue)) {
    return {};
  }

  try {
    let expr = convertArithmeticExpression(arithVar.variable, customVariables);
    if (!expr) throw new Error("Invalid expression");

    // Validate the converted expression doesn't contain null/undefined values
    const hasInvalidValues = (obj) => {
      if (obj === null || obj === undefined) return true;
      if (typeof obj === "object") {
        if (Array.isArray(obj)) {
          return obj.some(hasInvalidValues);
        }
        return Object.values(obj).some(hasInvalidValues);
      }
      return false;
    };

    if (hasInvalidValues(expr)) {
      throw new Error("Expression contains invalid null/undefined values");
    }

    // If arrayField is provided, replace $arrayField with $$this in the expression
    if (arrayField) {
      expr = replaceArrayFieldInExpr(expr, arrayField);

      // When in array context (anyElementTrue/allElementTrue), return expression directly without $expr
      // because we're already inside an aggregation expression context
      return makeExprArrayCondition(expr, operator, compareValue);
    }

    // For $match context, wrap in $expr
    return { $expr: makeExprArrayCondition(expr, operator, compareValue) };
  } catch (error) {
    // Fall back to the old way
    return makeFieldCondition(arithVar.name, operator, compareValue);
  }
};

/**
 * Converts schema field condition
 */
const convertSchemaFieldCondition = (
  field,
  operator,
  value,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
  arrayField = null,
  subFieldOptions = null,
  expressionContext = false,
  condition = null,
) => {
  const fieldDef = fieldOptions.find(
    (f) => f.value === field || f.label === field,
  );
  const fieldType = fieldDef?.type || "string";

  const compareValue = parseValueForComparison(
    value,
    customVariables,
    customSwitchCases,
    customListVariables,
    fieldOptions,
    arrayField,
    subFieldOptions, // Pass subFieldOptions so subfieldreferences can be resolved
  );

  // Type-aware value parsing
  let processedValue = parseNumberIfNeeded(compareValue);

  // For string fields with eq/ne operators, ensure value is a string
  if (
    fieldType === "string" &&
    (operator === "$eq" ||
      operator === "equals" ||
      operator === "$ne" ||
      operator === "not equals")
  ) {
    if (typeof processedValue === "number") {
      processedValue = String(processedValue);
    }
  }

  // Check if processedValue is a MongoDB expression (object with operators like $add, $subtract, etc.)
  // If so, we need to use $expr to compare
  const isMongoExpression =
    processedValue &&
    typeof processedValue === "object" &&
    !Array.isArray(processedValue);

  // If arrayField is provided, we're in a $filter/$map context and need expression format
  if (arrayField) {
    let fieldExpression;
    if (field.startsWith(`${arrayField}.`)) {
      // Field is a subfield of the array, use $$this
      const fieldReference = field.substring(arrayField.length + 1);
      fieldExpression = `$$this.${fieldReference}`;
    } else {
      // Field is from the root document, use $field
      fieldExpression = `$${field}`;
    }

    return makeExprArrayCondition(fieldExpression, operator, processedValue);
  }

  // If expressionContext is true (e.g., inside $switch), use aggregation expression syntax
  if (expressionContext) {
    return makeExprArrayCondition(`$${field}`, operator, processedValue);
  }

  // Regular $match context
  // If comparing to a MongoDB expression, use $expr
  if (isMongoExpression) {
    if (operator === "$exists") return { [field]: { $exists: true } };
    return {
      $expr: makeExprArrayCondition(`$${field}`, operator, processedValue),
    };
  }

  // Standard comparison operators with literal values
  switch (operator) {
    case "$eq":
    case "equals":
      return { [field]: { $eq: processedValue } };
    case "$ne":
    case "not equals":
      return { [field]: { $ne: processedValue } };
    case "$gt":
      return { [field]: { $gt: processedValue } };
    case "$gte":
      return { [field]: { $gte: processedValue } };
    case "$lt":
      return { [field]: { $lt: processedValue } };
    case "$lte":
      return { [field]: { $lte: processedValue } };
    case "$in": {
      const inArray = Array.isArray(processedValue)
        ? processedValue
        : [processedValue];
      return {
        [field]: {
          $in: inArray.map(parseNumberIfNeeded),
        },
      };
    }
    case "$lengthGt":
    case "length >":
      return { $expr: { $gt: [{ $size: `$${field}` }, processedValue] } };
    case "$lengthLt":
    case "length <":
      return { $expr: { $lt: [{ $size: `$${field}` }, processedValue] } };
    case "$exists":
      return {
        [field]: {
          $exists: typeof processedValue === "boolean" ? processedValue : true,
        },
      };
    case "$isNumber":
    case "isNumber":
      // $isNumber requires $expr, so we need to wrap it
      return { $expr: { $isNumber: `$${field}` } };
    case "$anyElementTrue":
    case "$allElementTrue":
      // For boolean list variables treated as schema fields, use booleanSwitch to determine comparison value
      // This happens when list variable fields are referenced without isListVariable flag
      if (
        value === undefined ||
        value === null ||
        (typeof value === "string" && value.trim() === "")
      ) {
        // Get the boolean value from booleanSwitch or default to true
        const booleanValue = condition
          ? getBooleanSwitch(condition, value)
          : true;
        return { [field]: { $eq: booleanValue } };
      }
      return { [field]: { $eq: processedValue } };
    default:
      return { [field]: processedValue };
  }
};

/**
 * Parses value for comparison, handling field references
 */
const parseValueForComparison = (
  value,
  customVariables,
  customSwitchCases,
  customListVariables,
  fieldOptions,
  arrayField = null,
  subFieldOptions = null,
) => {
  // Handle object with metadata format: {name: "...", _meta: {...}}
  if (value && typeof value === "object" && value._meta && value.name) {
    const valueName = value.name;
    const meta = value._meta;

    // Route based on metadata to avoid name collisions
    if (meta.isSwitchCase) {
      return `$${valueName}`;
    }

    if (meta.isListVariable) {
      return `$${valueName}`;
    }

    if (meta.isVariable) {
      // Arithmetic variables need to be inlined
      const arithVar = customVariables.find((v) => v.name === valueName);
      if (arithVar) {
        let expr = convertArithmeticExpression(
          arithVar.variable,
          customVariables,
        );
        if (expr) {
          if (
            typeof expr === "string" &&
            expr.startsWith("$") &&
            !isNaN(expr.slice(1))
          ) {
            expr = parseFloat(expr.slice(1));
          }
          return expr;
        }
      }
      return valueName;
    }

    if (meta.isSchemaField) {
      return resolveFieldReference(valueName, arrayField);
    }

    // If metadata doesn't match any known type, treat as literal
    return valueName;
  }

  // Handle non-string values (numbers, booleans, objects without metadata)
  if (typeof value !== "string") {
    return value;
  }

  // Fallback: Legacy string-based resolution with precedence rules
  // Check for schema field references first (prefer over variables)
  const fieldRef = fieldOptions.find(
    (f) => f.value === value || f.label === value,
  );
  if (fieldRef) {
    return resolveFieldReference(value, arrayField);
  }

  // Check subFieldOptions (array element fields) - these are specific to list variable contexts
  if (subFieldOptions && Array.isArray(subFieldOptions)) {
    const subFieldRef = subFieldOptions.find(
      (f) => f.value === value || f.label === value,
    );
    if (subFieldRef) {
      return resolveFieldReference(value, arrayField);
    }
  }

  // Check for arithmetic variables - these need to be inlined, not referenced as fields
  const arithVar = customVariables.find((v) => v.name === value);
  if (arithVar) {
    // Convert the arithmetic expression and return the inlined expression
    let expr = convertArithmeticExpression(arithVar.variable, customVariables);
    if (expr) {
      // If the latex converter returned a string like "$20.2", it's treating a literal number as a field reference
      // We need to convert it back to a number
      if (
        typeof expr === "string" &&
        expr.startsWith("$") &&
        !isNaN(expr.slice(1))
      ) {
        expr = parseFloat(expr.slice(1));
      }
      return expr;
    }
    // If conversion fails, return as literal (shouldn't happen but safety fallback)
    return value;
  }

  // Check for list variable or switch case references (these exist as fields in the document)
  if (
    customListVariables.find((v) => v.name === value) ||
    customSwitchCases.find((v) => v.name === value)
  ) {
    return `$${value}`;
  }

  // Check for map subfields (e.g., "listVar.subfield")
  if (typeof value === "string" && value.includes(".")) {
    const [baseVar] = value.split(".");
    const listVar = customListVariables.find((v) => v.name === baseVar);
    if (listVar?.listCondition?.operator === "$map") {
      return `$${value}`;
    }
  }

  // Return as literal value
  return !isNaN(value) && !isNaN(parseFloat(value)) ? parseFloat(value) : value;
};

/**
 * MongoDB operators that should not be treated as field references
 */
const MONGODB_OPERATORS = new Set([
  // Arithmetic operators
  "$abs",
  "$add",
  "$ceil",
  "$divide",
  "$exp",
  "$floor",
  "$ln",
  "$log",
  "$log10",
  "$mod",
  "$multiply",
  "$pow",
  "$round",
  "$sqrt",
  "$subtract",
  "$trunc",
  // Array operators
  "$arrayElemAt",
  "$arrayToObject",
  "$concatArrays",
  "$filter",
  "$first",
  "$in",
  "$indexOfArray",
  "$isArray",
  "$last",
  "$map",
  "$objectToArray",
  "$range",
  "$reduce",
  "$reverseArray",
  "$size",
  "$slice",
  "$zip",
  "$allElementsTrue",
  "$anyElementTrue",
  // Boolean operators
  "$and",
  "$not",
  "$or",
  "$nor",
  // Comparison operators
  "$cmp",
  "$eq",
  "$gt",
  "$gte",
  "$lt",
  "$lte",
  "$ne",
  // Conditional operators
  "$cond",
  "$ifNull",
  "$switch",
  // Date operators
  "$dateFromString",
  "$dateToString",
  "$dayOfMonth",
  "$dayOfWeek",
  "$dayOfYear",
  "$hour",
  "$isoDayOfWeek",
  "$isoWeek",
  "$isoWeekYear",
  "$millisecond",
  "$minute",
  "$month",
  "$second",
  "$toDate",
  "$week",
  "$year",
  // String operators
  "$concat",
  "$indexOfBytes",
  "$indexOfCP",
  "$ltrim",
  "$regexFind",
  "$regexFindAll",
  "$regexMatch",
  "$replaceAll",
  "$replaceOne",
  "$rtrim",
  "$split",
  "$strLenBytes",
  "$strLenCP",
  "$strcasecmp",
  "$substr",
  "$substrBytes",
  "$substrCP",
  "$toLower",
  "$toString",
  "$trim",
  "$toUpper",
  // Type operators
  "$convert",
  "$toBool",
  "$toDecimal",
  "$toDouble",
  "$toInt",
  "$toLong",
  "$toObjectId",
  "$type",
  // Aggregation operators
  "$avg",
  "$max",
  "$min",
  "$stdDevPop",
  "$stdDevSamp",
  "$sum",
  "$median",
  // Other operators
  "$let",
  "$literal",
  "$mergeObjects",
  "$rand",
  "$sampleRate",
]);

/**
 * Validates that all field references in a pipeline are defined
 * @param {Array} pipeline - MongoDB aggregation pipeline
 * @param {Array} fieldOptions - Available schema fields
 * @param {Array} customVariables - Arithmetic variables
 * @param {Array} customListVariables - List variables
 * @param {Array} customSwitchCases - Switch cases
 * @returns {Array} Array of undefined field reference errors
 */
const validatePipelineFieldReferences = (
  pipeline,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
) => {
  const errors = [];
  const definedFields = new Set();

  // Add all schema fields to defined fields
  fieldOptions.forEach((field) => {
    const fieldValue = field.value || field.label;
    if (fieldValue) {
      definedFields.add(fieldValue);
      definedFields.add(fieldValue.split(".")[0]);
    }
    if (field.label && field.label !== field.value) {
      definedFields.add(field.label);
      definedFields.add(field.label.split(".")[0]);
    }
  });

  // Add all custom variables
  customVariables.forEach((v) => definedFields.add(v.name));
  customListVariables.forEach((v) => definedFields.add(v.name));
  customSwitchCases.forEach((v) => definedFields.add(v.name));

  // Special system fields that are always available
  definedFields.add("_id");
  definedFields.add("objectId");

  /**
   * Recursively extracts field references from an expression.
   * @param {*} value - The value to inspect
   * @param {string} path - Current location path (for error messages)
   * @param {boolean} inIteratorScope - True when inside $map.in / $filter.cond / $reduce.in,
   *   where bare $field references are relative to the array element, not the document.
   */
  const extractFieldReferences = (
    value,
    path = "",
    inIteratorScope = false,
  ) => {
    const references = [];

    if (typeof value === "string") {
      // Inside an iterator scope ($map.in etc.), $field refers to the array element —
      // skip document-level validation for those references.
      if (
        !inIteratorScope &&
        value.startsWith("$") &&
        !value.startsWith("$$")
      ) {
        const fieldName = value.substring(1);
        // Extract the root field name (before any dots)
        const rootField = fieldName.split(".")[0];

        // Skip MongoDB operators
        if (!MONGODB_OPERATORS.has(value)) {
          references.push({
            field: rootField,
            fullPath: fieldName,
            location: path,
          });
        }
      }
    } else if (Array.isArray(value)) {
      value.forEach((item, index) => {
        references.push(
          ...extractFieldReferences(item, `${path}[${index}]`, inIteratorScope),
        );
      });
    } else if (value && typeof value === "object") {
      const ITERATOR_OPS = new Set(["$map", "$filter", "$reduce"]);
      Object.entries(value).forEach(([key, val]) => {
        const newPath = path ? `${path}.${key}` : key;
        if (ITERATOR_OPS.has(key) && val && typeof val === "object") {
          // Peek inside $map/$filter/$reduce body and mark 'in'/'cond' as iterator scope,
          // since $field references there are relative to the array element, not the document.
          Object.entries(val).forEach(([innerKey, innerVal]) => {
            const innerPath = `${newPath}.${innerKey}`;
            const isIteratorBody = innerKey === "in" || innerKey === "cond";
            references.push(
              ...extractFieldReferences(
                innerVal,
                innerPath,
                inIteratorScope || isIteratorBody,
              ),
            );
          });
        } else {
          references.push(
            ...extractFieldReferences(val, newPath, inIteratorScope),
          );
        }
      });
    }

    return references;
  };

  /**
   * Tracks fields that are defined in a stage
   */
  const trackDefinedFields = (stage) => {
    if (stage.$project) {
      Object.entries(stage.$project).forEach(([field, value]) => {
        // Only track if the field is included (value is 1 or an expression)
        if (value === 1 || (typeof value === "object" && value !== null)) {
          // Extract root field name (before any dots)
          const rootField = field.split(".")[0];
          definedFields.add(rootField);
        }
      });
    } else if (stage.$addFields) {
      Object.keys(stage.$addFields).forEach((field) => {
        const rootField = field.split(".")[0];
        definedFields.add(rootField);
      });
    }
  };

  // Process each stage
  pipeline.forEach((stage, stageIndex) => {
    // Extract all field references in this stage
    const references = extractFieldReferences(stage, `stage[${stageIndex}]`);

    // Check each reference
    references.forEach(({ field, fullPath, location }) => {
      if (!definedFields.has(field)) {
        errors.push({
          field: fullPath,
          location,
          message: `Field reference "$${fullPath}" is not defined. Make sure to define it in a previous stage or check for typos.`,
        });
      }
    });

    // Track fields defined by this stage for subsequent stages
    trackDefinedFields(stage);
  });

  return errors;
};

/**
 * Formats pipeline as pretty-printed JSON
 */
export const formatMongoAggregation = (pipeline) => {
  return JSON.stringify(pipeline, null, 2);
};

/**
 * Validates pipeline structure
 */
export const isValidPipeline = (pipeline) => {
  if (!Array.isArray(pipeline) || pipeline.length === 0) return false;

  const validateValue = (value, path = "") => {
    if (value === undefined) return false;
    if (value === null) return true; // null is a valid MongoDB query value (e.g. {$ne: [field, null]})
    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean"
    )
      return true;
    if (Array.isArray(value)) {
      return value.every((item, index) =>
        validateValue(item, `${path}[${index}]`),
      );
    }
    if (typeof value === "object") {
      for (const key in value) {
        if (!key || key.trim() === "") return false; // Invalid empty key
        if (!validateValue(value[key], `${path}.${key}`)) return false;
      }
      // Special validation for operators
      if (value.$in !== undefined && !Array.isArray(value.$in)) return false;
      // $size can be either an integer (in match context) or an expression (string/object in aggregation context)
      if (
        value.$size !== undefined &&
        typeof value.$size === "number" &&
        (!Number.isInteger(value.$size) || value.$size < 0)
      )
        return false;
      if (value.$anyElementTrue !== undefined) {
        // $anyElementTrue must be either an array or an object (for $map)
        if (
          !Array.isArray(value.$anyElementTrue) &&
          typeof value.$anyElementTrue !== "object"
        )
          return false;
      }
      if (value.$allElementTrue !== undefined) {
        // $allElementTrue must be either an array or an object (for $map)
        if (
          !Array.isArray(value.$allElementTrue) &&
          typeof value.$allElementTrue !== "object"
        )
          return false;
      }
      // $ifNull operator validation
      if (value.$ifNull !== undefined) {
        // $ifNull must be an array with exactly 2 elements
        if (!Array.isArray(value.$ifNull) || value.$ifNull.length !== 2)
          return false;
      }
      // $switch operator validation
      if (value.$switch !== undefined) {
        const switchObj = value.$switch;
        if (typeof switchObj !== "object" || switchObj === null) return false;
        // branches is required and must be an array
        if (!Array.isArray(switchObj.branches)) return false;
        // each branch must have case and then properties
        for (const branch of switchObj.branches) {
          if (
            typeof branch !== "object" ||
            branch === null ||
            !("case" in branch) ||
            !("then" in branch)
          )
            return false;
        }
        // default is optional but if present must be valid
        if (
          "default" in switchObj &&
          !validateValue(switchObj.default, `${path}.$switch.default`)
        )
          return false;
      }
      // Aggregation operators ($min, $max, $avg, $sum) accept strings (field refs), arrays, or numbers
      // No additional validation needed - they're already covered by the general validation above
      // $median requires an object with input and method, which is also covered
      return true;
    }
    return false;
  };

  for (const stage of pipeline) {
    if (!stage || typeof stage !== "object") return false;
    const keys = Object.keys(stage);
    if (keys.length !== 1) return false;

    const stageType = keys[0];
    if (!stageType.startsWith("$")) return false;

    const stageValue = stage[stageType];
    if (!stageValue || typeof stageValue !== "object") return false;

    // Allow empty stage objects (they're no-ops but valid)
    // This is important for arithmetic and list variables where stages
    // might be empty if all variables at a level are filtered out
    if (Object.keys(stageValue).length === 0) continue;

    // Validate the stage content
    if (!validateValue(stageValue, stageType)) return false;
  }

  return true;
};

// Legacy export for backward compatibility
export function convertToMongoAggregation(
  filters,
  schema = {},
  fieldOptions = [],
  customVariables = [],
  customListVariables = [],
  customSwitchCases = [],
  additionalFieldsToProject = [],
  annotationMode = false,
) {
  return buildMongoAggregationPipeline(
    filters,
    schema,
    fieldOptions,
    customVariables,
    customListVariables,
    customSwitchCases,
    additionalFieldsToProject,
    annotationMode,
  );
}

// Export default
export default {
  buildMongoAggregationPipeline,
  convertToMongoAggregation,
  formatMongoAggregation,
  isValidPipeline,
};
