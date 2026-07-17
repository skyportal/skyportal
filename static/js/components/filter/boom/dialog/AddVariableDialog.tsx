import { useState, useRef, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Paper,
  IconButton,
  Alert,
} from "@mui/material";
import { Close as CloseIcon, ContentCopy } from "@mui/icons-material";
import { v4 as uuidv4 } from "uuid";
import { useCurrentBuilder } from "../../../../hooks/useContexts";
import { postElement } from "../../../../ducks/boom_filter_modules";
import { useAppDispatch, useAppSelector } from "../../../../types/hooks";
import EquationEditor from "equation-editor-react";

// Numeric types
const numericTypes = ["double", "float", "int", "long"];
const excludedTypes = ["boolean", "array"];

// Helper function to find matching parentheses
const findMatchingParen = (str: string, startIdx: number) => {
  let count = 1;
  for (let i = startIdx + 1; i < str.length; i++) {
    if (str[i] === "(") count++;
    if (str[i] === ")") count--;
    if (count === 0) return i;
  }
  return -1;
};

// Helper function to extract operand (handles parentheses, variables, numbers)
const extractOperand = (str: string, fromEnd = false): string => {
  if (fromEnd) {
    // Extract from end - look for the last complete operand
    const trimmed = str.trim();
    if (trimmed.endsWith(")")) {
      // Find matching opening parenthesis
      let count = 1;
      for (let i = trimmed.length - 2; i >= 0; i--) {
        if (trimmed[i] === ")") count++;
        if (trimmed[i] === "(") count--;
        if (count === 0) {
          return trimmed.substring(i);
        }
      }
    }
    // Extract last number, variable, or function call
    const match = trimmed.match(
      /([a-zA-Z_][a-zA-Z0-9_.]*(?:\([^)]*\))?|\d+(?:\.\d+)?)$/,
    );
    return match ? match[0] : trimmed;
  } else {
    // Extract from start - look for the first complete operand
    const trimmed = str.trim();
    if (trimmed.startsWith("(")) {
      const endIdx = findMatchingParen(trimmed, 0);
      if (endIdx !== -1) {
        return trimmed.substring(0, endIdx + 1);
      }
    }
    // Extract first number, variable, or function call
    const match = trimmed.match(
      /^([a-zA-Z_][a-zA-Z0-9_.]*(?:\([^)]*\))?|\d+(?:\.\d+)?)/,
    );
    return match ? match[0] : trimmed;
  }
};

// Convert division notation to fraction format for better display
// This function handles complex expressions including parentheses
const convertDivisionToFraction = (str: string): string => {
  // Process divisions from left to right, being careful about operator precedence
  let result = str;
  let changed = true;

  while (changed) {
    changed = false;
    // Find division operators that are not already inside \frac
    const divisionMatch = result.match(/(.*?)([^\\]|^)\/([^\/].*)/);
    if (divisionMatch && !result.includes("\\frac")) {
      const beforeDiv =
        (divisionMatch[1] ?? "") +
        (divisionMatch[2] === "^" ? "" : (divisionMatch[2] ?? ""));
      const afterDiv = divisionMatch[3] ?? "";

      // Extract the immediate operands around the division
      const numerator = extractOperand(beforeDiv, true);
      const denominator = extractOperand(afterDiv, false);

      // Get the parts before numerator and after denominator
      const beforeNumerator = beforeDiv.substring(
        0,
        beforeDiv.length - numerator.length,
      );
      const afterDenominator = afterDiv.substring(denominator.length);

      // Don't convert if this looks like it's already a LaTeX fraction
      if (numerator.includes("\\frac") || denominator.includes("\\frac")) {
        break;
      }

      // Recursively convert nested divisions in operands
      const convertedNum = convertDivisionToFraction(numerator);
      const convertedDen = convertDivisionToFraction(denominator);

      result = `${beforeNumerator}\\frac{${convertedNum}}{${convertedDen}}${afterDenominator}`;
      changed = true;
    }
  }

  return result;
};

const getPreviewEquation = (variableName: string, expression: string) => {
  const varName = variableName || "yourVariableName";
  let expr = expression || "yourEquation";

  expr = convertDivisionToFraction(expr);

  return `${varName} = ${expr}`;
};

// Helper to resolve named types in the schema
const resolveNamedType = (typeName: any, schema: any): any => {
  if (typeof typeName !== "string" || !schema) return null;

  // Look in fields
  if (schema.fields && Array.isArray(schema.fields)) {
    for (const field of schema.fields) {
      const fieldType = Array.isArray(field.type)
        ? field.type.find((t: any) => t !== "null")
        : field.type;

      // Direct match in field type
      if (typeof fieldType === "object" && fieldType.name === typeName) {
        return fieldType;
      }

      // Search in nested records
      if (
        typeof fieldType === "object" &&
        fieldType.type === "record" &&
        fieldType.fields &&
        fieldType.name === typeName
      ) {
        return fieldType;
      }

      // Search in array items
      if (
        typeof fieldType === "object" &&
        fieldType.type === "array" &&
        typeof fieldType.items === "object" &&
        fieldType.items.name === typeName
      ) {
        return fieldType.items;
      }
    }
  }

  // Look in types
  if (schema.types && Array.isArray(schema.types)) {
    for (const type of schema.types) {
      if (type.name === typeName && type.type === "record") {
        return type;
      }
    }
  }

  return null;
};

const AddVariableDialog = () => {
  const {
    specialConditionDialog,
    setSpecialConditionDialog,
    setCustomVariables,
    setFilters,
    schema,
    customVariables,
    customListVariables,
    customBlocks,
  } = useCurrentBuilder() || {};

  const dispatch = useAppDispatch();
  const stream = useAppSelector(
    (state: any) => state.boom_filter_v.stream?.name,
  );

  const [variableName, setVariableName] = useState("");
  const [expression, setExpression] = useState("");
  const [cursorPos, setCursorPos] = useState(0);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState(0);
  const [justSelected, setJustSelected] = useState(false);
  const [preventNextSuggestions, setPreventNextSuggestions] = useState(false);
  const [lastInsertedValue, setLastInsertedValue] = useState("");
  const [copySuccess, setCopySuccess] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<any>(null);
  const inputElementRef = useRef<any>(null);
  const suggestionsRef = useRef<any>(null);
  const isKeyboardNavigation = useRef<any>(false);

  // Use actual schema from context, no defaults
  const activeSchema = schema || {};

  const operators = [
    { symbol: "+", name: "Add", type: "arithmetic" },
    { symbol: "-", name: "Subtract", type: "arithmetic" },
    { symbol: "*", name: "Multiply", type: "arithmetic" },
    { symbol: "\\frac{}{}", name: "Fraction", type: "arithmetic" },
    { symbol: "/", name: "Divide", type: "arithmetic" },
    { symbol: "||", name: "Absolute Value", type: "math" },
    { symbol: "sin(", name: "Sine", type: "math" },
    { symbol: "cos(", name: "Cosine", type: "math" },
    { symbol: "tan(", name: "Tangent", type: "math" },
    { symbol: "sqrt(", name: "Square Root", type: "math" },
    { symbol: "pow(", name: "Power", type: "math" },
    { symbol: "abs(", name: "Absolute", type: "math" },
    { symbol: "round(", name: "Round", type: "math" },
    { symbol: "floor(", name: "Floor", type: "math" },
    { symbol: "ceil(", name: "Ceiling", type: "math" },
    { symbol: "min(", name: "Minimum", type: "aggregate" },
    { symbol: "max(", name: "Maximum", type: "aggregate" },
    { symbol: "avg(", name: "Average", type: "aggregate" },
    { symbol: "sum(", name: "Sum", type: "aggregate" },
  ];

  const getSuggestions = (): any[] => {
    const beforeCursor = expression.slice(0, cursorPos);
    const afterCursor = expression.slice(cursorPos);
    const lastWord = beforeCursor.match(/[a-zA-Z._]*$/)?.[0] || "";

    // Don't show suggestions if there's no partial word being typed
    if (!lastWord || lastWord.length === 0) {
      return [];
    }

    // Helper function to check if adding a suggestion would be meaningful
    const wouldChangeMeaningfully = (suggestionValue: string) => {
      const lastWordStart = beforeCursor.search(/[a-zA-Z._]*$/);
      const simulatedExpression =
        expression.slice(0, lastWordStart) + suggestionValue + afterCursor;

      // If the simulated expression is the same as current, don't suggest it
      // Also don't suggest if this is the value we just inserted
      return (
        simulatedExpression !== expression &&
        suggestionValue !== lastInsertedValue
      );
    };

    // Separate arrays for different suggestion types to control order
    const thisFieldSuggestions: any[] = []; // this.* fields (highest priority in array context)
    const fieldSuggestions: any[] = [];
    const operatorSuggestions: any[] = [];
    const variableSuggestions: any[] = [];

    // Field suggestions for Avro schema
    if (
      activeSchema &&
      activeSchema.fields &&
      Array.isArray(activeSchema.fields)
    ) {
      activeSchema.fields.forEach((field: any) => {
        if (field.name && field.type) {
          // Helper function to extract the actual type from various formats
          const extractFieldType = (type: any): any => {
            // String type (e.g., "double", "float", "string")
            if (typeof type === "string") {
              return type;
            }
            // Array/union type (e.g., ["null", "float"])
            if (Array.isArray(type)) {
              const nonNullType = type.find((t: any) => t !== "null");
              if (typeof nonNullType === "string") {
                return nonNullType;
              }
              if (typeof nonNullType === "object" && nonNullType?.type) {
                return nonNullType.type;
              }
            }
            // Object type (e.g., {type: "record", ...})
            if (typeof type === "object" && type?.type) {
              return type.type;
            }
            return null;
          };

          // Get the field type
          const fieldType = extractFieldType(field.type);

          // Helper function to extract array type from potential union types
          const getArrayType = (): any => {
            // Direct array type
            if (fieldType === "array" && typeof field.type === "object") {
              return field.type;
            }
            // Union type (like ["null", {type: "array", ...}])
            if (Array.isArray(field.type)) {
              const arrayTypeInUnion = field.type.find(
                (t: any) => typeof t === "object" && t.type === "array",
              );
              return arrayTypeInUnion;
            }
            return null;
          };

          // Handle array fields - always show subfields with full paths
          if (fieldType === "array") {
            const arrayType = getArrayType();
            if (arrayType) {
              let itemsType = arrayType.items;

              // If items is a string reference, resolve it
              if (typeof itemsType === "string") {
                const resolvedType = resolveNamedType(itemsType, activeSchema);
                if (resolvedType) {
                  itemsType = resolvedType;
                }
              }

              // If the array contains records with fields, suggest them with full path
              if (
                itemsType &&
                typeof itemsType === "object" &&
                itemsType.type === "record" &&
                itemsType.fields
              ) {
                itemsType.fields.forEach((itemField: any) => {
                  // Get the actual type, handling unions
                  let itemFieldType;
                  if (typeof itemField.type === "string") {
                    itemFieldType = itemField.type;
                  } else if (Array.isArray(itemField.type)) {
                    // For union types, get the non-null type
                    const nonNullType = itemField.type.find(
                      (t: any) => t !== "null",
                    );
                    if (typeof nonNullType === "string") {
                      itemFieldType = nonNullType;
                    } else if (typeof nonNullType === "object") {
                      itemFieldType = nonNullType.type;
                    }
                  } else if (typeof itemField.type === "object") {
                    itemFieldType = itemField.type.type;
                  }

                  // Exclude booleans, arrays, and catalog structures from suggestions
                  if (
                    !excludedTypes.includes(itemFieldType) &&
                    (numericTypes.includes(itemFieldType) ||
                      itemFieldType === "record")
                  ) {
                    if (itemFieldType === "record") {
                      // For records (catalogs), don't add the catalog itself, just recurse into subfields
                      const processArrayNestedRecord = (
                        recField: any,
                        parPath: string,
                        dep = 0,
                      ) => {
                        if (dep > 5) return;
                        let recType = null;
                        if (
                          recField.type &&
                          typeof recField.type === "object" &&
                          recField.type.type === "record"
                        ) {
                          recType = recField.type;
                        } else if (Array.isArray(recField.type)) {
                          recType = recField.type.find(
                            (t: any) =>
                              typeof t === "object" && t.type === "record",
                          );
                        }
                        if (recType && recType.fields) {
                          recType.fields.forEach((nestField: any) => {
                            let nestFieldType = extractFieldType(
                              nestField.type,
                            );
                            const nestPath = `${parPath}.${nestField.name}`;
                            const numTypes = ["double", "float", "int", "long"];
                            const isNumField = numTypes.includes(nestFieldType);
                            if (isNumField) {
                              if (
                                nestPath
                                  .toLowerCase()
                                  .includes(lastWord.toLowerCase()) &&
                                wouldChangeMeaningfully(nestPath)
                              ) {
                                thisFieldSuggestions.push({
                                  type: "field",
                                  display: nestField.name,
                                  fullPath: nestPath,
                                  collection: field.name,
                                  description: `${parPath.replace(
                                    /^[^.]+\.?/,
                                    "",
                                  )} → ${nestField.name} (${nestFieldType})`,
                                });
                              }
                            }
                            if (nestFieldType === "record") {
                              processArrayNestedRecord(
                                nestField,
                                nestPath,
                                dep + 1,
                              );
                            }
                          });
                        }
                      };
                      const itemPath = `${field.name}.${itemField.name}`;
                      processArrayNestedRecord(itemField, itemPath);
                    } else {
                      // For numeric/string fields, add the suggestion
                      const itemPath = `${field.name}.${itemField.name}`;

                      // Show suggestions if it matches the search or if lastWord is empty/very short
                      if (
                        itemPath
                          .toLowerCase()
                          .includes(lastWord.toLowerCase()) &&
                        (wouldChangeMeaningfully(itemPath) ||
                          lastWord.length < 2)
                      ) {
                        thisFieldSuggestions.push({
                          type: "field",
                          display: itemField.name,
                          fullPath: itemPath,
                          collection: field.name,
                          description: `${field.name} → ${itemField.name}`,
                        });
                      }
                    }
                  }
                });
              }
            }
            return; // Skip further processing for array fields
          }

          // Exclude booleans and arrays from top-level field suggestions
          // Include numeric fields (but exclude booleans and arrays)
          if (
            !excludedTypes.includes(fieldType) &&
            numericTypes.includes(fieldType)
          ) {
            const fullPath = field.name;

            if (
              fullPath.toLowerCase().includes(lastWord.toLowerCase()) &&
              wouldChangeMeaningfully(fullPath)
            ) {
              fieldSuggestions.push({
                type: "field",
                display: field.name,
                fullPath: fullPath,
                collection: field.name,
                description: `Field: ${field.name} (${fieldType})`,
              });
            }
            return;
          }

          // Skip if it's excluded or not a record type
          if (excludedTypes.includes(fieldType) || fieldType !== "record") {
            return;
          }

          // If it's a record type, suggest its nested fields (except booleans and arrays)
          // This function recursively processes nested records
          const processNestedRecord = (
            recordField: any,
            parentPath: string,
            depth = 0,
            _bandMultiplier: any = null,
          ) => {
            if (depth > 5) return; // Prevent infinite recursion

            // Get the record type - handle both direct records and union types
            let recordType = null;
            if (
              recordField.type &&
              typeof recordField.type === "object" &&
              recordField.type.type === "record"
            ) {
              recordType = recordField.type;
            } else if (Array.isArray(recordField.type)) {
              recordType = recordField.type.find(
                (t: any) => typeof t === "object" && t.type === "record",
              );
            }

            if (recordType && recordType.fields) {
              // Check if this looks like a band-specific container (photstats)
              const isBandContainer =
                recordField.name === "photstats" ||
                parentPath.endsWith(".photstats");

              // Common photometric bands
              const commonBands = ["g", "r", "i", "z", "u", "y"];

              // Helper to find a named type definition within the same record's fields
              const resolveNamedTypeLocally = (typeName: any): any => {
                for (const siblingField of recordType.fields) {
                  // Check if this field defines the named type we're looking for
                  if (Array.isArray(siblingField.type)) {
                    for (const unionType of siblingField.type) {
                      if (
                        typeof unionType === "object" &&
                        unionType.type === "record" &&
                        unionType.name === typeName
                      ) {
                        return unionType;
                      }
                    }
                  } else if (
                    typeof siblingField.type === "object" &&
                    siblingField.type.type === "record" &&
                    siblingField.type.name === typeName
                  ) {
                    return siblingField.type;
                  }
                }
                // Fall back to global resolution
                return resolveNamedType(typeName, activeSchema);
              };

              recordType.fields.forEach((nestedField: any) => {
                // Try to extract field type and resolve named type references
                let nestedFieldType = extractFieldType(nestedField.type);
                let actualNestedFieldObject = nestedField;

                // If extractFieldType returns a string that's not a primitive type,
                // it might be a named type reference - try to resolve it
                const primitiveTypes = [
                  "double",
                  "float",
                  "int",
                  "long",
                  "string",
                  "boolean",
                  "array",
                  "record",
                  "null",
                ];
                if (
                  typeof nestedFieldType === "string" &&
                  !primitiveTypes.includes(nestedFieldType)
                ) {
                  const resolved = resolveNamedTypeLocally(nestedFieldType);
                  if (resolved && resolved.type === "record") {
                    nestedFieldType = "record";
                    // Create a synthetic field object with the resolved type
                    actualNestedFieldObject = {
                      ...nestedField,
                      type: resolved,
                    };
                  }
                }

                // If this is a band container and the field is a single letter that could be a band
                const isBandField =
                  isBandContainer &&
                  nestedField.name.length === 1 &&
                  nestedFieldType === "record";

                if (isBandField) {
                  // Expand this to all common bands
                  commonBands.forEach((band) => {
                    const bandPath = `${parentPath}.${band}`;
                    // Recurse into the band structure for each band
                    processNestedRecord(
                      actualNestedFieldObject,
                      bandPath,
                      depth + 1,
                      band,
                    );
                  });
                } else {
                  const nestedPath = `${parentPath}.${nestedField.name}`;

                  // If it's a numeric field (not boolean, not array), suggest it
                  if (numericTypes.includes(nestedFieldType)) {
                    if (
                      nestedPath
                        .toLowerCase()
                        .includes(lastWord.toLowerCase()) &&
                      wouldChangeMeaningfully(nestedPath)
                    ) {
                      fieldSuggestions.push({
                        type: "field",
                        display: nestedField.name,
                        fullPath: nestedPath,
                        collection: field.name,
                        description: `${`${parentPath.replace(
                          /^[^.]+\.?/,
                          "",
                        )} → ${nestedField.name}`.replace(
                          /^→ /,
                          "",
                        )} (${nestedFieldType})`,
                      });
                    }
                  }
                  // If it's a nested record, recurse (but don't add as suggestion)
                  else if (nestedFieldType === "record") {
                    processNestedRecord(
                      actualNestedFieldObject,
                      nestedPath,
                      depth + 1,
                    );
                  }
                }
              });
            }
          };

          // Process record fields
          if (fieldType === "record") {
            processNestedRecord(field, field.name);
          }
        }
      });
    }

    // Operator suggestions
    operators.forEach((op) => {
      if (
        (op.name.toLowerCase().includes(lastWord.toLowerCase()) ||
          op.symbol.includes(lastWord)) &&
        wouldChangeMeaningfully(op.symbol)
      ) {
        operatorSuggestions.push({
          type: "operator",
          display: op.name,
          value: op.symbol,
          description: op.type,
        });
      }
    });

    // Arithmetic variable suggestions (all are numerical) - ADD LAST
    if (customVariables && Array.isArray(customVariables)) {
      customVariables.forEach((variable: any) => {
        if (
          variable.name &&
          variable.name.toLowerCase().includes(lastWord.toLowerCase()) &&
          wouldChangeMeaningfully(variable.name)
        ) {
          variableSuggestions.push({
            type: "variable",
            display: variable.name,
            value: variable.name,
            fullPath: variable.name,
            description: "Arithmetic Variable",
          });
        }
      });
    }

    // List variable suggestions (only numerical aggregation operators) - ADD LAST
    if (customListVariables && Array.isArray(customListVariables)) {
      const numericalOperators = [
        "$min",
        "$max",
        "$avg",
        "$sum",
        "$size",
        "$stdDevPop",
        "$median",
      ];
      customListVariables.forEach((listVar: any) => {
        if (
          listVar.name &&
          listVar.listCondition &&
          numericalOperators.includes(listVar.listCondition.operator) &&
          listVar.name.toLowerCase().includes(lastWord.toLowerCase()) &&
          wouldChangeMeaningfully(listVar.name)
        ) {
          const operatorName = listVar.listCondition.operator
            .replace("$", "")
            .toUpperCase();
          variableSuggestions.push({
            type: "listVariable",
            display: listVar.name,
            value: listVar.name,
            fullPath: listVar.name,
            description: `List Variable: ${operatorName}`,
          });
        }
      });
    }

    // Combine suggestions with intelligent ordering
    // Prioritize operators (math/aggregate functions), then fields, then variables
    return [
      ...operatorSuggestions,
      ...fieldSuggestions,
      ...thisFieldSuggestions,
      ...variableSuggestions,
    ];
  };

  const suggestions = getSuggestions();

  // Update suggestions visibility
  useEffect(() => {
    // Don't show suggestions if we just selected one or are preventing suggestions
    if (justSelected || preventNextSuggestions) return;

    const shouldShow = suggestions.length > 0 && expression.trim().length > 0;
    setShowSuggestions(shouldShow);
    if (shouldShow) {
      setSelectedSuggestion(0);
    }
  }, [suggestions.length, expression, justSelected, preventNextSuggestions]);

  const handleExpressionChange = (e: any) => {
    setExpression(e.target.value);
    setCursorPos(e.target.selectionStart || 0);
    // Only show suggestions if we didn't just select one and aren't preventing suggestions
    if (!justSelected && !preventNextSuggestions) {
      setShowSuggestions(true);
    }
  };

  const insertSuggestion = (suggestion: any) => {
    if (!inputElementRef.current) return;

    // Set flag first to prevent suggestions from showing
    setJustSelected(true);
    setShowSuggestions(false);

    const beforeCursor = expression.slice(0, cursorPos);
    const afterCursor = expression.slice(cursorPos);
    const lastWordStart = beforeCursor.search(/[a-zA-Z._]*$/);

    const value =
      suggestion.type === "field" ? suggestion.fullPath : suggestion.value;
    const newExpression =
      expression.slice(0, lastWordStart) + value + afterCursor;

    const newPos = lastWordStart + value.length;

    // Track what was inserted to prevent re-suggesting it
    setLastInsertedValue(value);

    setExpression(newExpression);
    setCursorPos(newPos);
    setTimeout(() => {
      setJustSelected(false);
      setLastInsertedValue(""); // Clear after delay
    }, 1000); // Longer delay to prevent premature re-showing

    // Focus and set cursor position
    setTimeout(() => {
      if (inputElementRef.current) {
        inputElementRef.current.focus();
        inputElementRef.current.setSelectionRange(newPos, newPos);
      }
    }, 0);
  };

  const handleKeyDown = (e: any) => {
    if (!showSuggestions) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      isKeyboardNavigation.current = true;
      const newIndex = (selectedSuggestion + 1) % suggestions.length;
      setSelectedSuggestion(newIndex);
      scrollToSuggestion(newIndex);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      isKeyboardNavigation.current = true;
      const newIndex =
        (selectedSuggestion - 1 + suggestions.length) % suggestions.length;
      setSelectedSuggestion(newIndex);
      scrollToSuggestion(newIndex);
    } else if (e.key === "Enter" || e.key === "Tab") {
      e.preventDefault();
      e.stopPropagation();
      if (suggestions[selectedSuggestion]) {
        setPreventNextSuggestions(true);
        insertSuggestion(suggestions[selectedSuggestion]);
        // Prevent any further processing of this Enter key
        setTimeout(() => setPreventNextSuggestions(false), 1000);
      }
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  };

  const scrollToSuggestion = (index: number) => {
    if (suggestionsRef.current) {
      const suggestionElement = suggestionsRef.current.children[index];
      if (suggestionElement) {
        suggestionElement.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });

        // Reset keyboard navigation flag after scrolling completes
        setTimeout(() => {
          isKeyboardNavigation.current = false;
        }, 300);
      }
    }
  };
  const handleCloseSpecialCondition = () => {
    setSpecialConditionDialog({ open: false, blockId: null, equation: "" });
    setVariableName("");
    setExpression("");
    setError(""); // Clear error on close
  };

  const handleCopyPreview = () => {
    const equation = getPreviewEquation(variableName, expression);
    navigator.clipboard
      .writeText(equation)
      .then(() => {
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2000);
      })
      .catch((err: any) => {
        console.error("Failed to copy equation:", err);
      });
  };

  const handleAddVariable = () => {
    setError(""); // Clear any previous error

    if (!variableName.trim() || !expression.trim()) {
      setError("Please enter both a variable name and an expression");
      return;
    }

    // Check if variable name starts with a number
    if (/^[0-9]/.test(variableName)) {
      setError("Variable names cannot start with a number");
      return;
    }

    // Check if variable name contains invalid characters
    const invalidChars = /[\s\-+*^\/%= ]/;
    if (invalidChars.test(variableName)) {
      setError(
        "Variable names cannot contain spaces or mathematical operators (-, +, *, ^, /, %, =)",
      );
      return;
    }

    // Check if a list variable with the same name already exists
    if (customListVariables?.some((lv: any) => lv.name === variableName)) {
      setError(
        `A variable with the name "${variableName}" already exists. Please choose a different name.`,
      );
      return;
    }

    // Check if an arithmetic variable with the same name already exists
    if (customVariables?.some((v: any) => v.name === variableName)) {
      setError(
        `A variable with the name "${variableName}" already exists. Please choose a different name.`,
      );
      return;
    }

    // Check if a block with the same name already exists
    if (customBlocks?.some((b: any) => b.name === `Custom.${variableName}`)) {
      setError(
        `A variable with the name "${variableName}" already exists. Please choose a different name.`,
      );
      return;
    }

    const eq = `${variableName} = ${expression}`;

    dispatch(
      postElement({
        name: variableName,
        data: {
          variable: eq,
          type: "number",
          streams: [stream],
        },
        elements: "variables",
      }),
    );

    setCustomVariables((prev: any[]) => {
      if (prev.some((v: any) => v.name === variableName)) return prev;
      return [
        ...prev,
        {
          name: variableName,
          type: "number",
          variable: eq,
        },
      ];
    });

    // Add a new special condition to the block
    setFilters((prevFilters: any[]) => {
      const addConditionToBlock = (block: any): any => {
        if (block.id === specialConditionDialog.blockId) {
          return {
            ...block,
            children: [
              ...block.children,
              {
                id: uuidv4(),
                category: "condition",
                type: "number",
                field: variableName,
                operator: "$eq",
                value: "",
                createdAt: Date.now(),
              },
            ],
          };
        }
        if (block.children) {
          return {
            ...block,
            children: block.children.map((child: any) =>
              child.category === "block" ? addConditionToBlock(child) : child,
            ),
          };
        }
        return block;
      };
      return prevFilters.map(addConditionToBlock);
    });

    handleCloseSpecialCondition();
  };

  const previewEquation = useMemo(
    () => getPreviewEquation(variableName, expression),
    [variableName, expression],
  );

  return (
    <Dialog
      open={specialConditionDialog.open}
      onClose={handleCloseSpecialCondition}
      maxWidth="md"
      fullWidth
      disableRestoreFocus={false}
      slotProps={{ paper: { sx: { minHeight: "420px", maxHeight: "80vh" } } }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="h6" component="div">
            Add Arithmetic Variable
          </Typography>
        </Box>
        <IconButton onClick={handleCloseSpecialCondition} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {/* Context Selector */}
        {/* Variable Name */}
        <Box sx={{ mb: 3 }}>
          <Typography
            variant="subtitle2"
            gutterBottom
            sx={{ fontWeight: "bold" }}
          >
            Variable Name
          </Typography>
          <TextField
            fullWidth
            value={variableName}
            onChange={(e: any) => setVariableName(e.target.value)}
            placeholder="myVariable"
            size="small"
            autoComplete="off"
            data-form-type="other"
            slotProps={{
              htmlInput: {
                "data-lpignore": "true",
                "data-form-type": "other",
                autoComplete: "off",
              },
            }}
          />
        </Box>

        {/* Expression Builder */}
        <Box sx={{ mb: 3 }}>
          <Typography
            variant="subtitle2"
            gutterBottom
            sx={{ fontWeight: "bold" }}
          >
            Expression
          </Typography>
          <Box sx={{ position: "relative" }}>
            <TextField
              ref={inputRef}
              inputRef={inputElementRef}
              fullWidth
              value={expression}
              onChange={handleExpressionChange}
              onKeyDown={handleKeyDown}
              onClick={(e: any) => setCursorPos(e.target.selectionStart || 0)}
              placeholder="Start typing your expression..."
              size="small"
              autoComplete="off"
              slotProps={{
                htmlInput: {
                  style: { fontFamily: "monospace", fontSize: "14px" },
                },
              }}
              sx={{
                "& .MuiOutlinedInput-root": {
                  fontFamily: "monospace",
                },
              }}
            />

            {showSuggestions && suggestions.length > 0 && (
              <Paper
                ref={suggestionsRef}
                sx={{
                  position: "absolute",
                  top: "100%",
                  left: 0,
                  right: 0,
                  zIndex: 1000,
                  width: "100%",
                  mt: 0.5,
                  maxHeight: 250,
                  overflow: "auto",
                  boxShadow: 3,
                }}
              >
                {suggestions.map((suggestion: any, idx: number) => (
                  <Box
                    key={idx}
                    onMouseDown={(e: any) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                    onClick={(e: any) => {
                      e.preventDefault();
                      e.stopPropagation();
                      insertSuggestion(suggestion);
                    }}
                    onMouseEnter={() => {
                      if (!isKeyboardNavigation.current) {
                        setSelectedSuggestion(idx);
                      }
                    }}
                    sx={{
                      px: 2,
                      py: 1.5,
                      cursor: "pointer",
                      bgcolor:
                        idx === selectedSuggestion
                          ? "primary.100"
                          : "transparent",
                      border:
                        idx === selectedSuggestion
                          ? "1px solid"
                          : "1px solid transparent",
                      borderColor:
                        idx === selectedSuggestion
                          ? "primary.300"
                          : "transparent",
                      "&:hover": {
                        bgcolor:
                          idx === selectedSuggestion
                            ? "primary.100"
                            : "grey.50",
                      },
                      borderBottom: "1px solid",
                      borderBottomColor: "divider",
                      "&:last-child": { borderBottom: "none" },
                      transition: "all 0.15s ease-in-out",
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <Box>
                        <Typography
                          variant="body2"
                          sx={{ fontFamily: "monospace", fontWeight: "bold" }}
                        >
                          {suggestion.type === "field"
                            ? suggestion.fullPath
                            : suggestion.value}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {suggestion.description}
                        </Typography>
                      </Box>
                      <Box
                        sx={{
                          px: 1,
                          py: 0.5,
                          borderRadius: 1,
                          bgcolor:
                            suggestion.type === "variable"
                              ? "warning.100"
                              : suggestion.type === "listVariable"
                                ? "success.100"
                                : suggestion.type === "field"
                                  ? "info.100"
                                  : "secondary.100",
                          color:
                            suggestion.type === "variable"
                              ? "warning.800"
                              : suggestion.type === "listVariable"
                                ? "success.800"
                                : suggestion.type === "field"
                                  ? "info.800"
                                  : "secondary.800",
                        }}
                      >
                        <Typography
                          variant="caption"
                          sx={{ fontWeight: "bold" }}
                        >
                          {suggestion.type}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                ))}
              </Paper>
            )}
          </Box>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ mt: 0.5, display: "block" }}
          >
            Type field names or operators. Use ↑↓ to navigate, Tab/Enter to
            select, Esc to close.
          </Typography>
        </Box>

        {/* Preview with EquationEditor */}
        <Box>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 1,
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: "bold" }}>
              Preview
            </Typography>
            <Button
              size="small"
              startIcon={<ContentCopy />}
              onClick={handleCopyPreview}
              variant="outlined"
              sx={{ minWidth: "auto" }}
            >
              {copySuccess ? "Copied!" : "Copy"}
            </Button>
          </Box>
          <Box
            sx={{
              p: 2,
              bgcolor: "background.default",
              borderRadius: 1,
              border: "1px solid",
              borderColor: "divider",
              minHeight: 80,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <EquationEditor
              key={`${variableName}-${expression}`}
              value={previewEquation}
              onChange={() => {}}
              autoCommands="pi theta sqrt sum prod alpha beta gamma rho"
              autoOperatorNames="sin cos tan log ln exp abs"
            />
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleCloseSpecialCondition}>Cancel</Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleAddVariable}
          disabled={!variableName.trim() || !expression.trim()}
        >
          Add Variable
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddVariableDialog;
