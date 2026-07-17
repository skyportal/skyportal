import { useEffect, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Paper,
  Chip,
  TextField,
  Autocomplete,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
} from "@mui/material";
import {
  useListConditionDialog,
  useListConditionForm,
  useListConditionSave,
} from "../../../../hooks/useDialog";
import { useCurrentBuilder } from "../../../../hooks/useContexts";
import { normalizeFieldValue } from "../../../../utils/conditionHelpers";
import { getSimpleType } from "../../../../constants/filterConstants";
import BlockComponent from "../block/BlockComponent";
import MapExpressionEditor from "./MapExpressionEditor";
import { postElement } from "../../../../ducks/boom_filter_modules";
import { useAppDispatch, useAppSelector } from "../../../../types/hooks";

const OPERATORS_NEEDING_CONDITIONS = [
  "$anyElementTrue",
  "$allElementsTrue",
  "$filter",
];
const OPERATORS_NEEDING_SUBFIELD = [
  "$min",
  "$max",
  "$avg",
  "$sum",
  "$stdDevPop",
  "$median",
];

interface SubFieldSelectorProps {
  selectedSubField?: string;
  onSubFieldChange: (...a: any[]) => void;
  subFieldOptions: any[];
  selectedOperator: string;
}

const SubFieldSelector = ({
  selectedSubField,
  onSubFieldChange,
  subFieldOptions,
  selectedOperator,
}: SubFieldSelectorProps) => {
  // Get numeric subfields for aggregation operators
  const getNumericSubFields = () => {
    return subFieldOptions.filter((option: any) => option.type === "number");
  };

  const shouldShowSubFieldSelector =
    OPERATORS_NEEDING_SUBFIELD.includes(selectedOperator);

  if (!shouldShowSubFieldSelector) {
    return null;
  }

  const numericFields = getNumericSubFields();
  const selectedOption =
    numericFields.find((field: any) => field.label === selectedSubField) ||
    null;

  return (
    <Box sx={{ mb: 2 }}>
      <Autocomplete
        fullWidth
        options={numericFields}
        groupBy={(option: any) => option.group || "Other Fields"}
        getOptionLabel={(option: any) => option.label || ""}
        value={selectedOption}
        onChange={(_: any, newValue: any) => {
          onSubFieldChange(newValue ? newValue.label : "");
        }}
        filterOptions={(options: any[], { inputValue }: any) => {
          // Custom filter function for better search experience
          const filterValue = inputValue.toLowerCase();
          return options.filter((option: any) =>
            option.label.toLowerCase().includes(filterValue),
          );
        }}
        renderInput={(params: any) => (
          <TextField
            {...params}
            label="Subfield"
            variant="outlined"
            placeholder="Type to search for numeric fields..."
            helperText={`Select the numeric field to perform the ${selectedOperator.replace(
              "$",
              "",
            )} operation on`}
          />
        )}
        renderOption={(props: any, option: any) => {
          const { key, ...otherProps } = props;
          return (
            <li key={option.label} {...otherProps}>
              <div>
                <div style={{ fontWeight: "bold" }}>{option.label}</div>
                <div style={{ fontSize: "0.8em", color: "#666" }}>
                  Type: {option.type}
                </div>
              </div>
            </li>
          );
        }}
        noOptionsText="No numeric fields found"
        clearOnBlur={false}
        selectOnFocus
        handleHomeEndKeys
      />
    </Box>
  );
};

interface ArrayFieldSelectorProps {
  selectedArrayField?: string;
  onFieldChange: (...a: any[]) => void;
  availableArrayFields?: any[];
}

const ArrayFieldSelector = ({
  selectedArrayField,
  onFieldChange,
  availableArrayFields,
}: ArrayFieldSelectorProps) => {
  // Transform field objects to work with Autocomplete
  const fieldOptions = availableArrayFields || [];

  // Find the currently selected field object
  const selectedOption =
    fieldOptions.find((field: any) => field.label === selectedArrayField) ||
    null;

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Select an array field, existing list variable, or switch case with array
        outcomes to create conditions for:
      </Typography>

      <Autocomplete
        fullWidth
        options={fieldOptions}
        getOptionLabel={(option: any) => option.label || ""}
        value={selectedOption}
        onChange={(_: any, newValue: any) => {
          onFieldChange(newValue ? newValue.label : "");
        }}
        filterOptions={(options: any[], { inputValue }: any) => {
          // Custom filter function for better search experience
          const filterValue = inputValue.toLowerCase();
          return options.filter((option: any) =>
            option.label.toLowerCase().includes(filterValue),
          );
        }}
        renderInput={(params: any) => (
          <TextField
            {...params}
            label="Array Field"
            variant="outlined"
            placeholder="Type to search for array fields..."
            helperText="Start typing to filter available fields"
          />
        )}
        renderOption={(props: any, option: any) => {
          const { key, ...otherProps } = props;
          return (
            <li key={option.label} {...otherProps}>
              <div>
                <div>{option.label}</div>
                {option.isDbVariable && (
                  <div style={{ fontSize: "0.8em", color: "#666" }}>
                    Database List Variable
                  </div>
                )}
                {option.isSwitchCase && (
                  <div style={{ fontSize: "0.8em", color: "#666" }}>
                    Switch Case (Array Outcomes)
                  </div>
                )}
              </div>
            </li>
          );
        }}
        noOptionsText="No array fields found"
        clearOnBlur={false}
        selectOnFocus
        handleHomeEndKeys
      />
    </Box>
  );
};

interface ConditionNameInputProps {
  conditionName?: string;
  onNameChange: (...a: any[]) => void;
  nameError?: string;
}

const ConditionNameInput = ({
  conditionName,
  onNameChange,
  nameError,
}: ConditionNameInputProps) => {
  return (
    <Box sx={{ mb: 2 }}>
      <TextField
        fullWidth
        label="Condition Name"
        value={conditionName}
        onChange={(e: any) => onNameChange(e.target.value)}
        variant="outlined"
        size="small"
        error={!!nameError}
        helperText={nameError || "Give your list condition a descriptive name"}
        placeholder="e.g., High Priority Observations, Quality Detections"
      />
    </Box>
  );
};

interface ListOperatorSelectorProps {
  selectedOperator?: string;
  onOperatorChange: (...a: any[]) => void;
  operators?: any[];
}

const ListOperatorSelector = ({
  selectedOperator,
  onOperatorChange,
  operators,
}: ListOperatorSelectorProps) => {
  const getOperatorDescription = (operator: string) => {
    const descriptions: Record<string, string> = {
      $anyElementTrue:
        "Returns true if any element in the array matches the conditions",
      $allElementsTrue:
        "Returns true if all elements in the array match the conditions",
      $filter:
        "Filters the array to return only elements that match the conditions",
      $map: "Transforms each element in the array by applying an expression",
      $all: "Returns true if the array contains all specified values",
      $min: "Returns the minimum value from the array elements",
      $max: "Returns the maximum value from the array elements",
      $avg: "Returns the average value from the array elements",
      $sum: "Returns the sum of all array elements",
      $size: "Returns the number of elements in the array",
      $stdDevPop:
        "Returns the population standard deviation of the array elements",
      $median: "Returns the median value from the array elements",
    };
    return descriptions[operator] || "";
  };

  const getOperatorOutputType = (operator: string) => {
    // Boolean-returning operators
    if (["$anyElementTrue", "$allElementsTrue"].includes(operator)) {
      return "boolean";
    }
    // Array-returning operators
    if (["$filter", "$map"].includes(operator)) {
      return "array";
    }
    // Number-returning operators
    if (
      [
        "$min",
        "$max",
        "$avg",
        "$sum",
        "$size",
        "$stdDevPop",
        "$median",
      ].includes(operator)
    ) {
      return "number";
    }
    // For others, return null (don't display type)
    return null;
  };

  return (
    <Box sx={{ mb: 2 }}>
      <FormControl fullWidth variant="outlined">
        <InputLabel>List Operator</InputLabel>
        <Select
          value={selectedOperator || ""}
          onChange={(e: any) => onOperatorChange(e.target.value)}
          label="List Operator"
        >
          {operators?.map((op: any) => (
            <MenuItem key={op.value} value={op.value}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  width: "100%",
                }}
              >
                <span>{op.label}</span>
                {getOperatorOutputType(op.value) && (
                  <Box
                    component="span"
                    sx={{
                      ml: "auto",
                      px: 1,
                      py: 0.25,
                      fontSize: "0.7rem",
                      fontWeight: 600,
                      color: "#1e40af",
                      backgroundColor: "#dbeafe",
                      border: "1px solid #93c5fd",
                      borderRadius: 1,
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                    }}
                  >
                    → {getOperatorOutputType(op.value)}
                  </Box>
                )}
              </Box>
            </MenuItem>
          )) || []}
        </Select>
      </FormControl>
      {selectedOperator && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ mt: 0.5, display: "block" }}
        >
          {getOperatorDescription(selectedOperator)}
        </Typography>
      )}
    </Box>
  );
};

interface ConditionBuilderSectionProps {
  selectedOperator: string;
  selectedArrayField?: string;
  conditionName?: string;
  localFilters: any[];
  setLocalFilters: (...a: any[]) => void;
  subFieldOptions: any[];
  fieldOptions: any[];
  mapFields: any[];
  onMapFieldsChange: (...a: any[]) => void;
  customVariables: any[];
}

const ConditionBuilderSection = ({
  selectedOperator,
  selectedArrayField,
  conditionName,
  localFilters,
  setLocalFilters,
  subFieldOptions,
  fieldOptions, // Receive as prop instead of computing
  mapFields,
  onMapFieldsChange,
  customVariables,
}: ConditionBuilderSectionProps) => {
  const shouldShowConditionBuilder =
    OPERATORS_NEEDING_CONDITIONS.includes(selectedOperator);

  const shouldShowMapEditor = selectedOperator === "$map";

  if (!shouldShowConditionBuilder && !shouldShowMapEditor) {
    return null;
  }

  // Show Map Expression Editor for $map operator
  if (shouldShowMapEditor) {
    return (
      <MapExpressionEditor
        mapFields={mapFields}
        onMapFieldsChange={onMapFieldsChange}
        arrayField={selectedArrayField as any}
        subFieldOptions={subFieldOptions}
        customVariables={customVariables}
      />
    );
  }

  // Get the array field and its subfields
  const arrayField = fieldOptions.find(
    (f: any) => f.type === "array" && f.label === selectedArrayField,
  );

  // Check if the selected field is a custom list variable (from subFieldOptions)
  const isCustomListVariable =
    subFieldOptions &&
    subFieldOptions.length > 0 &&
    !arrayField?.arrayItems?.fields;

  if (!arrayField || !arrayField.arrayItems || !arrayField.arrayItems.fields) {
    // For cross_matches style fields, we should use the passed subFieldOptions
    if (subFieldOptions && subFieldOptions.length > 0) {
      const fieldOptionsList = [...(fieldOptions || []), ...subFieldOptions];

      return (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Define conditions that elements in the list must match:
          </Typography>

          {localFilters.length > 0 && (
            <Paper
              sx={{
                border: 2,
                borderColor: "success.light",
                borderRadius: 2,
                p: 2,
                background: "linear-gradient(90deg, #f0fdf4 60%, #d1fae5 100%)",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  mb: 1,
                }}
              >
                <Chip
                  label={`Conditions for: ${selectedArrayField}`}
                  size="small"
                  color="success"
                  variant="outlined"
                />
              </Box>

              <BlockComponent
                block={localFilters[0]}
                parentBlockId={null}
                isRoot={true}
                fieldOptionsList={fieldOptionsList}
                isListDialogOpen={true}
                // Pass the local filters and setter directly as props
                localFilters={localFilters}
                setLocalFilters={setLocalFilters}
              />
            </Paper>
          )}
        </Box>
      );
    }
    return null;
  }

  // Create subfield options with consistent structure and proper type mapping
  const subFieldOptionsConsistent = arrayField.arrayItems.fields.map(
    (sub: any) => {
      // Create a new object without the 'name' property to avoid conflicts
      const { name, ...subWithoutName } = sub;
      return {
        ...subWithoutName,
        label: `${selectedArrayField}.${name}`,
        type: getSimpleType(sub.type), // Ensure proper type mapping for operator selection
        isSchemaField: true, // Mark as schema field for proper metadata routing
      };
    },
  );

  // For custom list variables, use subFieldOptions as-is (already properly formatted)
  // For schema fields, use the subFieldOptionsConsistent with prefixes
  const fieldOptionsList = isCustomListVariable
    ? [...(fieldOptions || []), ...subFieldOptions]
    : [...(fieldOptions || []), ...subFieldOptionsConsistent];

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Define conditions that elements in the list must match:
      </Typography>

      {localFilters.length > 0 && (
        <Paper
          sx={{
            border: 2,
            borderColor: "success.light",
            borderRadius: 2,
            p: 2,
            background: "linear-gradient(90deg, #f0fdf4 60%, #d1fae5 100%)",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              mb: 1,
            }}
          >
            <Chip
              label={`Conditions for: ${selectedArrayField}`}
              size="small"
              sx={{
                fontSize: "0.75rem",
                fontWeight: 500,
                color: "success.dark",
                bgcolor: "success.light",
                border: 1,
                borderColor: "success.main",
              }}
            />
            {conditionName && (
              <Typography
                variant="caption"
                sx={{ color: "success.dark", fontStyle: "italic" }}
              >
                &quot;{conditionName}&quot;
              </Typography>
            )}
          </Box>
          <BlockComponent
            block={localFilters[0]}
            parentBlockId={null}
            isRoot={true}
            fieldOptionsList={fieldOptionsList}
            isListDialogOpen={true}
            // Pass the local filters and setter directly as props
            localFilters={localFilters}
            setLocalFilters={setLocalFilters}
          />
        </Paper>
      )}
    </Box>
  );
};

const AddListConditionDialog = () => {
  const {
    listConditionDialog,
    setListConditionDialog,
    filters,
    setFilters,
    createDefaultBlock,
    setCustomListVariables,
    customListVariables,
    customVariables,
    customBlocks,
    customSwitchCases,
    localFiltersUpdater,
    fieldOptions, // Get fieldOptions from context instead of computing it here
  } = useCurrentBuilder();

  // State for $map operator - now array of field definitions
  const [mapFields, setMapFields] = useState<any[]>([
    { fieldName: "", expression: "" },
  ]);

  // Error state for better error display
  const [error, setError] = useState("");

  // Use our custom hooks
  const form = useListConditionForm(
    fieldOptions,
    customListVariables,
    customSwitchCases,
  );

  const dialog: any = useListConditionDialog(
    listConditionDialog,
    filters,
    customListVariables,
    createDefaultBlock,
  );
  const save = useListConditionSave();
  const dispatch = useAppDispatch();
  const stream = useAppSelector(
    (state: any) => state.boom_filter_v.stream?.name,
  );

  // Auto-populate form when opening inline with condition data
  useEffect(() => {
    if (listConditionDialog.open && listConditionDialog.conditionId) {
      // Auto-set the array field from the condition
      if (dialog.listFieldNameFromCondition && !form.selectedArrayField) {
        form.setSelectedArrayField(dialog.listFieldNameFromCondition);
        dialog.handleFieldSelection(
          dialog.listFieldNameFromCondition,
          dialog.operatorFromCondition || "",
          form.setSelectedSubField,
        );
      }

      // Auto-set the operator from the condition
      if (dialog.operatorFromCondition && !form.selectedOperator) {
        form.setSelectedOperator(dialog.operatorFromCondition);
        dialog.handleOperatorChange(
          dialog.operatorFromCondition,
          dialog.listFieldNameFromCondition,
        );
      }

      // Auto-populate $map fields if editing a $map condition
      if (dialog.operatorFromCondition === "$map" && dialog.conditionValue) {
        const mapData = dialog.conditionValue;
        if (mapData.mapExpression) {
          // Convert mapExpression object to array of fields
          const entries = Object.entries(mapData.mapExpression);
          if (entries.length > 0) {
            const fields = entries.map(([fieldName, expression]) => ({
              fieldName,
              expression,
            }));
            setMapFields(fields);
          }
        }
      }
    }
  }, [listConditionDialog.open, listConditionDialog.conditionId, dialog, form]);

  const handleClose = () => {
    setListConditionDialog({ open: false, blockId: null });
    form.resetForm();
    dialog.resetDialog();
    // Reset $map state
    setMapFields([{ fieldName: "", expression: "" }]);
    setError(""); // Clear error on close
  };

  const handleFieldSelection = (fieldLabel: string) => {
    form.setSelectedArrayField(fieldLabel);
    // Pass empty string for operator since we haven't selected one yet when field changes
    dialog.handleFieldSelection(fieldLabel, "", form.setSelectedSubField);
  };

  const handleOperatorChange = (newOperator: string) => {
    form.setSelectedOperator(newOperator);
    dialog.handleOperatorChange(newOperator, form.selectedArrayField);
  };

  const handleSave = async () => {
    setError(""); // Clear any previous error

    const validationError = save.validateSaveConditions(
      dialog.listFieldName,
      form.selectedOperator,
      form.selectedSubField,
      form.conditionName,
      form.nameError,
      dialog.localFilters,
      form.validateConditionName,
    );

    if (validationError) {
      setError(validationError);
      return;
    }

    // Check if the selected base field is a list variable that must be defined
    const selectedFieldOption = form.availableArrayFields.find(
      (field: any) => field.label === dialog.listFieldName,
    );
    if (selectedFieldOption?.isListVariable) {
      const baseListVariable = customListVariables.find(
        (lv: any) => lv.name === dialog.listFieldName,
      );
      if (!baseListVariable || !baseListVariable.listCondition) {
        setError(
          `The list variable "${dialog.listFieldName}" must be defined before it can be used. Please save it first.`,
        );
        return;
      }
    }

    // Check if variable name starts with a number
    if (/^[0-9]/.test(form.conditionName.trim())) {
      setError("Variable names cannot start with a number");
      return;
    }

    // Check if variable name contains invalid characters
    const invalidChars = /[\s\-+*^\/%= ]/;
    if (invalidChars.test(form.conditionName.trim())) {
      setError(
        "Variable names cannot contain spaces or mathematical operators (-, +, *, ^, /, %, =)",
      );
      return;
    }

    // Check if an arithmetic variable with the same name already exists
    if (
      customVariables?.some((v: any) => v.name === form.conditionName.trim())
    ) {
      setError(
        `A variable with the name "${form.conditionName.trim()}" already exists. Please choose a different name.`,
      );
      return;
    }

    // Check if a list variable with the same name already exists
    if (
      customListVariables?.some(
        (lv: any) => lv.name === form.conditionName.trim(),
      )
    ) {
      setError(
        `A variable with the name "${form.conditionName.trim()}" already exists. Please choose a different name.`,
      );
      return;
    }

    // Check if a block with the same name already exists
    if (
      customBlocks?.some(
        (b: any) => b.name === `Custom.${form.conditionName.trim()}`,
      )
    ) {
      setError(
        `A variable with the name "${form.conditionName.trim()}" already exists. Please choose a different name.`,
      );
      return;
    }

    // Check if conditions are required for this operator
    const operatorNeedsConditions = OPERATORS_NEEDING_CONDITIONS.includes(
      form.selectedOperator,
    );
    const operatorNeedsSubField = OPERATORS_NEEDING_SUBFIELD.includes(
      form.selectedOperator,
    );
    const isMapOperator = form.selectedOperator === "$map";

    // Build map expression object if it's a $map operator
    let mapExpressionObj: Record<string, any> | null = null;
    if (isMapOperator) {
      // Validate that at least one field is defined
      const validFields = mapFields.filter(
        (f: any) => f.fieldName && f.expression,
      );
      if (validFields.length === 0) {
        alert(
          "Please provide at least one field with both a name and an expression for the $map operator.",
        );
        return;
      }
      // Build the map expression structure: { field1: expression1, field2: expression2, ... }
      mapExpressionObj = validFields.reduce((acc: any, field: any) => {
        let expressionValue = field.expression;

        // Check if the expression is a variable and add $ prefix
        const isVariable = customVariables.some(
          (v: any) => v.name === expressionValue,
        );
        const isListVariable = customListVariables.some(
          (lv: any) => lv.name === expressionValue,
        );

        if (isVariable || isListVariable) {
          expressionValue = `$${expressionValue}`;
        }

        acc[field.fieldName] = expressionValue;
        return acc;
      }, {});
    }

    // Create a list condition that wraps the inner conditions
    const listCondition = {
      type: "array",
      field: dialog.listFieldName,
      operator: form.selectedOperator,
      value: operatorNeedsConditions
        ? dialog.localFilters[0]
        : isMapOperator
          ? { mapExpression: mapExpressionObj }
          : null,
      subField: operatorNeedsSubField ? form.selectedSubField : null,
      subFieldOptions: (() => {
        // For map operators, generate subFieldOptions from mapExpression only
        if (isMapOperator && mapExpressionObj) {
          return Object.keys(mapExpressionObj).map((subfieldName) => ({
            label: subfieldName,
            type: "number", // Could be inferred from expression
            group: `${form.conditionName.trim()} Fields`,
          }));
        }

        // First check if the array field is a list variable
        const existingListVar = customListVariables.find(
          (lv: any) => lv.name === dialog.listFieldName,
        );
        if (existingListVar && existingListVar.listCondition?.subFieldOptions) {
          // Use subFieldOptions from the existing list variable.
          // Strip to bare subfield name — handleFieldSelection will re-prefix
          // with the input variable name at runtime (so "prv_candidates.jd" → "jd"
          // stored here, then "myVar1.jd" when used as input to another condition).
          return existingListVar.listCondition.subFieldOptions.map(
            (opt: any) => {
              const subfieldName = opt.label.includes(".")
                ? opt.label.split(".").pop()
                : opt.label;

              return {
                ...opt,
                group:
                  existingListVar.listCondition.operator === "$map"
                    ? opt.group
                    : undefined,
                label: subfieldName,
              };
            },
          );
        }

        // Use the same comprehensive field options that were used in the dialog
        if (operatorNeedsConditions) {
          const arrayField = fieldOptions.find(
            (f: any) => f.type === "array" && f.label === dialog.listFieldName,
          );
          if (
            arrayField &&
            arrayField.arrayItems &&
            arrayField.arrayItems.fields
          ) {
            return arrayField.arrayItems.fields.map((sub: any) => {
              const { name, ...subWithoutName } = sub;
              return {
                ...subWithoutName,
                label: `${dialog.listFieldName}.${name}`,
                type: getSimpleType(sub.type),
                isSchemaField: true,
              };
            });
          }
        }
        // Fall back to the original subFieldOptions from dialog
        return dialog.subFieldOptions;
      })(),
      name: form.conditionName.trim(),
    };

    const apiResult: any = await dispatch(
      postElement({
        name: form.conditionName.trim(),
        data: {
          listCondition: listCondition,
          type: "array",
          streams: [stream],
        },
        elements: "listVariables",
      }),
    );

    const success = await save.saveListCondition({
      listFieldName: dialog.listFieldName,
      selectedOperator: form.selectedOperator,
      selectedSubField: form.selectedSubField,
      conditionName: form.conditionName,
      localFilters: dialog.localFilters,
      subFieldOptions: listCondition.subFieldOptions,
      saved: apiResult?.status === "success",
      listCondition: listCondition,
      listConditionDialog,
      setCustomListVariables,
      setFilters: setFilters,
      setLocalFilters: localFiltersUpdater,
    });

    // Only close if both the API call and the filter update succeeded
    if (success && apiResult?.status === "success") {
      // Add a small delay to ensure state updates have processed
      setTimeout(() => {
        handleClose();
      }, 100);
    }
  };

  const isFormValid = () => {
    const operatorNeedsSubField = OPERATORS_NEEDING_SUBFIELD.includes(
      form.selectedOperator,
    );
    const operatorNeedsConditions = OPERATORS_NEEDING_CONDITIONS.includes(
      form.selectedOperator,
    );
    const isMapOperator = form.selectedOperator === "$map";

    return (
      form.selectedArrayField &&
      form.selectedOperator &&
      form.conditionName.trim() &&
      !form.nameError &&
      (!operatorNeedsSubField || form.selectedSubField) &&
      (!operatorNeedsConditions ||
        (dialog.localFilters.length > 0 &&
          dialog.localFilters[0].children.length > 0)) &&
      (!isMapOperator ||
        mapFields.some((f: any) => {
          const fieldName = typeof f.fieldName === "string" ? f.fieldName : "";
          const expression = normalizeFieldValue(f.expression);
          return fieldName.trim() && expression.trim();
        }))
    );
  };

  return (
    <Dialog
      open={listConditionDialog.open}
      onClose={handleClose}
      maxWidth="lg"
      fullWidth
      disableRestoreFocus={false}
      slotProps={{
        paper: {
          style: { minHeight: 600 },
          "aria-labelledby": "add-list-condition-dialog-title",
        } as any,
        root: {
          "aria-hidden": false,
        } as any,
      }}
    >
      <DialogTitle id="add-list-condition-dialog-title">
        Add List Condition
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <ArrayFieldSelector
            selectedArrayField={form.selectedArrayField}
            onFieldChange={handleFieldSelection}
            availableArrayFields={form.availableArrayFields}
          />

          {form.selectedArrayField && (
            <>
              <ListOperatorSelector
                selectedOperator={form.selectedOperator}
                onOperatorChange={handleOperatorChange}
                operators={dialog.arrayOperators}
              />

              <SubFieldSelector
                selectedSubField={form.selectedSubField}
                onSubFieldChange={form.setSelectedSubField}
                subFieldOptions={dialog.subFieldOptions}
                selectedOperator={form.selectedOperator}
              />

              <ConditionNameInput
                conditionName={form.conditionName}
                onNameChange={form.handleNameChange}
                nameError={form.nameError}
              />

              <ConditionBuilderSection
                selectedOperator={form.selectedOperator}
                selectedArrayField={form.selectedArrayField}
                conditionName={form.conditionName}
                localFilters={dialog.localFilters}
                setLocalFilters={dialog.setLocalFilters}
                subFieldOptions={dialog.subFieldOptions}
                fieldOptions={fieldOptions}
                mapFields={mapFields}
                onMapFieldsChange={setMapFields}
                customVariables={customVariables}
              />
            </>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSave}
          disabled={!isFormValid()}
        >
          Add List Condition
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddListConditionDialog;
