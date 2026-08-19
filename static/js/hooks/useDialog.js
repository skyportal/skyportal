import { useState, useCallback, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { getArrayFieldSubOptions } from "../constants/filterConstants";
import { useCurrentBuilder } from "./useContexts";

export const useDialogStates = () => {
  // Dialog states
  const [saveDialog, setSaveDialog] = useState({ open: false, block: null });
  const [saveName, setSaveName] = useState("");
  const [saveError, setSaveError] = useState("");
  const [specialConditionDialog, setSpecialConditionDialog] = useState({
    open: false,
    blockId: null,
  });
  const [listConditionDialog, setListConditionDialog] = useState({
    open: false,
    blockId: null,
  });
  const [switchDialog, setSwitchDialog] = useState({
    open: false,
    blockId: null,
  });
  const [mongoDialog, setMongoDialog] = useState({ open: false });

  // Reset all dialog states
  const resetDialogs = useCallback(() => {
    setSaveDialog({ open: false, block: null });
    setSaveName("");
    setSaveError("");
    setSpecialConditionDialog({ open: false, blockId: null });
    setListConditionDialog({ open: false, blockId: null });
    setSwitchDialog({ open: false, blockId: null });
    setMongoDialog({ open: false });
  }, []);

  // Individual dialog actions
  const openSaveDialog = useCallback((block) => {
    setSaveDialog({ open: true, block });
  }, []);

  const closeSaveDialog = useCallback(() => {
    setSaveDialog({ open: false, block: null });
    setSaveName("");
    setSaveError("");
  }, []);

  const openSpecialConditionDialog = useCallback((blockId) => {
    setSpecialConditionDialog({ open: true, blockId });
  }, []);

  const closeSpecialConditionDialog = useCallback(() => {
    setSpecialConditionDialog({ open: false, blockId: null });
  }, []);

  const openListConditionDialog = useCallback((blockId) => {
    setListConditionDialog({ open: true, blockId });
  }, []);

  const closeListConditionDialog = useCallback(() => {
    setListConditionDialog({ open: false, blockId: null });
  }, []);

  const openSwitchDialog = useCallback((blockId) => {
    setSwitchDialog({ open: true, blockId });
  }, []);

  const closeSwitchDialog = useCallback(() => {
    setSwitchDialog({ open: false, blockId: null });
  }, []);

  return {
    // Dialog states
    saveDialog,
    saveName,
    saveError,
    specialConditionDialog,
    listConditionDialog,
    switchDialog,
    mongoDialog,

    // Dialog actions
    openSaveDialog,
    closeSaveDialog,
    setSaveDialog, // Direct state setter for save dialog
    openSpecialConditionDialog,
    closeSpecialConditionDialog,
    setSpecialConditionDialog, // Direct state setter for complex updates
    openListConditionDialog,
    closeListConditionDialog,
    setListConditionDialog, // Direct state setter for complex updates
    openSwitchDialog,
    closeSwitchDialog,
    setSwitchDialog, // Direct state setter for complex updates

    // Save dialog actions
    setSaveName,
    setSaveError,
    setMongoDialog,
    resetDialogs,
  };
};

export const useListConditionDialog = (
  listConditionDialog,
  filters,
  customListVariables,
  defaultBlock,
) => {
  const { schema } = useCurrentBuilder(); // Access schema from context
  const [localFilters, setLocalFilters] = useState([]);
  const [listFieldName, setListFieldName] = useState("");
  const [subFieldOptions, setSubFieldOptions] = useState([]);

  // Available operators for array conditions
  const arrayOperators = [
    { value: "$anyElementTrue", label: "Any Element True" },
    { value: "$allElementsTrue", label: "All Elements True" },
    { value: "$filter", label: "Filter" },
    { value: "$map", label: "Map" },
    { value: "$min", label: "Minimum Value" },
    { value: "$max", label: "Maximum Value" },
    { value: "$avg", label: "Average Value" },
    { value: "$sum", label: "Sum of Values" },
    { value: "$size", label: "Count Elements" },
    { value: "$stdDevPop", label: "Standard Deviation" },
    { value: "$median", label: "Median Value" },
  ];

  // Find condition id in filters to retrieve the field name and operator
  const conditionId = listConditionDialog.conditionId;

  const findDataInBlock = (block) => {
    if (block.id === listConditionDialog.blockId) {
      return block.children.reduce(
        (data, child) => {
          if (child.id === conditionId) {
            return {
              field: child.field || "",
              operator: child.operator || "",
            };
          }
          if (child.category === "block") {
            return findDataInBlock(child) || data; // Recurse into child blocks
          }
          return data; // Return current data if not found
        },
        { field: "", operator: "" },
      );
    }

    if (block.children) {
      return block.children.reduce(
        (data, child) => {
          if (data.field) return data; // Stop if already found
          if (child.category === "block") {
            return findDataInBlock(child) || data; // Recurse into child blocks
          }
          return data; // Return current data if not found
        },
        { field: "", operator: "" },
      );
    }
    return { field: "", operator: "" }; // Return empty if no data found in this block
  };

  // Check all conditions in filters to find the field name and operator associated with the conditionId
  const getConditionDataFromId = () => {
    if (!conditionId) return { field: "", operator: "" };

    return filters.reduce(
      (foundData, block) => {
        if (foundData.field) return foundData; // Stop if already found

        return findDataInBlock(block);
      },
      { field: "", operator: "" },
    );
  };

  // Get the field name and operator from the condition
  const conditionData = getConditionDataFromId();
  const listFieldNameFromCondition = conditionData.field;
  const operatorFromCondition = conditionData.operator;

  // Update sub-field options when the field name changes
  useEffect(() => {
    const options = getArrayFieldSubOptions(listFieldNameFromCondition, schema);
    setSubFieldOptions(options);
  }, [listFieldNameFromCondition, schema]);

  const handleFieldSelection = (
    fieldLabel,
    selectedOperator,
    setSelectedSubField,
  ) => {
    setListFieldName(fieldLabel);

    // Check if this is a list variable
    const listVariable = customListVariables.find(
      (lv) => lv.name === fieldLabel,
    );
    if (listVariable && listVariable.listCondition?.subFieldOptions) {
      // Use sub-field options from the list variable, prefixed with the variable name
      const updatedSubFieldOptions =
        listVariable.listCondition.subFieldOptions.map((opt) => {
          // Extract the bare subfield name (everything after the last dot)
          const subfieldName = opt.label.includes(".")
            ? opt.label.split(".").pop()
            : opt.label;

          // For map operators, set a specific group name
          const groupName =
            listVariable.listCondition.operator === "$map"
              ? opt.group || `${listVariable.name} Fields`
              : undefined;

          return {
            ...opt,
            group: groupName,
            // Prefix with the variable name so resolveFieldReference can map
            // "inputname.jd" → "$$this.jd" in MongoDB generation
            label: `${fieldLabel}.${subfieldName}`,
          };
        });
      setSubFieldOptions(updatedSubFieldOptions);
    } else {
      // Use regular array field sub-options
      const options = getArrayFieldSubOptions(fieldLabel, schema);
      setSubFieldOptions(options);
    }

    // Clear selected subfield when array field changes
    setSelectedSubField("");

    // Only initialize with a default block if operator requires conditions
    if (
      ["$anyElementTrue", "$allElementsTrue", "$filter"].includes(
        selectedOperator,
      )
    ) {
      setLocalFilters([defaultBlock("And")]);
    }
  };

  const handleOperatorChange = (newOperator, selectedArrayField) => {
    // Initialize or clear local filters based on whether operator needs conditions
    if (
      ["$anyElementTrue", "$allElementsTrue", "$filter", "$map"].includes(
        newOperator,
      )
    ) {
      if (selectedArrayField && localFilters.length === 0) {
        setLocalFilters([defaultBlock("And")]);
      }
    } else {
      setLocalFilters([]);
    }
  };

  const resetDialog = () => {
    setLocalFilters([]);
    setListFieldName("");
    setSubFieldOptions([]);
  };

  return {
    // State
    localFilters,
    setLocalFilters,
    listFieldName,
    subFieldOptions,
    arrayOperators,

    // Condition data from inline context
    listFieldNameFromCondition,
    operatorFromCondition,

    // Actions
    handleFieldSelection,
    handleOperatorChange,
    resetDialog,
  };
};

export const useListConditionForm = (
  fieldOptions,
  customListVariables = [],
  customSwitchCases = [],
) => {
  const [selectedArrayField, setSelectedArrayField] = useState("");
  const [selectedOperator, setSelectedOperator] = useState("");
  const [selectedSubField, setSelectedSubField] = useState("");
  const [conditionName, setConditionName] = useState("");
  const [nameError, setNameError] = useState("");

  // Helper to normalize name values (handle both string and object formats)
  const normalizeName = (name) => {
    if (!name) return "";
    if (typeof name === "string") return name;
    if (typeof name === "object" && name.name) return name.name;
    return String(name);
  };

  // Get all available array fields (including list variables and switch cases with array outcomes)
  const availableArrayFields = [
    // Include schema array fields - check for both type "array" and isExpandableArray
    ...(fieldOptions || []).filter(
      (field) => field.type === "array" || field.isExpandableArray,
    ),
    // Only include list variables that are actually saved (exist in customListVariables)
    // This prevents using undefined or circular list variables
    ...customListVariables
      .filter((lv) => lv.name && lv.listCondition) // Only include properly defined list variables
      .map((lv) => ({
        label: normalizeName(lv.name),
        type: "array_variable",
        isListVariable: true,
        isDbVariable: true, // All list variables from customListVariables are database variables
      })),
    // Include switch cases where all outcomes are arrays
    ...(customSwitchCases || [])
      .filter((sc) => {
        // Check if the switch case has array outcomes
        const switchCondition = sc.switchCondition;
        if (!switchCondition || !switchCondition.value) return false;

        const outcomes = [];

        // Collect all possible outcome values
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

        if (outcomes.length === 0) return false;

        // Check if all outcomes refer to array fields or array variables
        return outcomes.every((outcome) => {
          // Check if outcome is an array variable
          const arrayVar = customListVariables.find(
            (lv) => lv.name === outcome,
          );
          if (arrayVar) return true;

          // Check if outcome is an array field from schema
          const arrayField = (fieldOptions || []).find(
            (field) =>
              field.label === outcome &&
              (field.type === "array" || field.isExpandableArray),
          );
          if (arrayField) return true;

          return false;
        });
      })
      .map((sc) => ({
        label: normalizeName(sc.name),
        type: "array_switch",
        isSwitchCase: true,
        isDbVariable: false,
      })),
  ];

  const validateConditionName = useCallback((name) => {
    if (!name.trim()) {
      return "Condition name is required";
    }
    if (name.trim().length < 3) {
      return "Condition name must be at least 3 characters long";
    }
    if (name.trim().length > 50) {
      return "Condition name must be less than 50 characters";
    }
    if (!/^[a-zA-Z0-9_\s-]+$/.test(name.trim())) {
      return "Condition name can only contain letters, numbers, spaces, hyphens, and underscores";
    }
    return "";
  }, []);

  const handleNameChange = useCallback(
    (newName) => {
      setConditionName(newName);
      const error = validateConditionName(newName);
      setNameError(error);
    },
    [setConditionName, validateConditionName, setNameError],
  );

  const resetForm = useCallback(() => {
    setSelectedArrayField("");
    setSelectedOperator("");
    setSelectedSubField("");
    setConditionName("");
    setNameError("");
  }, [
    setSelectedArrayField,
    setSelectedOperator,
    setSelectedSubField,
    setConditionName,
    setNameError,
  ]);

  const isFormValid = useCallback(() => {
    if (
      !selectedArrayField ||
      !selectedOperator ||
      !conditionName.trim() ||
      nameError
    ) {
      return false;
    }

    // Check if subfield is required for aggregation operators
    const operatorNeedsSubField = ["$min", "$max", "$avg", "$sum"].includes(
      selectedOperator,
    );
    if (operatorNeedsSubField && !selectedSubField.trim()) {
      return false;
    }

    return true;
  }, [
    selectedArrayField,
    selectedOperator,
    selectedSubField,
    conditionName,
    nameError,
  ]);

  return {
    // State
    selectedArrayField,
    selectedOperator,
    selectedSubField,
    conditionName,
    nameError,
    availableArrayFields,

    // Actions
    setSelectedArrayField,
    setSelectedOperator,
    setSelectedSubField,
    handleNameChange,
    resetForm,

    // Computed
    isFormValid: isFormValid(),
    validateConditionName,
  };
};

export const useListConditionSave = () => {
  const validateSaveConditions = (
    listFieldName,
    selectedOperator,
    selectedSubField,
    conditionName,
    nameError,
    localFilters,
    validateConditionName,
  ) => {
    if (!listFieldName.trim()) {
      return "Please select an array field";
    }

    // Check if subfield is required for aggregation operators
    const operatorNeedsSubField = [
      "$min",
      "$max",
      "$avg",
      "$sum",
      "$stdDevPop",
      "$median",
    ].includes(selectedOperator);
    if (operatorNeedsSubField && !selectedSubField.trim()) {
      return "Please select a subfield for the aggregation operation";
    }

    const nameValidationError = validateConditionName(conditionName);
    if (nameValidationError) {
      return nameValidationError;
    }

    // Check if conditions are required for this operator
    const operatorNeedsConditions = [
      "$anyElementTrue",
      "$allElementsTrue",
      "$filter",
    ].includes(selectedOperator);

    if (
      operatorNeedsConditions &&
      localFilters &&
      (localFilters?.length === 0 || localFilters[0].children.length === 0)
    ) {
      return "Please add at least one condition";
    }

    return null; // No validation errors
  };

  const saveListCondition = useCallback(
    async ({
      listFieldName,
      selectedOperator,
      selectedSubField,
      conditionName,
      localFilters,
      subFieldOptions,
      saved,
      listCondition,
      listConditionDialog,
      setCustomListVariables,
      setFilters,
      setLocalFilters, // Add this parameter for local state update
    }) => {
      if (saved) {
        setCustomListVariables((prev) => {
          return [
            ...prev.filter((lv) => lv.name !== conditionName.trim()),
            {
              name: conditionName.trim(),
              type: "array_variable",
              listCondition: listCondition,
              operator: selectedOperator,
            },
          ];
        });
      }

      // Create new condition for the filter
      const newCondition = {
        id: uuidv4(),
        category: "condition",
        field: conditionName.trim(),
        operator: selectedOperator,
        value: "",
        booleanSwitch: true, // Default to true for new conditions
        createdAt: Date.now(),
        isListVariable: true,
      };

      // Helper function to add condition to block
      const addConditionToBlock = (block) => {
        if (block.id === listConditionDialog.blockId) {
          let updatedChildren = [...block.children];

          // If conditionId is provided, delete the original condition
          if (listConditionDialog.conditionId) {
            updatedChildren = updatedChildren.filter(
              (child) => child.id !== listConditionDialog.conditionId,
            );
          }

          // Add the new list variable condition
          updatedChildren.push(newCondition);

          return {
            ...block,
            children: updatedChildren,
          };
        }
        if (block.children) {
          return {
            ...block,
            children: block.children.map((child) =>
              child.category === "block" ? addConditionToBlock(child) : child,
            ),
          };
        }
        return block;
      };

      // Update both context filters and local filters if available
      const updateFilters = (prevFilters) => {
        return prevFilters.map(addConditionToBlock);
      };

      // Update context filters
      setFilters(updateFilters);

      // Update local filters if setLocalFilters is provided
      if (setLocalFilters && typeof setLocalFilters === "function") {
        setLocalFilters(updateFilters);
      }

      return true; // Success
    },
    [],
  );

  return {
    validateSaveConditions,
    saveListCondition,
  };
};

export const usePopoverRegistry = (
  conditionId,
  customListVariables,
  setListPopoverAnchor,
  customSwitchCases,
  setSwitchPopoverAnchor,
) => {
  useEffect(() => {
    // Initialize registries if they don't exist
    if (!window.listPopoverRegistry) {
      window.listPopoverRegistry = new Map();
    }
    if (!window.listVariablePopoverRegistry) {
      window.listVariablePopoverRegistry = new Map();
    }

    // Register this component's callback
    window.listPopoverRegistry.set(conditionId, (anchorElement) => {
      setListPopoverAnchor(anchorElement);
      return true;
    });

    // Set up the global callback if it doesn't exist
    if (!window.openListPopover) {
      window.openListPopover = (targetConditionId, anchorElement) => {
        const callback = window.listPopoverRegistry?.get(targetConditionId);
        if (callback) {
          return callback(anchorElement);
        }
        return false;
      };
    }

    // Register list variable callback for this component
    const listVariableCallback = (listVariableName, anchorElement) => {
      const listVar = customListVariables.find(
        (lv) => lv.name === listVariableName,
      );
      if (listVar) {
        setListPopoverAnchor(anchorElement);
        window.currentListVariable = listVar;
        return true;
      }
      return false;
    };

    window.listVariablePopoverRegistry.set(conditionId, listVariableCallback);

    // Set up the global list variable callback if it doesn't exist
    if (!window.openListVariablePopover) {
      window.openListVariablePopover = (listVariableName, anchorElement) => {
        for (const callback of window.listVariablePopoverRegistry?.values() ||
          []) {
          if (callback(listVariableName, anchorElement)) {
            return true;
          }
        }
        return false;
      };
    }

    // Initialize switch case registry
    if (!window.switchCasePopoverRegistry) {
      window.switchCasePopoverRegistry = new Map();
    }

    // Register switch case callback for this component
    const switchCaseCallback = (switchCaseName, anchorElement) => {
      const switchCase = customSwitchCases.find(
        (sc) => sc.name === switchCaseName,
      );
      if (switchCase) {
        setSwitchPopoverAnchor(anchorElement);
        window.currentSwitchCase = switchCase;
        return true;
      }
      return false;
    };

    window.switchCasePopoverRegistry.set(conditionId, switchCaseCallback);

    // Set up the global switch case callback if it doesn't exist
    if (!window.openSwitchCasePopover) {
      window.openSwitchCasePopover = (switchCaseName, anchorElement) => {
        for (const callback of window.switchCasePopoverRegistry?.values() ||
          []) {
          if (callback(switchCaseName, anchorElement)) {
            return true;
          }
        }
        return false;
      };
    }

    return () => {
      // Clean up this component's callbacks
      window.listPopoverRegistry?.delete(conditionId);
      window.listVariablePopoverRegistry?.delete(conditionId);
      window.switchCasePopoverRegistry?.delete(conditionId);

      // If this was the last component, clean up global callbacks
      if (window.listPopoverRegistry?.size === 0) {
        window.openListPopover = null;
      }
      if (window.listVariablePopoverRegistry?.size === 0) {
        window.openListVariablePopover = null;
      }
      if (window.switchCasePopoverRegistry?.size === 0) {
        window.openSwitchCasePopover = null;
      }
    };
  }, [
    conditionId,
    customListVariables,
    setListPopoverAnchor,
    customSwitchCases,
    setSwitchPopoverAnchor,
  ]);
};
