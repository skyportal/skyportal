import { Switch, FormControlLabel, TextField } from "@mui/material";
import ChipArrayInput from "./ChipArrayInput";
import { mongoOperatorTypes } from "../../../../constants/filterConstants";

interface SpecialOperatorInputsProps {
  conditionOrBlock: any;
  block: any;
  updateCondition: (...a: any[]) => void;
}

const SpecialOperatorInputs = ({
  conditionOrBlock,
  block,
  updateCondition,
}: SpecialOperatorInputsProps) => {
  if (conditionOrBlock.operator === "$in") {
    return (
      <ChipArrayInput
        value={conditionOrBlock.value}
        onChange={(newValue: any) =>
          updateCondition(block.id, conditionOrBlock.id, "value", newValue)
        }
        label="Enter values (space or enter to add)"
      />
    );
  }

  if ((mongoOperatorTypes as any)[conditionOrBlock.operator] === "exists") {
    return (
      <FormControlLabel
        control={
          <Switch
            checked={conditionOrBlock.value !== false}
            onChange={(e: any) =>
              updateCondition(
                block.id,
                conditionOrBlock.id,
                "value",
                e.target.checked,
              )
            }
            color="default"
          />
        }
        label={
          conditionOrBlock.operator === "$exists"
            ? conditionOrBlock.value !== false
              ? "True"
              : "False"
            : conditionOrBlock.value !== false
              ? "True"
              : "False"
        }
        labelPlacement="end"
        style={{ marginLeft: 0, marginRight: 8 }}
      />
    );
  }

  if ((mongoOperatorTypes as any)[conditionOrBlock.operator] === "round") {
    return (
      <TextField
        size="small"
        type="number"
        label="Decimal Places"
        value={
          conditionOrBlock.value !== undefined ? conditionOrBlock.value : 0
        }
        onChange={(e: any) =>
          updateCondition(
            block.id,
            conditionOrBlock.id,
            "value",
            parseInt(e.target.value) || 0,
          )
        }
        style={{ minWidth: 120, maxWidth: 150 }}
        slotProps={{ htmlInput: { min: 0, max: 10 } }}
      />
    );
  }

  if (
    (mongoOperatorTypes as any)[conditionOrBlock.operator] === "array_single"
  ) {
    return (
      <TextField
        size="small"
        type="number"
        label={
          conditionOrBlock.operator === "$lengthGt"
            ? "Length Greater Than"
            : conditionOrBlock.operator === "$lengthLt"
              ? "Length Less Than"
              : "Value"
        }
        value={
          conditionOrBlock.value !== undefined && conditionOrBlock.value !== ""
            ? conditionOrBlock.value
            : -1
        }
        onChange={(e: any) =>
          updateCondition(
            block.id,
            conditionOrBlock.id,
            "value",
            parseInt(e.target.value) || 0,
          )
        }
        style={{ minWidth: 120, maxWidth: 150 }}
      />
    );
  }

  if (
    (mongoOperatorTypes as any)[conditionOrBlock.operator] === "array_number"
  ) {
    return (
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <TextField
          size="small"
          type="number"
          label="Divisor"
          value={
            Array.isArray(conditionOrBlock.value)
              ? conditionOrBlock.value[0] || ""
              : ""
          }
          onChange={(e: any) => {
            const divisor = parseInt(e.target.value) || 0;
            const remainder = Array.isArray(conditionOrBlock.value)
              ? conditionOrBlock.value[1] || 0
              : 0;
            updateCondition(block.id, conditionOrBlock.id, "value", [
              divisor,
              remainder,
            ]);
          }}
          style={{ minWidth: 80, maxWidth: 100 }}
        />
        <TextField
          size="small"
          type="number"
          label="Remainder"
          value={
            Array.isArray(conditionOrBlock.value)
              ? conditionOrBlock.value[1] || ""
              : ""
          }
          onChange={(e: any) => {
            const remainder = parseInt(e.target.value) || 0;
            const divisor = Array.isArray(conditionOrBlock.value)
              ? conditionOrBlock.value[0] || 0
              : 0;
            updateCondition(block.id, conditionOrBlock.id, "value", [
              divisor,
              remainder,
            ]);
          }}
          style={{ minWidth: 80, maxWidth: 100 }}
        />
      </div>
    );
  }

  // For aggregation operators, don't show anything additional
  if (
    (mongoOperatorTypes as any)[conditionOrBlock.operator] === "aggregation" ||
    (conditionOrBlock.value &&
      typeof conditionOrBlock.value === "object" &&
      conditionOrBlock.value.type === "array" &&
      conditionOrBlock.value.subField)
  ) {
    return null;
  }

  return null;
};

export default SpecialOperatorInputs;
