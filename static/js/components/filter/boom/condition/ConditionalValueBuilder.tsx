import { useState } from "react";
import {
  Box,
  Typography,
  IconButton,
  Button,
  Paper,
  Popover,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from "@mui/icons-material";
import Latex from "react-latex-next";
import { useAppSelector } from "../../../../types/hooks";
import BlockComponent from "../block/BlockComponent";
import AutocompleteFields from "./AutocompleteFields";
import { useCurrentBuilder } from "../../../../hooks/useContexts";
import { flattenFieldOptions } from "../../../../constants/filterConstants";
import { getFieldOptionsWithVariable } from "../../../../utils/conditionHelpers";

// Helper function to escape LaTeX special characters for display
const escapeLatexForDisplay = (text: any) => {
  if (!text) return text;
  // Escape underscores to prevent subscript rendering
  // Replace _ with \_ to show it as literal underscore
  return text.replace(/_/g, "\\_");
};

/**
 * ConditionalValueBuilder - Builds a $switch expression using CASE/WHEN/THEN/DEFAULT logic
 * Each case contains a full block that can have conditions and nested blocks
 *
 * Example output structure:
 * {
 *   cases: [
 *     {
 *       block: {
 *         id: "...",
 *         category: "block",
 *         operator: "$and",
 *         children: [...]
 *       },
 *       then: "High"
 *     }
 *   ],
 *   default: "Med"
 * }
 */
interface ConditionalValueBuilderProps {
  value?: any;
  onChange?: (...a: any[]) => void;
  defaultCondition: (...a: any[]) => any;
  defaultBlock: (...a: any[]) => any;
  fieldOptionsList?: any[] | undefined;
}

const ConditionalValueBuilder = ({
  value,
  onChange,
  defaultCondition,
  defaultBlock,
  fieldOptionsList = [],
}: ConditionalValueBuilderProps) => {
  // Get schema from Redux and flatten to field options
  const schema = useAppSelector((state: any) => state.filter_modules?.schema);
  const currentStream = useAppSelector(
    (state: any) => state.boom_filter_v.stream?.name,
  );
  const final_schema = schema?.versions?.find(
    (v: any) => v.vid === schema.active_id,
  )?.schema;
  const schemaFieldOptions = flattenFieldOptions(final_schema) || [];

  // Get builder context to access all necessary data
  const {
    customVariables,
    customListVariables,
    customSwitchCases,
    fieldOptionsList: contextFieldOptionsList,
  } = useCurrentBuilder();

  // Combine: use passed fieldOptionsList, or contextFieldOptionsList, or schema fields
  // The main builder passes schema fields through contextFieldOptionsList, but if that's empty,
  // we get them directly from Redux
  const baseFieldOptions =
    fieldOptionsList.length > 0
      ? fieldOptionsList
      : contextFieldOptionsList && contextFieldOptionsList.length > 0
        ? contextFieldOptionsList
        : schemaFieldOptions;

  const effectiveFieldOptionsList = baseFieldOptions;

  // Combine all field options including variables for THEN value autocomplete
  const allFieldOptions = getFieldOptionsWithVariable(
    effectiveFieldOptionsList,
    customVariables,
    customListVariables,
    customSwitchCases || [],
    [],
    null,
    currentStream,
  );

  // Helper to create a default empty block
  const createDefaultCaseBlock = () => ({
    ...defaultBlock(),
    operator: "$and",
  });

  // Parse existing value or initialize empty
  const normalizeData = (data: any) => {
    if (!data || !data.cases || data.cases.length === 0) {
      return {
        cases: [
          {
            block: createDefaultCaseBlock(),
            then: "",
          },
        ],
        default: "",
      };
    }

    const normalizedCases = data.cases.map((caseItem: any) => {
      // If old format with conditions array, convert to block format
      if (caseItem.conditions) {
        const block = createDefaultCaseBlock();
        block.operator = caseItem.logicalOperator || "$and";
        block.children = caseItem.conditions.map((cond: any) => {
          if (cond === null) {
            return defaultCondition();
          }
          return {
            ...defaultCondition(),
            ...cond,
          };
        });
        return {
          block,
          then: caseItem.then || "",
        };
      }

      // Already new format or needs initialization
      if (!caseItem.block) {
        return {
          block: createDefaultCaseBlock(),
          then: caseItem.then || "",
        };
      }

      return caseItem;
    });

    return {
      cases: normalizedCases,
      default: data.default || "",
    };
  };

  const [switchData, setSwitchData] = useState<any>(normalizeData(value));
  const [collapsedCases, setCollapsedCases] = useState<any>(new Set());
  const [openEquationIds, setOpenEquationIds] = useState<any>([]);
  const [, setSelectedChip] = useState("");
  const [equationAnchor, setEquationAnchor] = useState<any>(null);

  const handleBlockChange = (caseIndex: any, newBlock: any) => {
    // Safety check: ensure newBlock is valid
    if (!newBlock) {
      console.warn(
        "ConditionalValueBuilder: newBlock is undefined, skipping update",
      );
      return;
    }

    const updated = { ...switchData };
    updated.cases[caseIndex].block = newBlock;
    setSwitchData(updated);
    if (onChange) onChange(updated);
  };

  const handleCaseThenChange = (caseIndex: any, thenValue: any) => {
    const updated = { ...switchData };
    updated.cases[caseIndex].then = thenValue;
    setSwitchData(updated);
    if (onChange) onChange(updated);
  };

  const handleDefaultChange = (defaultValue: any) => {
    const updated = { ...switchData, default: defaultValue };
    setSwitchData(updated);
    if (onChange) onChange(updated);
  };

  const toggleCaseCollapse = (caseIndex: any) => {
    setCollapsedCases((prev: any) => {
      const newSet = new Set(prev);
      if (newSet.has(caseIndex)) {
        newSet.delete(caseIndex);
      } else {
        newSet.add(caseIndex);
      }
      return newSet;
    });
  };

  const addCase = () => {
    const updated = { ...switchData };
    updated.cases.push({
      block: createDefaultCaseBlock(),
      then: "",
    });
    setSwitchData(updated);
    if (onChange) onChange(updated);
  };

  const removeCase = (caseIndex: any) => {
    if (switchData.cases.length <= 1) return; // Keep at least one case
    const updated = { ...switchData };
    updated.cases.splice(caseIndex, 1);
    setSwitchData(updated);
    if (onChange) onChange(updated);
  };

  return (
    <Paper
      elevation={1}
      sx={{
        ml: 0,
        mt: 0,
        p: 2,
        backgroundColor: "transparent",
        borderLeft: "4px solid #212121",
        borderRadius: 1,
        width: "100%",
        border: "1px solid",
        borderColor: "divider",
        transition: "all 0.2s ease",
        "&:hover": {
          backgroundColor: "rgba(0, 0, 0, 0.04)",
          borderColor: "grey.700",
          borderLeftColor: "#000000",
          boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
        },
      }}
    >
      {/* CASE rows */}
      {switchData.cases.map((caseItem: any, caseIndex: number) => {
        // Safety check: ensure block exists
        if (!caseItem.block) {
          console.warn(
            `ConditionalValueBuilder: Case ${caseIndex} has no block, initializing`,
          );
          caseItem.block = createDefaultCaseBlock();
        }

        return (
          <Paper
            key={caseIndex}
            sx={{ p: 2, mb: 2, border: 1, borderColor: "divider" }}
            elevation={1}
          >
            {/* Case Header */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                mb: 1,
                py: 0.5,
                borderBottom: 1,
                borderColor: "divider",
              }}
            >
              {/* Collapse/Expand Icon */}
              <IconButton
                size="small"
                onClick={() => toggleCaseCollapse(caseIndex)}
                sx={{ mr: 1 }}
              >
                {collapsedCases.has(caseIndex) ? (
                  <ExpandMoreIcon fontSize="small" />
                ) : (
                  <ExpandLessIcon fontSize="small" />
                )}
              </IconButton>

              <Typography
                variant="subtitle2"
                sx={{
                  fontWeight: "bold",
                  color: "#424242",
                  minWidth: 80,
                }}
              >
                CASE {caseIndex + 1}
              </Typography>

              <Box sx={{ flex: 1 }} />

              {/* Delete Case Button (only show if more than 1 case) */}
              {switchData.cases.length > 1 && (
                <IconButton
                  size="small"
                  onClick={() => removeCase(caseIndex)}
                  sx={{ color: "#d32f2f" }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              )}
            </Box>

            {/* Embedded Block Component - only show when not collapsed */}
            {!collapsedCases.has(caseIndex) && (
              <>
                <Box sx={{ ml: 2 }}>
                  {caseItem.block && (
                    <BlockComponent
                      block={caseItem.block}
                      parentBlockId={null}
                      isRoot={true}
                      fieldOptionsList={effectiveFieldOptionsList}
                      localFilters={[caseItem.block]}
                      setLocalFilters={(updatedFiltersOrUpdater: any) => {
                        // Handle both direct value and updater function
                        let updatedFilters;
                        if (typeof updatedFiltersOrUpdater === "function") {
                          // It's an updater function - call it with current block
                          updatedFilters = updatedFiltersOrUpdater([
                            caseItem.block,
                          ]);
                        } else {
                          updatedFilters = updatedFiltersOrUpdater;
                        }

                        // The updated block should be the first (and only) item in the array
                        if (
                          updatedFilters &&
                          Array.isArray(updatedFilters) &&
                          updatedFilters.length > 0
                        ) {
                          handleBlockChange(caseIndex, updatedFilters[0]);
                        }
                      }}
                      disableSwitchOption={true}
                    />
                  )}
                </Box>

                {/* THEN Value */}
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    ml: 2,
                    mt: 2,
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      color: "#555",
                    }}
                  >
                    THEN:
                  </Typography>
                  <AutocompleteFields
                    fieldOptions={allFieldOptions}
                    value={caseItem.then || ""}
                    onChange={(newValue: any) =>
                      handleCaseThenChange(caseIndex, newValue)
                    }
                    conditionOrBlock={{ id: `switch-case-${caseIndex}-then` }}
                    side="right"
                    {...({
                      customVariables: customVariables || [],
                      customListVariables: customListVariables || [],
                    } as any)}
                    setOpenEquationIds={setOpenEquationIds}
                    setSelectedChip={setSelectedChip}
                    setEquationAnchor={setEquationAnchor}
                  />
                </Box>
              </>
            )}
          </Paper>
        );
      })}

      {/* Add Case Button */}
      <Button
        size="small"
        startIcon={<AddIcon />}
        onClick={addCase}
        sx={{
          mb: 2,
          textTransform: "none",
          color: "#1976d2",
        }}
      >
        Add Case
      </Button>

      {/* DEFAULT */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          pt: 2,
          borderTop: "2px solid #ddd",
        }}
      >
        <Typography
          variant="body2"
          sx={{
            fontWeight: 600,
            color: "#1976d2",
          }}
        >
          DEFAULT (If no match)
        </Typography>
        <Box sx={{ flex: 1 }} />
        <Typography
          variant="body2"
          sx={{
            fontWeight: 600,
            color: "#555",
          }}
        >
          THEN:
        </Typography>
        <AutocompleteFields
          fieldOptions={allFieldOptions}
          value={switchData.default || ""}
          onChange={(newValue: any) => handleDefaultChange(newValue)}
          conditionOrBlock={{ id: "switch-default-then" }}
          side="right"
          {...({
            customVariables: customVariables || [],
            customListVariables: customListVariables || [],
          } as any)}
          setOpenEquationIds={setOpenEquationIds}
          setSelectedChip={setSelectedChip}
          setEquationAnchor={setEquationAnchor}
        />
      </Box>

      {/* Equation Popover for arithmetic variables */}
      {equationAnchor && openEquationIds.length > 0 && (
        <Popover
          open={!!equationAnchor}
          anchorEl={equationAnchor}
          onClose={() => {
            setOpenEquationIds([]);
            setEquationAnchor(null);
          }}
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
            {(() => {
              // Find the equation for the selected variable
              // The openEquationIds contains the condition ID like "switch-case-0-then"
              // We need to extract which case and get its THEN value
              const conditionId = openEquationIds[0];
              let variableName: any = null;

              if (conditionId === "switch-default-then") {
                variableName = switchData.default;
              } else {
                // Extract case index from ID like "switch-case-0-then"
                const match = conditionId?.match(/switch-case-(\d+)-then/);
                if (match) {
                  const caseIndex = parseInt(match[1], 10);
                  variableName = switchData.cases[caseIndex]?.then;
                }
              }

              const variableOption = allFieldOptions.find(
                (opt: any) => opt.label === variableName && opt.isVariable,
              );

              if (variableOption) {
                const eqObj = customVariables?.find(
                  (eq: any) => eq.name === variableOption.label,
                );
                const equation = eqObj
                  ? eqObj.variable
                  : variableOption.equation;
                if (equation) {
                  const displayEquation = escapeLatexForDisplay(equation);
                  return <Latex>{`$$${displayEquation}$$`}</Latex>;
                }
              }
              return <Typography>No equation found</Typography>;
            })()}
          </Paper>
        </Popover>
      )}
    </Paper>
  );
};

export default ConditionalValueBuilder;
