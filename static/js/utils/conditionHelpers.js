// Normalize a field value that may be a string or an object with a .name property
export const normalizeFieldValue = (value) => {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object" && value.name) return value.name;
  return String(value);
};

// Helper function to infer type from switch case outcomes
const inferSwitchCaseType = (
  switchCondition,
  customVariables = [],
  fieldOptionsList = [],
  schema = null,
  fallbackFieldOptions = [],
) => {
  if (!switchCondition || !switchCondition.value) {
    return undefined;
  }

  const outcomes = [];

  // Collect all possible outcome values (then values and default)
  if (
    switchCondition.value.cases &&
    Array.isArray(switchCondition.value.cases)
  ) {
    switchCondition.value.cases.forEach((caseItem) => {
      if (
        caseItem.then !== undefined &&
        caseItem.then !== null &&
        caseItem.then !== ""
      ) {
        outcomes.push(caseItem.then);
      }
    });
  }

  if (
    switchCondition.value.default !== undefined &&
    switchCondition.value.default !== null &&
    switchCondition.value.default !== ""
  ) {
    outcomes.push(switchCondition.value.default);
  }

  if (outcomes.length === 0) {
    return "string"; // Default to string if no outcomes
  }

  // Check if all outcomes are references to fields or variables
  let inferredType = undefined;

  for (const outcome of outcomes) {
    if (typeof outcome !== "string") {
      // Non-string values - shouldn't happen but handle it
      continue;
    }

    // Check if outcome is a variable
    const variable = customVariables?.find((v) => v.name === outcome);
    if (variable) {
      const varType = variable.type || "number";
      if (!inferredType) {
        inferredType = varType;
      } else if (inferredType !== varType) {
        // Mixed types - default to string
        return "string";
      }
      continue;
    }

    // Check if outcome is a field by using getFieldType (more comprehensive than just checking fieldOptionsList)
    const fieldType = getFieldType(
      outcome,
      customVariables,
      schema,
      fallbackFieldOptions,
      fieldOptionsList,
      [],
      [],
    );
    if (fieldType) {
      if (!inferredType) {
        inferredType = fieldType;
      } else if (inferredType !== fieldType) {
        // Mixed types - default to string
        return "string";
      }
      continue;
    }

    // If it's not a variable or field, check if it's a literal value
    // Try to infer from literal values
    if (!isNaN(outcome) && !isNaN(parseFloat(outcome))) {
      // It's a number
      if (!inferredType) {
        inferredType = "number";
      } else if (inferredType !== "number") {
        return "string";
      }
    } else if (outcome === "true" || outcome === "false") {
      // It's a boolean
      if (!inferredType) {
        inferredType = "boolean";
      } else if (inferredType !== "boolean") {
        return "string";
      }
    } else {
      // It's a string
      if (!inferredType) {
        inferredType = "string";
      } else if (inferredType !== "string") {
        return "string";
      }
    }
  }

  return inferredType || "string";
};

// Helper functions for field type checking
export const getFieldType = (
  field,
  customVariables,
  schema,
  fallbackFieldOptions,
  fieldOptionsList,
  customListVariables = [],
  customSwitchCases = [],
) => {
  if (!field) {
    return undefined;
  }

  // Normalize field to handle both string and object formats
  // New format: {name: "fieldName", _meta: {...}}
  // Legacy format: "fieldName"
  let fieldName = field;
  let fieldMeta = null;
  if (typeof field === "object" && field !== null) {
    if (field.name) {
      fieldName = field.name;
      fieldMeta = field._meta || null;
    } else {
      return undefined;
    }
  }

  if (typeof fieldName !== "string") {
    return undefined;
  }

  // First check custom variables and list variables - ensure they are arrays
  const safeCustomVariables = Array.isArray(customVariables)
    ? customVariables
    : [];
  const safeCustomListVariables = Array.isArray(customListVariables)
    ? customListVariables
    : [];
  const safeSwitchCases = Array.isArray(customSwitchCases)
    ? customSwitchCases
    : [];

  // If metadata is present, use it to determine the exact field type (solves name collisions)
  if (fieldMeta) {
    if (fieldMeta.isSwitchCase) {
      const switchCase = safeSwitchCases.find((sc) => sc.name === fieldName);
      if (switchCase) {
        const type = inferSwitchCaseType(
          switchCase.switchCondition,
          safeCustomVariables,
          fieldOptionsList,
          schema,
          fallbackFieldOptions,
        );
        return type;
      }
    }

    if (fieldMeta.isListVariable) {
      const listVar = safeCustomListVariables.find(
        (lv) => lv.name === fieldName,
      );
      if (listVar?.type) {
        return listVar.type;
      }
    }

    if (fieldMeta.isVariable) {
      const fieldVar = safeCustomVariables.find((v) => v.name === fieldName);
      if (fieldVar?.type) {
        return fieldVar.type;
      }
      // If it's a custom variable but no type specified, assume number (for arithmetic variables)
      if (fieldVar) {
        return "number";
      }
    }

    if (fieldMeta.isSchemaField) {
      const fieldObjList = fieldOptionsList
        ? fieldOptionsList.find((f) => f.label === fieldName)
        : null;
      if (fieldObjList?.type) {
        return fieldObjList.type;
      }
      // Check fallback field options
      const safeFieldOptions = fallbackFieldOptions || [];
      const exactMatch = safeFieldOptions.find((f) => f.label === fieldName);
      if (exactMatch?.type) {
        return exactMatch.type;
      }
    }
  }

  // Fallback: legacy precedence-based lookup (may be incorrect if names collide)
  const fieldVar = safeCustomVariables.find((v) => v.name === fieldName);
  const listVar = safeCustomListVariables.find((lv) => lv.name === fieldName);
  const switchCase = safeSwitchCases.find((sc) => sc.name === fieldName);
  const fieldObjList = fieldOptionsList
    ? fieldOptionsList.find((f) => f.label === fieldName)
    : null;

  if (fieldVar?.type) {
    return fieldVar.type;
  }
  // If it's a custom variable but no type specified, assume number (for arithmetic variables)
  if (fieldVar) {
    return "number";
  }
  if (listVar?.type) {
    return listVar.type;
  }

  // For switch cases, infer type from outcomes (the "then" values)
  // The targetField is where the result is stored, not what determines the type
  if (switchCase) {
    const type = inferSwitchCaseType(
      switchCase.switchCondition,
      safeCustomVariables,
      fieldOptionsList,
      schema,
      fallbackFieldOptions,
    );
    return type;
  }

  if (fieldObjList?.type) {
    return fieldObjList.type;
  }

  // Check for exact match first (backward compatibility)
  const safeFieldOptions = fallbackFieldOptions || [];
  const exactMatch = safeFieldOptions.find((f) => f.label === fieldName);
  if (exactMatch?.type) {
    return exactMatch.type;
  }
  // Handle nested field paths (e.g., "Candidate.isdiffpos", "cross_matches.NED_BetaV3.z")
  const fieldParts = fieldName?.split(".");

  if (fieldParts.length >= 2) {
    const rootField = fieldParts[0];
    const nestedPath = fieldParts.slice(1);

    // Find the root field in the nested schema - access fields array from the schema
    const schemaFields = schema?.fields || [];
    const rootFieldObj = schemaFields.find((f) => f.name === rootField);

    if (rootFieldObj) {
      // Handle object type with nested values
      if (
        rootFieldObj.type === "object" &&
        rootFieldObj.values &&
        Array.isArray(rootFieldObj.values)
      ) {
        return findNestedFieldType(rootFieldObj.values, nestedPath);
      }

      // Handle array type with nested objects
      if (
        rootFieldObj.type === "array" &&
        rootFieldObj.values &&
        Array.isArray(rootFieldObj.values)
      ) {
        // For array fields, the first part after root is the array object type (e.g., "NED_BetaV3")
        if (nestedPath.length >= 1) {
          const arrayObjectName = nestedPath[0];
          const remainingPath = nestedPath.slice(1);

          // Find the specific array object type
          const arrayObject = rootFieldObj.values.find(
            (v) => v.label === arrayObjectName,
          );
          if (arrayObject && arrayObject.values) {
            return findNestedFieldType([arrayObject], remainingPath, true);
          }
        }
      }
    }
  }

  return undefined;
};

// Helper function to find field type in nested structure
const findNestedFieldType = (values, fieldPath, isArrayObject = false) => {
  if (!fieldPath || fieldPath.length === 0) return undefined;

  const currentField = fieldPath[0];
  const remainingPath = fieldPath.slice(1);

  if (isArrayObject && values.length > 0 && values[0].values) {
    // For array objects, look in the values property
    const targetValues = values[0].values;

    if (remainingPath.length === 0) {
      // Final field, return its type
      return targetValues[currentField];
    } else {
      // More nesting, continue traversal
      const nestedObj = targetValues[currentField];
      if (typeof nestedObj === "object" && nestedObj !== null) {
        return findNestedFieldType(
          [{ values: nestedObj }],
          remainingPath,
          true,
        );
      }
    }
  } else {
    // For regular object types
    for (const value of values) {
      if (value.label === currentField) {
        if (remainingPath.length === 0) {
          // Final field, return its type
          return value.type;
        } else if (value.values) {
          // More nesting, continue traversal
          if (Array.isArray(value.values)) {
            return findNestedFieldType(value.values, remainingPath);
          } else if (typeof value.values === "object") {
            return findNestedFieldType(
              [{ values: value.values }],
              remainingPath,
              true,
            );
          }
        }
      }
    }
  }

  return undefined;
};

export const isFieldType = (
  field,
  type,
  customVariables,
  schema,
  fallbackFieldOptions,
  fieldOptionsList,
  customListVariables = [],
  customSwitchCases = [],
) => {
  return (
    getFieldType(
      field,
      customVariables,
      schema,
      fallbackFieldOptions,
      fieldOptionsList,
      customListVariables,
      customSwitchCases,
    ) === type
  );
};

// Helper function to get operators for a field
export const getOperatorsForField = (
  field,
  customVariables,
  schema,
  fallbackFieldOptions,
  fieldOptionsList,
  customListVariables = [],
  customSwitchCases = [],
) => {
  // Use getFieldType to determine the type, which handles nested fields properly
  const type = getFieldType(
    field,
    customVariables,
    schema,
    fallbackFieldOptions,
    fieldOptionsList,
    customListVariables,
    customSwitchCases,
  );

  // If we can't determine the type, return empty array
  if (!type) return [];

  const baseOperators = ["$exists", "$isNumber"]; // Available for all field types

  switch (type) {
    case "number":
      return [
        "$eq",
        "$ne",
        "$gt",
        "$gte",
        "$lt",
        "$lte",
        "$in",
        "$round",
        ...baseOperators,
      ];
    case "string":
      return ["$eq", "$ne", "$in", "$regex", "$type", ...baseOperators];
    case "array":
    case "array_variable": // List variables should have the same operators as regular arrays
    case "array_switch": // Switch cases with array outcomes should have the same operators as regular arrays
      return [
        "$anyElementTrue",
        "$allElementsTrue",
        "$filter",
        "$map",
        "$lengthGt",
        "$lengthLt",
        "$min",
        "$max",
        "$avg",
        "$sum",
        "$size",
        "$stdDevPop",
        "$median",
        ...baseOperators,
      ];
    case "array_variable_boolean": // List variables with anyElementTrue/allElementsTrue operators - exclude length operators
      return [
        "$anyElementTrue",
        "$allElementsTrue",
        "$filter",
        "$map",
        // Exclude $lengthGt and $lengthLt for boolean array variables
        "$min",
        "$max",
        "$avg",
        "$sum",
        "$size",
        "$stdDevPop",
        "$median",
        ...baseOperators,
      ];
    case "boolean":
      return ["$eq", "$ne", ...baseOperators];
    default:
      return baseOperators;
  }
};

// Helper function to compose field options with variables
export const getFieldOptionsWithVariable = (
  fieldOptionsList,
  customVariables,
  customListVariables,
  customSwitchCases = [],
  schemaFieldOptions = [], // Add schema field options parameter
  currentContextTime = null, // Optional: filter switches created after this time
  currentStream = null, // Optional: filter by stream
) => {
  const streamPrefix = currentStream ? currentStream.split(" ")[0] : null;
  const matchesStream = (item) =>
    !streamPrefix || !item.stream || item.stream === streamPrefix;

  const filteredListVariables = streamPrefix
    ? customListVariables?.filter(matchesStream)
    : customListVariables;
  const filteredCustomVariables = streamPrefix
    ? customVariables?.filter(matchesStream)
    : customVariables;
  const filteredSwitchCases = streamPrefix
    ? customSwitchCases?.filter(matchesStream)
    : customSwitchCases;

  const normalizeName = normalizeFieldValue;

  const listVariableOptions =
    filteredListVariables?.map((lv) => {
      // If the list operator is anyElementTrue or allElementsTrue, set type to array_variable_boolean
      const operator = lv.listCondition?.operator;
      const isBooleanArray =
        operator === "$anyElementTrue" || operator === "$allElementsTrue";
      const normalized = normalizeName(lv.name);
      return {
        label: normalized,
        type: isBooleanArray ? "array_variable_boolean" : "array_variable",
        isListVariable: true,
        isVariable: false,
        listCondition: lv.listCondition,
        group: "Database List Variables",
      };
    }) || [];

  // Filter switch cases to only show those created before current context
  const timeFilteredSwitchCases = currentContextTime
    ? filteredSwitchCases?.filter(
        (sc) => !sc.createdAt || sc.createdAt < currentContextTime,
      )
    : filteredSwitchCases;

  const switchCaseOptions =
    timeFilteredSwitchCases?.map((sc) => {
      // Always infer type from switch case outcomes (the "then" values)
      // regardless of whether it has a targetField or not
      const inferredType =
        inferSwitchCaseType(
          sc.switchCondition,
          customVariables,
          fieldOptionsList,
          null,
          schemaFieldOptions,
        ) || "string";

      const normalized = normalizeName(sc.name);
      return {
        label: normalized,
        type: inferredType,
        isSwitchCase: true,
        isVariable: false,
        isListVariable: false,
        switchCondition: sc.switchCondition,
        group: "Switch Cases",
      };
    }) || [];

  const variableOptions =
    filteredCustomVariables?.map((eq) => {
      const normalized = normalizeName(eq.name);
      return {
        label: normalized,
        type: "number",
        isVariable: true,
        isListVariable: false,
        equation: eq.variable,
        group: "Arithmetic Variables",
      };
    }) || [];

  const baseOptions = fieldOptionsList;

  // Always include schema fields regardless of which base options are used
  const combined = [
    ...baseOptions,
    ...schemaFieldOptions,
    ...variableOptions,
    ...listVariableOptions,
    ...switchCaseOptions,
  ];

  return combined;
};

// Helper function to update conditions in the filter tree
export const createUpdateConditionFunction = (filters, setFilters) => {
  return (blockId, conditionId, key, value) => {
    const updateBlock = (block) => {
      if (block.id !== blockId) {
        return {
          ...block,
          children: block.children?.map((child) =>
            child.category === "block" ? updateBlock(child) : child,
          ),
        };
      }
      return {
        ...block,
        children: block.children.map((child) =>
          child.id === conditionId ? { ...child, [key]: value } : child,
        ),
      };
    };
    setFilters(filters.map(updateBlock));
  };
};

// Helper function to remove items from the filter tree
export const createRemoveItemFunction = (
  filters,
  setFilters,
  defaultCondition,
) => {
  return (blockId, itemId) => {
    const removeFromBlock = (block) => {
      if (block.id !== blockId) {
        return {
          ...block,
          children: block.children.map((child) =>
            child.category === "block" ? removeFromBlock(child) : child,
          ),
        };
      }
      const filteredChildren = block.children.filter(
        (child) => child.id !== itemId,
      );
      // If this is the root block and removing would leave it empty, always keep at least one condition
      if (filteredChildren.length === 0 && blockId === filters[0].id) {
        return {
          ...block,
          children: [defaultCondition()],
        };
      }
      return {
        ...block,
        children: filteredChildren,
      };
    };
    setFilters(filters.map(removeFromBlock));
  };
};
