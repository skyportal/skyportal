import { useConditionContext } from "../../../../hooks/useContexts";
import {
  Button,
  Switch,
  FormControlLabel,
  Popover,
  Paper,
} from "@mui/material";
import AutocompleteFields from "./AutocompleteFields";
import ConditionalValueBuilder from "./ConditionalValueBuilder";
import "katex/dist/katex.min.css";
import Latex from "react-latex-next";
import {
  mongoOperatorTypes,
  flattenFieldOptions,
} from "../../../../constants/filterConstants";
import {
  getFieldOptionsWithVariable,
  normalizeFieldValue,
} from "../../../../utils/conditionHelpers";
import { useAppSelector } from "../../../../types/hooks";

const underscoreLatexForDisplay = (text: any) => {
  if (!text) return text;
  return text.replace(/_/g, "\\_");
};

interface EquationPopoverProps {
  openEquationIds: string[];
  conditionId: string;
  selectedChip: string;
  fieldOptionsWithVariable: any[];
  conditionOrBlock: any;
  customVariables: any[];
  anchorEl?: any;
  onClose: (...a: any[]) => void;
}

export const EquationPopover = ({
  openEquationIds,
  conditionId,
  selectedChip,
  fieldOptionsWithVariable,
  conditionOrBlock,
  customVariables,
  anchorEl,
  onClose,
}: EquationPopoverProps) => {
  const isOpen = openEquationIds.includes(conditionId) && anchorEl;

  if (!isOpen) return null;

  let variableOption: any;
  if (selectedChip === "left") {
    variableOption = fieldOptionsWithVariable.find(
      (opt: any) =>
        opt.label ===
          (conditionOrBlock.field || conditionOrBlock.variableName) &&
        opt.isVariable,
    );
  }
  if (selectedChip === "right") {
    variableOption = fieldOptionsWithVariable.find(
      (opt: any) => opt.label === conditionOrBlock.value && opt.isVariable,
    );
  }

  if (!variableOption) return null;

  const eqObj = customVariables.find(
    (eq: any) => eq.variable === variableOption.label,
  );
  const equation = eqObj ? eqObj.variable : variableOption.equation;
  const displayEquation = underscoreLatexForDisplay(equation);

  return (
    <Popover
      open={!!isOpen}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{
        vertical: "center",
        horizontal: "right",
      }}
      transformOrigin={{
        vertical: "center",
        horizontal: "left",
      }}
      sx={{
        "& .MuiPopover-paper": {
          maxWidth: 600,
          minWidth: 300,
        },
      }}
    >
      <Paper
        elevation={3}
        sx={{
          p: 2,
          background: "#fef3c7",
          border: "1px solid #fde68a",
          borderRadius: 2,
        }}
      >
        <Latex>{`$$${displayEquation}$$`}</Latex>
      </Paper>
    </Popover>
  );
};

const shouldSkipValueInput = (conditionOrBlock: any) => {
  return (
    (mongoOperatorTypes as any)[conditionOrBlock.operator] === "exists" ||
    (mongoOperatorTypes as any)[conditionOrBlock.operator] === "array_single" ||
    (mongoOperatorTypes as any)[conditionOrBlock.operator] === "array_number" ||
    (mongoOperatorTypes as any)[conditionOrBlock.operator] === "round" ||
    ((mongoOperatorTypes as any)[conditionOrBlock.operator] === "aggregation" &&
      conditionOrBlock.value &&
      typeof conditionOrBlock.value === "object" &&
      conditionOrBlock.value.type === "array" &&
      conditionOrBlock.value.subField)
  );
};

interface ArrayFieldInputProps {
  conditionOrBlock: any;
  block: any;
}

const ArrayFieldInput = ({ conditionOrBlock, block }: ArrayFieldInputProps) => {
  const { setListConditionDialog } = useConditionContext();

  // For all array operators that should show the "+ List Variable" button
  return (
    <Button
      variant="outlined"
      color="primary"
      onClick={() => {
        if (setListConditionDialog) {
          setListConditionDialog({
            open: true,
            blockId: block.id,
            conditionId: conditionOrBlock.id,
          });
        }
      }}
      sx={{
        minWidth: 150,
        height: 40,
        borderStyle: "fixed",
        borderWidth: 2,
        "&:hover": {
          borderStyle: "fixed",
          borderWidth: 2,
        },
      }}
    >
      + List Variable
    </Button>
  );
};

interface ListVariableInputProps {
  listVariable: any;
  conditionOrBlock: any;
  block: any;
  updateCondition: (...a: any[]) => void;
  setOpenEquationIds: (...a: any[]) => void;
  setSelectedChip: (...a: any[]) => void;
  setEquationAnchor?: ((...a: any[]) => void) | null;
}

const ListVariableInput = ({
  listVariable,
  conditionOrBlock,
  block,
  updateCondition,
  setOpenEquationIds,
  setSelectedChip,
  setEquationAnchor = null,
}: ListVariableInputProps) => {
  const {
    customVariables,
    customListVariables,
    fieldOptionsList,
    customSwitchCases,
    isListDialogOpen,
    setListConditionDialog,
  } = useConditionContext();
  const currentStream = useAppSelector(
    (state: any) => state.boom_filter_v.stream?.name,
  );
  const operator =
    listVariable.listCondition?.operator || listVariable.operator;
  const selectedOperator = conditionOrBlock.operator;

  // For $in and $nin operators, always show AutocompleteFields
  if (selectedOperator === "$in" || selectedOperator === "$nin") {
    return (
      <AutocompleteFields
        key={`${conditionOrBlock.id}.right`}
        fieldOptions={getFieldOptionsWithVariable(
          fieldOptionsList,
          customVariables,
          customListVariables,
          customSwitchCases || [],
          [],
          conditionOrBlock.createdAt,
          currentStream,
        )}
        value={(() => {
          const val = conditionOrBlock.value;
          if (!val) return "";
          if (typeof val === "string") return val;
          if (typeof val === "object" && val.name) return val.name;
          return String(val);
        })()}
        onChange={(newValue: any) =>
          updateCondition(block.id, conditionOrBlock.id, "value", newValue)
        }
        conditionOrBlock={conditionOrBlock}
        setOpenEquationIds={setOpenEquationIds}
        customVariables={[]}
        setSelectedChip={setSelectedChip}
        side={"right"}
        style={{ width: "100%" }}
        isListDialog={isListDialogOpen}
        customListVariables={customListVariables}
        setEquationAnchor={setEquationAnchor}
      />
    );
  }

  // For array operators ($anyElementTrue, $allElementsTrue), show a boolean switch
  if (
    conditionOrBlock.operator === "$anyElementTrue" ||
    conditionOrBlock.operator === "$allElementsTrue"
  ) {
    return (
      <FormControlLabel
        control={
          <Switch
            checked={conditionOrBlock.booleanSwitch !== false}
            onChange={(e: any) =>
              updateCondition(
                block.id,
                conditionOrBlock.id,
                "booleanSwitch",
                e.target.checked,
              )
            }
            color="primary"
          />
        }
        label={conditionOrBlock.booleanSwitch !== false ? "True" : "False"}
        labelPlacement="end"
        style={{ marginLeft: 0, marginRight: 8, minWidth: 100 }}
      />
    );
  }

  // For aggregation list variables with comparison operators, show regular value input
  if (
    (mongoOperatorTypes as any)[operator] === "aggregation" &&
    (mongoOperatorTypes as any)[conditionOrBlock.operator] === "comparison"
  ) {
    return (
      <AutocompleteFields
        key={`${conditionOrBlock.id}.right`}
        fieldOptions={getFieldOptionsWithVariable(
          fieldOptionsList,
          customVariables,
          customListVariables,
          customSwitchCases || [],
          [],
          conditionOrBlock.createdAt,
          currentStream,
        )}
        value={(() => {
          const val = conditionOrBlock.value;
          if (!val) return "";
          if (typeof val === "string") return val;
          if (typeof val === "object" && val.name) return val.name;
          return String(val);
        })()}
        onChange={(newValue: any) =>
          updateCondition(block.id, conditionOrBlock.id, "value", newValue)
        }
        conditionOrBlock={conditionOrBlock}
        setOpenEquationIds={setOpenEquationIds}
        customVariables={[]}
        setSelectedChip={setSelectedChip}
        side={"right"}
        style={{ width: "100%" }}
        isListDialog={isListDialogOpen}
        customListVariables={customListVariables}
        setEquationAnchor={setEquationAnchor}
      />
    );
  }

  // Check if we need the "+ List Variable" button
  const isFilterVariable =
    listVariable &&
    (listVariable.listCondition?.operator === "$filter" ||
      listVariable.operator === "$filter");
  const currentOperator = conditionOrBlock.operator;
  const isArrayOrAggregationOperator =
    (mongoOperatorTypes as any)[currentOperator] === "array" ||
    (mongoOperatorTypes as any)[currentOperator] === "aggregation";

  if (isFilterVariable && isArrayOrAggregationOperator) {
    return (
      <Button
        variant="outlined"
        color="primary"
        onClick={() => {
          if (setListConditionDialog) {
            setListConditionDialog({
              open: true,
              blockId: block.id,
              conditionId: conditionOrBlock.id,
            });
          }
        }}
        sx={{
          minWidth: 150,
          height: 40,
          borderStyle: "fixed",
          borderWidth: 2,
          "&:hover": {
            borderStyle: "fixed",
            borderWidth: 2,
          },
        }}
      >
        + List Variable
      </Button>
    );
  }

  // For other list variables, show empty AutocompleteFields (disabled)
  return (
    <AutocompleteFields
      key={`${conditionOrBlock.id}.right`}
      fieldOptions={[]}
      value={""}
      onChange={() => {}} // Disabled for list variables
      conditionOrBlock={{ ...conditionOrBlock, value: "" }}
      setOpenEquationIds={setOpenEquationIds}
      customVariables={[]}
      setSelectedChip={setSelectedChip}
      side={"right"}
      style={{ width: "100%", opacity: 0.5 }}
      isListDialog={isListDialogOpen}
      customListVariables={customListVariables}
      setEquationAnchor={setEquationAnchor}
    />
  );
};

interface ConditionalValueInputProps {
  conditionOrBlock: any;
  block: any;
  updateCondition: (...a: any[]) => void;
  defaultCondition: (...a: any[]) => any;
  defaultBlock: (...a: any[]) => any;
  fieldOptionsList?: any[];
}

export const ConditionalValueInput = ({
  conditionOrBlock,
  block,
  updateCondition,
  defaultCondition,
  defaultBlock,
  fieldOptionsList,
}: ConditionalValueInputProps) => {
  const handleSwitchDataChange = (newSwitchData: any) => {
    updateCondition(block.id, conditionOrBlock.id, "value", newSwitchData);
  };

  return (
    <ConditionalValueBuilder
      value={conditionOrBlock.value}
      onChange={handleSwitchDataChange}
      defaultCondition={defaultCondition}
      defaultBlock={defaultBlock}
      fieldOptionsList={fieldOptionsList}
    />
  );
};

interface RegularValueInputProps {
  conditionOrBlock: any;
  block: any;
  updateCondition: (...a: any[]) => void;
  setOpenEquationIds: (...a: any[]) => void;
  setSelectedChip: (...a: any[]) => void;
  setEquationAnchor?: ((...a: any[]) => void) | null;
}

const RegularValueInput = ({
  conditionOrBlock,
  block,
  updateCondition,
  setOpenEquationIds,
  setSelectedChip,
  setEquationAnchor = null,
}: RegularValueInputProps) => {
  const {
    customVariables,
    customListVariables,
    customSwitchCases,
    fieldOptionsList,
    isListDialogOpen,
  } = useConditionContext();
  const currentStream = useAppSelector(
    (state: any) => state.boom_filter_v.stream?.name,
  );

  return (
    <AutocompleteFields
      key={`${conditionOrBlock.id}.right`}
      fieldOptions={getFieldOptionsWithVariable(
        fieldOptionsList,
        customVariables,
        customListVariables,
        customSwitchCases || [],
        [],
        conditionOrBlock.createdAt,
        currentStream,
      )}
      value={(() => {
        // Check if this is an aggregation operator that should be shown on the left
        const isAggregationOnLeft =
          conditionOrBlock.value &&
          typeof conditionOrBlock.value === "object" &&
          conditionOrBlock.value.type === "array" &&
          conditionOrBlock.value.subField &&
          ["$min", "$max", "$avg", "$sum"].includes(conditionOrBlock.operator);

        const rawValue = isAggregationOnLeft ? "" : conditionOrBlock.value;

        // Normalize value to handle both string and object formats
        if (rawValue === null || rawValue === undefined) {
          return "";
        }
        if (typeof rawValue === "string") return rawValue;
        if (typeof rawValue === "object" && rawValue.name) return rawValue.name;
        return String(rawValue);
      })()}
      onChange={(newValue: any) => {
        updateCondition(block.id, conditionOrBlock.id, "value", newValue);
      }}
      conditionOrBlock={(() => {
        // Check if this is an aggregation operator that should be shown on the left
        const isAggregationOnLeft =
          conditionOrBlock.value &&
          typeof conditionOrBlock.value === "object" &&
          conditionOrBlock.value.type === "array" &&
          conditionOrBlock.value.subField &&
          ["$min", "$max", "$avg", "$sum"].includes(conditionOrBlock.operator);

        if (isAggregationOnLeft) {
          return {
            ...conditionOrBlock,
            value: "", // This prevents the aggregation chip from showing on the right
          };
        }

        return conditionOrBlock;
      })()}
      setOpenEquationIds={setOpenEquationIds}
      customVariables={[]}
      setSelectedChip={setSelectedChip}
      side={"right"}
      style={{ width: "100%" }}
      isListDialog={isListDialogOpen}
      customListVariables={customListVariables}
      setEquationAnchor={setEquationAnchor}
    />
  );
};

interface ValueInputProps {
  conditionOrBlock: any;
  block: any;
  updateCondition: (...a: any[]) => void;
  setOpenEquationIds: (...a: any[]) => void;
  setSelectedChip: (...a: any[]) => void;
  setEquationAnchor?: ((...a: any[]) => void) | null;
  createDefaultCondition: (...a: any[]) => any;
  createDefaultBlock: (...a: any[]) => any;
}

const ValueInput = ({
  conditionOrBlock,
  block,
  updateCondition,
  setOpenEquationIds,
  setSelectedChip,
  setEquationAnchor = null,
  createDefaultCondition,
  createDefaultBlock,
}: ValueInputProps) => {
  const schema = useAppSelector((state: any) => state.filter_modules?.schema);
  const fieldOptions = flattenFieldOptions(schema);

  const { customListVariables, customVariables, fieldOptionsList } =
    useConditionContext();

  // Check conditions that don't require context first
  if (shouldSkipValueInput(conditionOrBlock)) {
    return null;
  }

  const isArrayFieldWithArrayOperator = () => {
    const fieldName = normalizeFieldValue(conditionOrBlock.field);
    const fieldVar = customVariables?.find((v: any) => v.name === fieldName);
    const fieldObjList = fieldOptionsList
      ? fieldOptionsList.find((f: any) => f.label === fieldName)
      : null;
    const baseFieldOption = fieldOptions.find(
      (f: any) => f.label === fieldName,
    );

    const isArrayField =
      fieldVar?.type === "array" ||
      fieldObjList?.type === "array" ||
      baseFieldOption?.type === "array";
    const currentOperator = conditionOrBlock.operator;

    // Operators that should show the "+ List Variable" button for array fields
    const arrayOperatorsForButton = [
      "$filter",
      "$min",
      "$max",
      "$avg",
      "$sum",
      "$size",
      "$stdDevPop",
      "$median",
      "$anyElementTrue",
      "$allElementsTrue",
    ];

    return isArrayField && arrayOperatorsForButton.includes(currentOperator);
  };

  // Check if this is an array field with an array operator that should show "+ List Variable" button
  const isArrayWithOperator = isArrayFieldWithArrayOperator();

  const isBooleanField = () => {
    const fieldName = normalizeFieldValue(conditionOrBlock.field);
    const fieldVar = customVariables?.find((v: any) => v.name === fieldName);
    const fieldObjList = fieldOptionsList
      ? fieldOptionsList.find((f: any) => f.label === fieldName)
      : null;
    const baseFieldOption = fieldOptions.find(
      (f: any) => f.label === fieldName,
    );

    return (
      fieldVar?.type === "boolean" ||
      fieldObjList?.type === "boolean" ||
      baseFieldOption?.type === "boolean"
    );
  };

  // Check conditions that require context
  if (isBooleanField()) {
    return null;
  }

  // Skip value input for operators that have special inputs (handled by SpecialOperatorInputs)
  const operatorsWithSpecialInputs = ["$exists", "$isNumber", "$round", "$in"];
  if (operatorsWithSpecialInputs.includes(conditionOrBlock.operator)) {
    return null;
  }

  if (isArrayWithOperator) {
    return (
      <ArrayFieldInput conditionOrBlock={conditionOrBlock} block={block} />
    );
  }

  // Check if this is a list variable
  const fieldName = normalizeFieldValue(conditionOrBlock.field);
  const listVariable = customListVariables.find(
    (lv: any) => lv.name === fieldName,
  );
  if (listVariable) {
    return (
      <ListVariableInput
        listVariable={listVariable}
        conditionOrBlock={conditionOrBlock}
        block={block}
        updateCondition={updateCondition}
        setOpenEquationIds={setOpenEquationIds}
        setSelectedChip={setSelectedChip}
        setEquationAnchor={setEquationAnchor}
      />
    );
  }

  // Check if this is a switch operator
  if (conditionOrBlock.operator === "$switch") {
    return (
      <ConditionalValueInput
        conditionOrBlock={conditionOrBlock}
        block={block}
        updateCondition={updateCondition}
        defaultCondition={createDefaultCondition}
        defaultBlock={createDefaultBlock}
      />
    );
  }

  // Regular value input
  return (
    <RegularValueInput
      conditionOrBlock={conditionOrBlock}
      block={block}
      updateCondition={updateCondition}
      setOpenEquationIds={setOpenEquationIds}
      setSelectedChip={setSelectedChip}
      setEquationAnchor={setEquationAnchor}
    />
  );
};

export default ValueInput;
