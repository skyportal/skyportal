import { useState, useEffect } from "react";
import { Box, MenuItem, Select, FormControl } from "@mui/material";
import AutocompleteFields from "./AutocompleteFields";
import { getFieldOptionsWithVariable } from "../../../../utils/conditionHelpers";
import { useConditionContext } from "../../../../hooks/useContexts";
import { useAppSelector } from "../../../../types/hooks";

interface SimpleConditionRowProps {
  condition?: any;
  onChange?: ((value: any) => void) | null;
}

/**
 * SimpleConditionRow - A minimal condition builder (Field + Operator + Value)
 * Used inside ConditionalValueBuilder to prevent UI inception
 */
const SimpleConditionRow = ({
  condition,
  onChange = null,
}: SimpleConditionRowProps) => {
  const {
    customVariables,
    customListVariables,
    customSwitchCases,
    fieldOptionsList,
  } = useConditionContext();
  const currentStream = useAppSelector(
    (state: any) => state.boom_filter_v.stream?.name,
  );

  const [field, setField] = useState<any>(condition?.field || "");
  const [operator, setOperator] = useState<any>(condition?.operator || "$eq");
  const [value, setValue] = useState<any>(condition?.value || "");

  // Use the same field options as the main filter builder
  const allFieldOptions = getFieldOptionsWithVariable(
    fieldOptionsList,
    customVariables,
    customListVariables,
    customSwitchCases || [],
    [],
    condition?.createdAt,
    currentStream,
  );

  // Common operators
  const operators = [
    { value: "$eq", label: "=" },
    { value: "$ne", label: "≠" },
    { value: "$gt", label: ">" },
    { value: "$gte", label: "≥" },
    { value: "$lt", label: "<" },
    { value: "$lte", label: "≤" },
  ];

  useEffect(() => {
    if (onChange && (field || operator || value)) {
      onChange({
        field,
        operator,
        value,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [field, operator, value]);

  return (
    <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
      {/* Field Selector */}
      <AutocompleteFields
        fieldOptions={allFieldOptions}
        value={field}
        onChange={(newField: any) => setField(newField)}
        conditionOrBlock={{ field, operator, value }}
        setOpenEquationIds={() => {}}
        customVariables={customVariables || []}
        setSelectedChip={() => {}}
        side="left"
        style={{ width: "200px" }}
        customListVariables={customListVariables || []}
      />

      {/* Operator Selector */}
      <FormControl size="small" sx={{ minWidth: 80 }}>
        <Select
          value={operator}
          onChange={(e: any) => setOperator(e.target.value)}
        >
          {operators.map((op: any) => (
            <MenuItem key={op.value} value={op.value}>
              {op.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Value Input */}
      <AutocompleteFields
        fieldOptions={allFieldOptions}
        value={value}
        onChange={(newValue: any) => setValue(newValue)}
        conditionOrBlock={{ field, operator, value }}
        setOpenEquationIds={() => {}}
        customVariables={customVariables || []}
        setSelectedChip={() => {}}
        side="right"
        style={{ width: "200px" }}
        customListVariables={customListVariables || []}
      />
    </Box>
  );
};

export default SimpleConditionRow;
