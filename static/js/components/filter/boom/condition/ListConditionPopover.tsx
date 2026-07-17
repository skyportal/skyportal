import { useRef, useEffect, useState } from "react";
import {
  Popover,
  IconButton,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  Box,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import CancelIcon from "@mui/icons-material/Cancel";
import BlockComponent from "../block/BlockComponent";
import { useCurrentBuilder } from "../../../../hooks/useContexts";
import { usePutFilterElementMutation } from "../../../../ducks/boom_filter_modules";
import { normalizeFieldValue } from "../../../../utils/conditionHelpers";

const OPERATOR_LABELS: Record<string, any> = {
  $anyElementTrue: "Any Element True",
  $allElementsTrue: "All Elements True",
  $filter: "Filter",
  $map: "Map",
  $min: "Minimum",
  $max: "Maximum",
  $avg: "Average",
  $sum: "Sum",
  $size: "Count Elements",
  $stdDevPop: "Standard Deviation (Population)",
  $median: "Median",
  $all: "All",
};

const getOperatorLabel = (operator: any) =>
  OPERATOR_LABELS[operator] || operator;

const getOperatorOutputType = (operator: any) => {
  if (["$anyElementTrue", "$allElementsTrue"].includes(operator))
    return "boolean";
  if (["$filter", "$map"].includes(operator)) return "array";
  if (
    ["$min", "$max", "$avg", "$sum", "$size", "$stdDevPop", "$median"].includes(
      operator,
    )
  )
    return "number";
  return null;
};

const getCompatibleOperators = (operator: any) => {
  if (operator === "$map") return ["$map"];
  const outputType = getOperatorOutputType(operator);
  if (outputType === "boolean") return ["$anyElementTrue", "$allElementsTrue"];
  if (outputType === "array") return ["$filter"];
  if (outputType === "number")
    return ["$min", "$max", "$avg", "$sum", "$size", "$stdDevPop", "$median"];
  return [operator];
};

interface ListConditionPopoverProps {
  listPopoverAnchor?: any;
  setListPopoverAnchor: (...a: any[]) => void;
  conditionOrBlock: any;
  customListVariables?: any[];
  createDefaultCondition: (...a: any[]) => any;
  customVariables?: any[];
  block: any;
  updateCondition: (...a: any[]) => void;
  fieldOptions?: any[];
  fieldOptionsList?: any[];
}

const ListConditionPopover = ({
  listPopoverAnchor,
  setListPopoverAnchor,
  conditionOrBlock,
  customListVariables,
  createDefaultCondition, // Fixed: use createDefaultCondition
  customVariables,
  block,
  updateCondition,
  fieldOptions,
  fieldOptionsList,
}: ListConditionPopoverProps) => {
  const popoverRef = useRef<any>(null);
  const isOpen = Boolean(listPopoverAnchor);
  const [editMode, setEditMode] = useState(false);
  const [editedConditions, setEditedConditions] = useState<any>(null);
  const [editingOperator, setEditingOperator] = useState(false);
  const [editedOperator, setEditedOperator] = useState<any>(null);
  const { setCustomListVariables } = useCurrentBuilder();
  const [putElement] = usePutFilterElementMutation();

  // Handle focus management when popover opens/closes
  useEffect(() => {
    if (isOpen && popoverRef.current) {
      // Set focus to the popover container when it opens
      const timer = setTimeout(() => {
        if (popoverRef.current) {
          popoverRef.current.focus();
        }
      }, 100);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [isOpen]);

  const handleClose = () => {
    const anchorElement = listPopoverAnchor;
    setListPopoverAnchor(null);
    (window as any).currentListVariable = null; // Clear temporary data
    setEditMode(false); // Reset edit mode
    setEditedConditions(null); // Clear edited conditions
    setEditingOperator(false); // Reset operator editing
    setEditedOperator(null); // Clear edited operator

    // Ensure focus is properly managed when closing
    if (anchorElement) {
      // Small delay to ensure the popover has closed before returning focus
      setTimeout(() => {
        if (anchorElement && typeof anchorElement.focus === "function") {
          try {
            anchorElement.focus();
          } catch {
            // Fallback - focus on the document body if anchor focus fails
            document.body.focus();
          }
        }
      }, 100);
    }
  };

  const handleSaveEdit = async (listVar: any) => {
    if ((editedConditions || editedOperator) && setCustomListVariables) {
      const updatedListCondition = {
        ...listVar.listCondition,
        ...(editedConditions && { value: editedConditions }),
        ...(editedOperator && { operator: editedOperator }),
      };

      try {
        // Update in the database using Redux action
        await putElement({
          name: listVar.name,
          data: {
            listCondition: updatedListCondition,
            type: listVar.type || "array",
          },
          elements: "listVariables",
        });

        // Update in the context (local state) - this will trigger a re-render
        setCustomListVariables((prev: any) => {
          return prev.map((lv: any) => {
            if (lv.name === listVar.name) {
              return {
                ...lv,
                listCondition: updatedListCondition,
              };
            }
            return lv;
          });
        });

        // Exit edit mode
        setEditMode(false);
        setEditedConditions(null);
        setEditingOperator(false);
        setEditedOperator(null);
      } catch (error) {
        console.error("Failed to save list variable:", error);
        alert("Failed to save changes to the database. Please try again.");
      }
    }
  };

  const handleCancelEdit = () => {
    setEditMode(false);
    setEditedConditions(null);
    setEditingOperator(false);
    setEditedOperator(null);
  };

  const handleStartEdit = (listVar: any) => {
    setEditMode(true);
    // Deep clone to ensure we have an independent copy for editing
    const clonedValue = JSON.parse(JSON.stringify(listVar.listCondition.value));
    setEditedConditions(clonedValue);
  };

  const renderPopoverContent = () => {
    // Priority 1: Check if this is a list variable popover (from global callback)
    let listVar = (window as any).currentListVariable;
    if (listVar) {
      // Always get the fresh data from customListVariables if available
      const freshListVar = customListVariables?.find(
        (lv: any) => lv.name === listVar.name,
      );
      return renderListVariableContent(freshListVar || listVar);
    }

    // if (!conditionOrBlock) {
    //   return null;
    // }

    // Priority 2: Check for aggregation operator popover (newly created with subField)
    if (
      conditionOrBlock.value &&
      typeof conditionOrBlock.value === "object" &&
      conditionOrBlock.value.type === "array" &&
      conditionOrBlock.value.subField
    ) {
      return renderAggregationDisplay(conditionOrBlock);
    }
    // Priority 2.5: Check for direct aggregation operator with subField in conditionOrBlock
    if (
      conditionOrBlock.operator &&
      [
        "$min",
        "$max",
        "$avg",
        "$sum",
        "$size",
        "$stdDevPop",
        "$median",
      ].includes(conditionOrBlock.operator)
    ) {
      return renderAggregationDisplay(conditionOrBlock);
    }

    // Priority 3: Check for reused list variable (from AutocompleteFields chip click)
    if (conditionOrBlock.isListVariable && conditionOrBlock.field) {
      const reusedListVar = customListVariables?.find(
        (lv: any) => lv.name === conditionOrBlock.field,
      );
      if (reusedListVar) {
        return renderListVariableContent(reusedListVar);
      }
    }

    // Priority 4: Regular list condition popover (for newly created conditions with value but no subField)
    if (
      conditionOrBlock.value &&
      typeof conditionOrBlock.value === "object" &&
      conditionOrBlock.value.type === "array" &&
      !conditionOrBlock.value.subField
    ) {
      return renderRegularListCondition(
        conditionOrBlock,
        block,
        updateCondition,
        createDefaultCondition,
        customVariables,
        customListVariables,
      );
    }

    return null;
  };

  const renderListVariableContent = (listVar: any) => {
    // Determine if this list variable can be edited (has conditions to edit)
    const canEdit =
      listVar.listCondition.value &&
      typeof listVar.listCondition.value === "object" &&
      ![
        "$min",
        "$max",
        "$avg",
        "$sum",
        "$size",
        "$stdDevPop",
        "$median",
        "$map",
      ].includes(listVar.listCondition.operator);

    return (
      <div
        style={{
          width: "90vw",
          maxWidth: 900,
          minWidth: 400,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 8,
          }}
        >
          <div
            style={{
              fontWeight: 600,
              color: "#166534",
              fontSize: 17,
              letterSpacing: 0.2,
            }}
          >
            <span style={{ color: "#059669" }}>{listVar.name}</span>
            <span style={{ fontSize: 14, color: "#6b7280", marginLeft: 8 }}>
              ({normalizeFieldValue(listVar.listCondition.field)})
            </span>
          </div>

          {canEdit && (
            <div style={{ display: "flex", gap: 8 }}>
              {!editMode ? (
                <Tooltip title="Edit list condition">
                  <IconButton
                    size="small"
                    onClick={() => handleStartEdit(listVar)}
                    style={{
                      backgroundColor: "#e0f2fe",
                      color: "#0369a1",
                      padding: 6,
                    }}
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              ) : (
                <>
                  <Tooltip title="Save changes">
                    <IconButton
                      size="small"
                      onClick={() => handleSaveEdit(listVar)}
                      style={{
                        backgroundColor: "#dcfce7",
                        color: "#166534",
                        padding: 6,
                      }}
                    >
                      <SaveIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Cancel editing">
                    <IconButton
                      size="small"
                      onClick={handleCancelEdit}
                      style={{
                        backgroundColor: "#fee2e2",
                        color: "#991b1b",
                        padding: 6,
                      }}
                    >
                      <CancelIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </>
              )}
            </div>
          )}
        </div>

        {/* Display the list operator */}
        {listVar.listCondition.operator && (
          <div
            style={{
              padding: "8px 12px",
              backgroundColor: "#f0f9ff",
              borderRadius: 6,
              fontSize: 14,
              color: "#0369a1",
              border: "1px solid #bae6fd",
              fontWeight: 500,
              marginBottom: 4,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            {!editingOperator ? (
              <>
                <div style={{ flex: 1 }}>
                  <span style={{ fontWeight: 600 }}>Operator:</span>{" "}
                  {getOperatorLabel(listVar.listCondition.operator)}
                </div>
                {getOperatorOutputType(listVar.listCondition.operator) && (
                  <div
                    style={{
                      padding: "4px 10px",
                      backgroundColor: "#dbeafe",
                      borderRadius: 4,
                      fontSize: 12,
                      color: "#1e40af",
                      fontWeight: 600,
                      border: "1px solid #93c5fd",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                    }}
                  >
                    → {getOperatorOutputType(listVar.listCondition.operator)}
                  </div>
                )}
                {listVar.listCondition.operator !== "$map" && (
                  <Tooltip title="Edit operator">
                    <IconButton
                      size="small"
                      onClick={() => {
                        setEditingOperator(true);
                        setEditedOperator(listVar.listCondition.operator);
                      }}
                      style={{
                        backgroundColor: "#e0f2fe",
                        color: "#0369a1",
                        padding: 4,
                      }}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
              </>
            ) : (
              <>
                <div style={{ flex: 1 }}>
                  <span style={{ fontWeight: 600 }}>Operator:</span>
                  <FormControl
                    size="small"
                    style={{ marginLeft: 8, minWidth: 200 }}
                  >
                    <Select
                      value={editedOperator}
                      onChange={(e: any) => setEditedOperator(e.target.value)}
                      style={{
                        fontSize: 14,
                        backgroundColor: "white",
                      }}
                    >
                      {getCompatibleOperators(
                        listVar.listCondition.operator,
                      ).map((op: any) => (
                        <MenuItem key={op} value={op}>
                          {getOperatorLabel(op)}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </div>
                <Tooltip title="Save operator change">
                  <IconButton
                    size="small"
                    onClick={() => handleSaveEdit(listVar)}
                    style={{
                      backgroundColor: "#dcfce7",
                      color: "#166534",
                      padding: 4,
                    }}
                  >
                    <SaveIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Cancel">
                  <IconButton
                    size="small"
                    onClick={() => {
                      setEditingOperator(false);
                      setEditedOperator(null);
                    }}
                    style={{
                      backgroundColor: "#fee2e2",
                      color: "#991b1b",
                      padding: 4,
                    }}
                  >
                    <CancelIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </>
            )}
          </div>
        )}

        <div style={{ width: "100%" }}>
          {listVar.listCondition.operator === "$map" &&
          listVar.listCondition.value ? (
            // For $map operator, display the map configuration in a user-friendly way
            <Box
              sx={{
                p: 2,
                bgcolor: "background.paper",
                border: "1px solid",
                borderColor: "grey.300",
                borderRadius: 1,
              }}
            >
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: 600, mb: 2, color: "primary.main" }}
              >
                Map Expression
              </Typography>

              {(() => {
                const mapData = listVar.listCondition.value;
                const mapExpression = mapData.mapExpression || {};
                const fields = Object.entries(mapExpression);

                return (
                  <>
                    <Box sx={{ mb: 2 }}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: "block", mb: 0.5 }}
                      >
                        For each element in{" "}
                        <strong>
                          {normalizeFieldValue(listVar.listCondition.field)}
                        </strong>
                        , create:
                      </Typography>
                    </Box>

                    {fields.map(
                      ([fieldName, expression]: any, index: number) => {
                        // Try to find the arithmetic variable details
                        const arithmeticVar = customVariables?.find(
                          (v: any) => v.name === expression,
                        );

                        return (
                          <Box
                            key={fieldName}
                            sx={{
                              p: 1.5,
                              mb: index < fields.length - 1 ? 2 : 0,
                              bgcolor: "grey.50",
                              borderRadius: 1,
                              border: "1px solid",
                              borderColor: "grey.200",
                            }}
                          >
                            <Box
                              sx={{
                                display: "flex",
                                alignItems: "baseline",
                                mb: 1,
                              }}
                            >
                              <Typography
                                variant="body2"
                                sx={{ fontWeight: 600, mr: 1 }}
                              >
                                Field:
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{
                                  fontFamily: "monospace",
                                  color: "success.main",
                                }}
                              >
                                {fieldName}
                              </Typography>
                            </Box>

                            <Box
                              sx={{ display: "flex", alignItems: "baseline" }}
                            >
                              <Typography
                                variant="body2"
                                sx={{ fontWeight: 600, mr: 1 }}
                              >
                                Expression:
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{
                                  fontFamily: "monospace",
                                  color: "info.main",
                                }}
                              >
                                {expression}
                              </Typography>
                            </Box>

                            {arithmeticVar && (
                              <Box
                                sx={{
                                  mt: 2,
                                  pt: 2,
                                  borderTop: "1px solid",
                                  borderColor: "grey.300",
                                }}
                              >
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{ display: "block", mb: 0.5 }}
                                >
                                  Formula:
                                </Typography>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    fontFamily: "monospace",
                                    fontSize: "0.85rem",
                                  }}
                                >
                                  {arithmeticVar.variable}
                                </Typography>
                              </Box>
                            )}
                          </Box>
                        );
                      },
                    )}

                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mt: 2, fontStyle: "italic" }}
                    >
                      This transforms each array element by computing{" "}
                      {fields.length} field{fields.length > 1 ? "s" : ""}.
                    </Typography>
                  </>
                );
              })()}
            </Box>
          ) : listVar.listCondition.value ? (
            <BlockComponent
              block={
                editMode
                  ? editedConditions || listVar.listCondition.value
                  : listVar.listCondition.value
              }
              parentBlockId={null}
              isRoot={true}
              fieldOptionsList={(() => {
                // Combine subFieldOptions with full field options for comprehensive coverage
                const subFieldOpts =
                  listVar.listCondition.subFieldOptions || [];
                const fullFieldOpts = fieldOptionsList || fieldOptions || [];
                // If we have subFieldOptions, combine them with full options, otherwise just use full options
                return subFieldOpts.length > 0
                  ? [...fullFieldOpts, ...subFieldOpts]
                  : fullFieldOpts;
              })()}
              isListDialogOpen={false}
              localFilters={
                editMode
                  ? [editedConditions || listVar.listCondition.value]
                  : null
              }
              setLocalFilters={
                editMode
                  ? (newFiltersOrUpdater: any) => {
                      // Handle both direct values and updater functions
                      let newFilters;
                      if (typeof newFiltersOrUpdater === "function") {
                        // If it's an updater function, call it with current localFilters
                        const currentFilters = [
                          editedConditions || listVar.listCondition.value,
                        ];
                        newFilters = newFiltersOrUpdater(currentFilters);
                      } else {
                        // If it's a direct value, use it as-is
                        newFilters = newFiltersOrUpdater;
                      }

                      // Update via setLocalFilters for full editing support
                      // Use JSON deep clone to ensure nested structures are preserved
                      if (
                        newFilters &&
                        newFilters.length > 0 &&
                        newFilters[0]?.id
                      ) {
                        try {
                          const clonedBlock = JSON.parse(
                            JSON.stringify(newFilters[0]),
                          );
                          setEditedConditions(clonedBlock);
                        } catch (error) {
                          console.error("Failed to clone block:", error);
                          setEditedConditions(newFilters[0]);
                        }
                      }
                    }
                  : null
              }
            />
          ) : listVar.listCondition.subField ||
            (listVar.listCondition.operator &&
              [
                "$min",
                "$max",
                "$avg",
                "$sum",
                "$size",
                "$stdDevPop",
                "$median",
              ].includes(listVar.listCondition.operator)) ? (
            renderAggregationDisplay(listVar.listCondition)
          ) : (
            <div
              style={{ fontSize: 14, color: "#6b7280", fontStyle: "italic" }}
            >
              This list condition does not have sub-conditions to display.
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderAggregationDisplay = (listCondition: any) => {
    // Handle different possible data structures
    const operator = listCondition.operator || "";
    const arrayField =
      listCondition.field ||
      (listCondition.value && listCondition.value.field) ||
      "";
    const subField =
      listCondition.subField ||
      (listCondition.value && listCondition.value.subField) ||
      "";

    // $size doesn't require a subField
    if (!operator || !arrayField) {
      return (
        <div style={{ fontSize: 14, color: "#6b7280", fontStyle: "italic" }}>
          Incomplete aggregation information available.
        </div>
      );
    }

    // For $size operator, display without subField
    if (operator === "$size") {
      return (
        <div>
          <div
            style={{
              padding: "12px 16px",
              backgroundColor: "#f0fdf4",
              borderRadius: 8,
              fontSize: 16,
              color: "#166534",
              border: "1px solid #bbf7d0",
              fontWeight: 600,
              fontFamily: "monospace",
              marginBottom: 12,
            }}
          >
            COUNT({arrayField})
          </div>
          <div style={{ fontSize: 14, color: "#6b7280" }}>
            This aggregation operation counts the number of elements in the
            &quot;
            {arrayField}&quot; array.
          </div>
        </div>
      );
    }

    // Other operators require subField
    if (!subField) {
      return (
        <div style={{ fontSize: 14, color: "#6b7280", fontStyle: "italic" }}>
          Incomplete aggregation information available.
        </div>
      );
    }

    return (
      <div>
        <div
          style={{
            padding: "12px 16px",
            backgroundColor: "#f0fdf4",
            borderRadius: 8,
            fontSize: 16,
            color: "#166534",
            border: "1px solid #bbf7d0",
            fontWeight: 600,
            fontFamily: "monospace",
            marginBottom: 12,
          }}
        >
          {operator.replace("$", "").toUpperCase()}({arrayField}.{subField})
        </div>
        <div style={{ fontSize: 14, color: "#6b7280" }}>
          This aggregation operation calculates the{" "}
          {operator.replace("$", "").toLowerCase()} value of the &quot;
          {subField}&quot; field across all elements in the &quot;{arrayField}
          &quot; array.
        </div>
      </div>
    );
  };

  const renderRegularListCondition = (
    conditionBlock: any,
    parentBlock: any,
    updateConditionFunc: any,
    _createDefaultConditionFunc: any,
    _variables: any,
    _listVariables: any,
  ) => {
    return (
      <div
        style={{
          width: "90vw",
          maxWidth: 900,
          minWidth: 400,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div
          style={{
            fontWeight: 600,
            color: "#166534",
            fontSize: 17,
            marginBottom: 8,
            letterSpacing: 0.2,
          }}
        >
          {conditionBlock.value.name ? (
            <>
              <span style={{ color: "#059669" }}>
                {conditionBlock.value.name}
              </span>
              <span style={{ fontSize: 14, color: "#6b7280", marginLeft: 8 }}>
                ({normalizeFieldValue(conditionBlock.value.field)})
              </span>
            </>
          ) : (
            <>
              List Condition:{" "}
              <span style={{ color: "#059669" }}>
                {normalizeFieldValue(conditionBlock.value.field)}
              </span>
            </>
          )}
        </div>

        {/* Display the list operator */}
        {conditionBlock.value.operator && (
          <div
            style={{
              padding: "8px 12px",
              backgroundColor: "#f0f9ff",
              borderRadius: 6,
              fontSize: 14,
              color: "#0369a1",
              border: "1px solid #bae6fd",
              fontWeight: 500,
              marginBottom: 4,
            }}
          >
            <span style={{ fontWeight: 600 }}>Operator:</span>{" "}
            {getOperatorLabel(conditionBlock.value.operator)}
          </div>
        )}
        <div style={{ width: "100%" }}>
          {conditionBlock.value.value ? (
            <BlockComponent
              block={conditionBlock.value.value}
              parentBlockId={null}
              isRoot={true}
              fieldOptionsList={(() => {
                // Combine subFieldOptions with full field options for comprehensive coverage
                const subFieldOpts = conditionBlock.value.subFieldOptions || [];
                const fullFieldOpts = fieldOptionsList || fieldOptions || [];
                // If we have subFieldOptions, combine them with full options, otherwise just use full options
                return subFieldOpts.length > 0
                  ? [...fullFieldOpts, ...subFieldOpts]
                  : fullFieldOpts;
              })()}
              localFilters={[conditionBlock.value.value]}
              setLocalFilters={(newFilters: any) => {
                // Update the list condition value in the main filters
                const updatedListValue = {
                  ...conditionBlock.value,
                  value: newFilters[0],
                };
                updateConditionFunc(
                  parentBlock.id,
                  conditionBlock.id,
                  "value",
                  updatedListValue,
                );
              }}
            />
          ) : (
            <div
              style={{ fontSize: 14, color: "#6b7280", fontStyle: "italic" }}
            >
              This list condition does not have sub-conditions to display.
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <Popover
      open={Boolean(listPopoverAnchor)}
      anchorEl={listPopoverAnchor}
      onClose={handleClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
      transformOrigin={{ vertical: "top", horizontal: "left" }}
      disableEnforceFocus={false}
      disableAutoFocus={true}
      disableRestoreFocus={true}
      disablePortal={false}
      keepMounted={false}
      hideBackdrop={false}
      slotProps={{
        root: {
          // Prevent aria-hidden on the root when focus is inside
          "aria-hidden": false,
        } as any,
        paper: {
          style: {
            minWidth: 500,
            maxWidth: 1000,
            width: "80vw",
            padding: 18,
            borderRadius: 16,
            boxShadow: "0 8px 32px 0 rgba(16,185,129,0.13)",
            background: "linear-gradient(90deg, #f0fdf4 60%, #d1fae5 100%)",
            overflowY: "auto",
            overflowX: "hidden",
            maxHeight: "80vh",
          },
          role: "dialog",
          "aria-modal": "true",
          "aria-labelledby": "list-condition-popover-title",
          // Prevent aria-hidden on the paper when focus is inside
          "aria-hidden": false,
        } as any,
      }}
    >
      <div
        ref={popoverRef}
        id="list-condition-popover-title"
        style={{ position: "absolute", left: "-10000px" }}
        tabIndex={-1}
      >
        List Condition Details
      </div>
      <div tabIndex={0} style={{ outline: "none" }}>
        {renderPopoverContent()}
      </div>
    </Popover>
  );
};

export default ListConditionPopover;
