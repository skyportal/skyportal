import { useCallback, useEffect } from "react";
import { FormControlLabel, Switch } from "@mui/material";
import {
  mongoOperatorLabels,
  flattenFieldOptions,
} from "../../../../constants/filterConstants";
import {
  getOperatorsForField,
  getFieldType,
} from "../../../../utils/conditionHelpers";
import { useConditionContext } from "../../../../hooks/useContexts";
import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
import { styled, lighten, darken } from "@mui/system";
import { useAppSelector } from "../../../../types/hooks";

const GroupHeader = styled("div")(({ theme }: { theme: any }) => {
  // Fallbacks for palette
  const primaryMain = theme.palette?.primary?.main || "#1976d2";
  const primaryLight = theme.palette?.primary?.light || "#42a5f5";
  const isDark = theme.palette?.mode === "dark";
  return {
    position: "sticky",
    top: "-8px",
    padding: "4px 10px",
    color: primaryMain,
    backgroundColor: isDark
      ? darken(primaryMain, 0.8)
      : lighten(primaryLight, 0.85),
  };
});

const GroupItems = styled("ul")({
  padding: 0,
});

interface AutocompleteOperatorsProps {
  operators?: string[];
  value?: string | null;
  onChange?: ((value: string) => void) | null;
  mongoOperatorLabels_?: Record<string, any>;
  style?: any;
}

const AutocompleteOperators = ({
  operators = [],
  value = "",
  onChange = null,
  mongoOperatorLabels_ = {},
}: AutocompleteOperatorsProps) => {
  // Prepare options with label
  const options = (operators || []).map((op: any) => ({
    value: op,
    label: mongoOperatorLabels_[op] || op,
    group: "Operators",
  }));

  return (
    <Autocomplete
      size="small"
      options={options}
      groupBy={(option: any) => option.group}
      getOptionLabel={(option: any) => option.label}
      sx={{
        width: "100%",
        minWidth: 150,
        "& .MuiAutocomplete-popper": {
          zIndex: 1300,
        },
      }}
      value={options.find((opt: any) => opt.value === value) || null}
      onChange={(_: any, newValue: any) =>
        onChange && onChange(newValue ? newValue.value : "")
      }
      renderInput={(params: any) => <TextField {...params} label="Operator" />}
      renderOption={(props: any, option: any) => {
        const { key, ...otherProps } = props;
        return (
          <li key={option.value} {...otherProps}>
            {option.label}
          </li>
        );
      }}
      renderGroup={(params: any) => (
        <li key={params.key}>
          <GroupHeader>{params.group}</GroupHeader>
          <GroupItems>{params.children}</GroupItems>
        </li>
      )}
      isOptionEqualToValue={(option: any, val: any) =>
        option.value === val.value
      }
    />
  );
};

// Helper function to check if a field is boolean (same logic as ValueInput)
const isBooleanField = (
  conditionOrBlock: any,
  customVariables: any,
  fieldOptionsList: any,
  customSwitchCases: any[] = [],
  schema: any = null,
  fieldOptions: any[] = [],
) => {
  // Use getFieldType to properly check the type, including for switch cases
  const fieldType = getFieldType(
    conditionOrBlock.field,
    customVariables,
    schema,
    fieldOptions,
    fieldOptionsList,
    [], // customListVariables - not needed for boolean check
    customSwitchCases,
  );

  return fieldType === "boolean";
};

interface OperatorSelectorProps {
  conditionOrBlock: any;
  block: any;
  operatorOptions: string[];
  updateCondition: (...a: any[]) => void;
}

const OperatorSelector = ({
  conditionOrBlock,
  block,
  operatorOptions,
  updateCondition,
}: OperatorSelectorProps) => {
  const {
    customListVariables,
    customVariables,
    fieldOptionsList,
    customSwitchCases,
  } = useConditionContext();

  const schema = useAppSelector((state: any) => state.filter_modules?.schema);
  const fieldOptions = flattenFieldOptions(schema);

  // Check if this is a list variable
  const fieldName =
    typeof conditionOrBlock.field === "string"
      ? conditionOrBlock.field
      : conditionOrBlock.field?.name || conditionOrBlock.field;

  const listVariable = customListVariables.find(
    (lv: any) => lv.name === fieldName,
  );

  if (listVariable) {
    return (
      <ListVariableOperator
        conditionOrBlock={conditionOrBlock}
        block={block}
        updateCondition={updateCondition}
        listOperator={listVariable.listCondition.operator}
      />
    );
  }

  // Check if this is a boolean field - using the same logic as ValueInput
  if (
    isBooleanField(
      conditionOrBlock,
      customVariables,
      fieldOptionsList,
      customSwitchCases,
      schema,
      fieldOptions,
    )
  ) {
    return (
      <BooleanFieldSwitch
        conditionOrBlock={conditionOrBlock}
        block={block}
        updateCondition={updateCondition}
      />
    );
  }

  // Regular operator autocomplete
  return (
    <AutocompleteOperators
      operators={operatorOptions}
      value={conditionOrBlock.operator}
      onChange={(op: any) =>
        updateCondition(block.id, conditionOrBlock.id, "operator", op)
      }
      mongoOperatorLabels_={mongoOperatorLabels}
      style={{ minWidth: 60, maxWidth: 80 }}
    />
  );
};

// Helper function to determine the output type of a list variable based on its creation operator
const getListVariableOutputType = (listOperator: any) => {
  // Boolean-returning operators
  if (["$anyElementTrue", "$allElementsTrue"].includes(listOperator)) {
    return "boolean";
  }
  // Array-returning operators
  if (["$filter", "$map"].includes(listOperator)) {
    return "array";
  }
  // Number-returning operators
  if (
    ["$min", "$max", "$avg", "$sum", "$size", "$stdDevPop", "$median"].includes(
      listOperator,
    )
  ) {
    return "number";
  }
  // Default to array for unknown operators
  return "array";
};

// Helper function to get default operator based on output type and list operator
const getDefaultOperatorForType = (
  outputType: any,
  listOperator: any = null,
) => {
  // For arrays, prefer the operator used to create the list variable
  if (outputType === "array" && listOperator) {
    return listOperator;
  }

  // For boolean output types with anyElementTrue/allElementsTrue, use the list operator
  if (
    outputType === "boolean" &&
    listOperator &&
    ["$anyElementTrue", "$allElementsTrue"].includes(listOperator)
  ) {
    return listOperator;
  }

  switch (outputType) {
    case "number":
      return "$eq"; // Most common comparison for numbers
    case "boolean":
      return "$eq"; // Check if true/false
    case "array":
      return "$lengthGt"; // Fallback for arrays without a list operator
    default:
      return "$exists";
  }
};

interface ListVariableOperatorProps {
  conditionOrBlock: any;
  block: any;
  updateCondition: (...a: any[]) => void;
  listOperator: string;
}

const ListVariableOperator = ({
  conditionOrBlock,
  block,
  updateCondition,
  listOperator,
}: ListVariableOperatorProps) => {
  const { customVariables, fieldOptionsList, customListVariables } =
    useConditionContext();
  const schema = useAppSelector((state: any) => state.filter_modules?.schema);
  const fieldOptions = flattenFieldOptions(schema);

  const handleOperatorChange = useCallback(
    (op: any) => {
      updateCondition(block.id, conditionOrBlock.id, "operator", op);
    },
    [updateCondition, block.id, conditionOrBlock.id],
  );

  // Determine the output type of this list variable
  const outputType = getListVariableOutputType(listOperator);

  // Get available operators based on the list variable's OUTPUT type
  const getAvailableOperatorsForListVariable = () => {
    // Use getOperatorsForField with the output type to get the appropriate operators
    const operators = getOperatorsForField(
      conditionOrBlock.field,
      customVariables,
      schema,
      fieldOptions,
      fieldOptionsList,
      customListVariables,
      [], // customSwitchCases - empty array since list variables can't be switch cases
    );

    // For number output types, we should use number operators, not array operators
    if (outputType === "number") {
      const baseOperators = ["$exists", "$isNumber"];
      return [
        "$eq",
        "$ne",
        "$gt",
        "$gte",
        "$lt",
        "$lte",
        "$round",
        ...baseOperators,
      ];
    }

    // For boolean output types, use boolean operators
    if (outputType === "boolean") {
      const baseOperators = ["$exists", "$isNumber"];
      // Include the list operator if it's anyElementTrue or allElementsTrue
      if (["$anyElementTrue", "$allElementsTrue"].includes(listOperator)) {
        return [listOperator, "$eq", "$ne", ...baseOperators];
      }
      return ["$eq", "$ne", ...baseOperators];
    }

    // For array output types, use the standard array operators
    return operators;
  };

  const availableOperators = getAvailableOperatorsForListVariable();
  // Set the default operator based on output type if none is currently set
  // OR if the current operator is not valid for this list variable type
  // OR if it looks like a generic default that should be replaced with the list operator
  useEffect(() => {
    // Get the preferred default operator (the operator used to create the list variable)
    const preferredOperator = getDefaultOperatorForType(
      outputType,
      listOperator,
    );

    // Check if we should update the operator
    const hasNoOperator = !conditionOrBlock.operator;
    const hasInvalidOperator =
      conditionOrBlock.operator &&
      !availableOperators.includes(conditionOrBlock.operator);

    // For arrays: also replace if current is a "generic" array operator but preferred is available
    // This handles cases where the operator was auto-set to $anyElementTrue but should be $filter
    const shouldReplaceWithPreferred =
      outputType === "array" &&
      availableOperators.includes(preferredOperator) &&
      ["$anyElementTrue", "$allElementsTrue"].includes(
        conditionOrBlock.operator,
      ) &&
      preferredOperator !== conditionOrBlock.operator;

    if (
      (hasNoOperator || hasInvalidOperator || shouldReplaceWithPreferred) &&
      availableOperators.length > 0
    ) {
      // Use the preferred operator if it's available, otherwise fall back to the first available
      const operatorToSet = availableOperators.includes(preferredOperator)
        ? preferredOperator
        : availableOperators[0];

      updateCondition(block.id, conditionOrBlock.id, "operator", operatorToSet);
    }
  }, [
    block.id,
    conditionOrBlock.id,
    conditionOrBlock.operator,
    availableOperators,
    outputType,
    listOperator,
    updateCondition,
  ]);

  // Use the current operator if set and valid, otherwise fall back to the first available operator
  const currentOperator =
    conditionOrBlock.operator &&
    availableOperators.includes(conditionOrBlock.operator)
      ? conditionOrBlock.operator
      : availableOperators.length > 0
        ? availableOperators[0]
        : null;

  return (
    <AutocompleteOperators
      operators={availableOperators}
      value={currentOperator}
      onChange={handleOperatorChange}
      mongoOperatorLabels_={mongoOperatorLabels}
      style={{ minWidth: 60, maxWidth: 80 }}
    />
  );
};

interface BooleanFieldSwitchProps {
  conditionOrBlock: any;
  block: any;
  updateCondition: (...a: any[]) => void;
}

const BooleanFieldSwitch = ({
  conditionOrBlock,
  block,
  updateCondition,
}: BooleanFieldSwitchProps) => {
  const handleSwitchChange = useCallback(
    (e: any) => {
      updateCondition(block.id, conditionOrBlock.id, "value", e.target.checked);
    },
    [updateCondition, block.id, conditionOrBlock.id],
  );

  return (
    <FormControlLabel
      control={
        <Switch
          checked={conditionOrBlock.value === true}
          onChange={handleSwitchChange}
          color="primary"
        />
      }
      label={String(conditionOrBlock.value === true)}
      labelPlacement="end"
      style={{ marginLeft: 0, marginRight: 8 }}
    />
  );
};

export default OperatorSelector;
