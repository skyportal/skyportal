import React, { useState, useEffect } from "react";
import {
  Button,
  Box,
  Typography,
  Paper,
  IconButton,
  FormControl,
  Select,
  MenuItem,
  TextField,
  InputLabel,
} from "@mui/material";
import {
  Code as CodeIcon,
  ArrowBack as ArrowBackIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import {
  useFilterBuilder,
  useAnnotationBuilder,
} from "../../../hooks/useContexts";
import { getFieldOptionsWithVariable } from "../../../utils/conditionHelpers";
import MongoQueryDialog from "./dialog/MongoQueryDialog";
import MapAnnotationsDialog from "./dialog/MapAnnotationsDialog";
import AutocompleteFields from "./condition/AutocompleteFields";
import EquationPopover from "./EquationPopover";
import { filterBuilderStyles } from "../../../styles/componentStyles";
import { latexToMongoConverter } from "../../../utils/robustLatexConverter";
import {
  flattenFieldOptions,
  getArrayFieldSubOptions,
} from "../../../constants/filterConstants";
import { useFilterSchema } from "../../../ducks/boom_filter_modules";
import { useBoomFilterVersion } from "../../../ducks/boom_filter";

interface AnnotationBuilderContentProps {
  onBackToFilterBuilder?: (...a: any[]) => void;
}

const AnnotationBuilderContent = ({
  onBackToFilterBuilder,
}: AnnotationBuilderContentProps) => {
  const {
    filters,
    projectionFields,
    setProjectionFields,
    setFilters,
    createDefaultBlock,
  } = useAnnotationBuilder();
  const { hasValidQuery: hasValidFilterQuery } = useFilterBuilder();
  const filterContext = useFilterBuilder();
  const navigate = useNavigate();

  const { data: store_schema } = useFilterSchema();
  const { data: boomFilterVersion } = useBoomFilterVersion();
  const filter_stream = boomFilterVersion?.stream?.name?.split(" ")[0];

  const [schema, setSchema] = useState<any>(null);
  const [fieldOptions, setFieldOptions] = useState<any[]>([]);
  const [collapsedGroups, setCollapsedGroups] = useState<any>(new Set());
  const [mapDialogOpen, setMapDialogOpen] = useState(false);
  const [mapDialogFieldId, setMapDialogFieldId] = useState<any>(null);
  const [mapProjectionFields, setMapProjectionFields] = useState<any[]>([]);
  const [openEquationIds, setOpenEquationIds] = useState<any[]>([]);
  const [, setSelectedChip] = useState<any>(null);
  const [equationAnchor, setEquationAnchor] = useState<any>(null);

  // Initialize annotation filters if empty
  useEffect(() => {
    if (filters.length === 0) {
      setFilters([createDefaultBlock("And")]);
    }
  }, [filters.length, createDefaultBlock, setFilters]);

  useEffect(() => {
    if (!projectionFields || projectionFields.length === 0) {
      setProjectionFields([
        {
          id: `annotation-${Date.now()}`,
          fieldName: "",
          outputName: "",
          type: "include",
          roundDecimals: 4,
          isDefault: false,
        },
      ]);
    }
  }, [projectionFields, setProjectionFields]);

  useEffect(() => {
    if (store_schema) {
      setSchema(store_schema);
      setFieldOptions(flattenFieldOptions(store_schema));
    }
  }, [store_schema]);

  const getFieldOptions = () => {
    if (!fieldOptions || fieldOptions.length === 0) {
      return [];
    }

    return getFieldOptionsWithVariable(
      fieldOptions,
      filterContext.customVariables || [],
      filterContext.customListVariables || [],
      filterContext.customSwitchCases || [],
      [],
      null,
      filter_stream,
    )
      .map((field: any) => {
        const fieldName = field.label || field.name;
        let subFields = field.subFields || [];
        if (field.type === "array") {
          subFields = getArrayFieldSubOptions(fieldName, schema);
        }
        let expression = field.expression;
        if (field.isVariable) {
          const dbVar = (filterContext.customVariables || []).find(
            (v: any) => v.name === fieldName,
          );
          if (dbVar && dbVar.variable) {
            expression = latexToMongoConverter.convertToMongo(
              dbVar.variable.split("=")[1].trim(),
            );
          } else if (field.value && !expression) {
            expression = latexToMongoConverter.convertToMongo(field.value);
          }
        }
        return {
          name: fieldName,
          type: field.type || "string",
          label: fieldName,
          description: field.description || "",
          isVariable: field.isVariable || false,
          isListVariable: field.isListVariable || false,
          group: field.isVariable
            ? "Arithmetic Variables"
            : field.isListVariable
              ? "Database List Variables"
              : field.group ||
                (fieldName.split(".").length > 1
                  ? fieldName.split(".")[0]
                  : `${filter_stream} fields`),
          isArray: field.type === "array",
          isArrayVariable:
            field.type === "array_variable" || field.type === "array_switch",
          subFields:
            field.type === "array_variable" || field.type === "array_switch"
              ? field.listCondition?.subFieldOptions
              : subFields,
          ...(expression ? { expression } : {}),
        };
      })
      .filter((field: any) => field && field.name && field.name !== "objectId")
      .sort((a: any, b: any) => {
        if (a.group < b.group) return -1;
        if (a.group > b.group) return 1;
        return a.name.localeCompare(b.name);
      });
  };

  const addProjectionField = () => {
    setProjectionFields([
      ...projectionFields,
      {
        id: Date.now(),
        fieldName: "",
        outputName: "",
        type: "include",
        roundDecimals: 4,
        isDefault: false,
      },
    ]);
  };

  const removeProjectionField = (id: any) => {
    setProjectionFields((fields: any[]) =>
      fields.filter((f: any) => f.id !== id),
    );
  };

  const updateProjectionField = (id: any, updates: any) => {
    setProjectionFields((fields: any[]) =>
      fields.map((f: any) => (f.id === id ? { ...f, ...updates } : f)),
    );
  };

  const handleBackToFilters = () => {
    if (onBackToFilterBuilder) {
      onBackToFilterBuilder();
    } else {
      navigate("/");
    }
  };

  const availableFields = getFieldOptions();

  React.useEffect(() => {
    const allGroups = [
      ...new Set(availableFields.map((field: any) => field.group)),
    ];
    if (allGroups.length > 0 && allGroups.length > collapsedGroups.size) {
      setCollapsedGroups(new Set(allGroups));
    }
  }, [availableFields, collapsedGroups.size]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        ...filterBuilderStyles.container,
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={handleBackToFilters}
            sx={{ "&:hover": { backgroundColor: "primary.50" } }}
          >
            Back to Filters
          </Button>
          <Typography variant="h4" sx={{ color: "text.primary" }}>
            Annotations
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<CodeIcon />}
          onClick={() => filterContext.setMongoDialog({ open: true })}
          disabled={!hasValidFilterQuery()}
          sx={{
            borderColor: hasValidFilterQuery() ? "primary.main" : undefined,
            color: hasValidFilterQuery() ? "primary.main" : undefined,
            "&:hover": {
              borderColor: hasValidFilterQuery() ? "primary.dark" : undefined,
              backgroundColor: hasValidFilterQuery() ? "primary.50" : undefined,
            },
          }}
        >
          Test/Preview filter output
        </Button>
      </Box>

      {/* Projection Fields */}
      <Paper sx={{ p: 3 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 3,
          }}
        >
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={addProjectionField}
            size="small"
          >
            Add Annotation
          </Button>
        </Box>

        {projectionFields.length === 0 ? (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ textAlign: "center", py: 4 }}
          >
            No annotations configured. Add annotations to specify what should be
            included in the query results.
          </Typography>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {projectionFields.map((field: any) => (
              <Paper key={field.id} variant="outlined" sx={{ p: 2 }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    flexWrap: "nowrap",
                    overflowX: "auto",
                  }}
                >
                  <TextField
                    label="Annotation Name"
                    value={field.outputName}
                    onChange={(e: any) =>
                      updateProjectionField(field.id, {
                        outputName: e.target.value,
                      })
                    }
                    size="small"
                    sx={{ minWidth: 150 }}
                    placeholder={field.fieldName}
                  />

                  <Box sx={{ minWidth: 200, maxWidth: 300, flexShrink: 0 }}>
                    <AutocompleteFields
                      fieldOptions={availableFields}
                      value={field.fieldName ? { name: field.fieldName } : ""}
                      onChange={(newValue: any) => {
                        const fieldName =
                          typeof newValue === "string"
                            ? newValue
                            : newValue?.name || "";
                        const fullOption: any = availableFields.find(
                          (opt: any) => opt.name === fieldName,
                        );
                        let subFields = fullOption?.subFields || [];
                        if (
                          fullOption?.isArray &&
                          subFields.length === 0 &&
                          fullOption?.schema &&
                          Array.isArray(fullOption.schema)
                        ) {
                          const firstObj = fullOption.schema[0];
                          if (firstObj && typeof firstObj === "object") {
                            subFields = Object.keys(firstObj);
                          }
                        }
                        updateProjectionField(field.id, {
                          fieldName,
                          isArray:
                            fullOption?.type === "array" ||
                            fullOption?.type === "array_variable" ||
                            fullOption?.type === "array_switch",
                          subFields,
                        });
                      }}
                      conditionOrBlock={{
                        id: field.id,
                        field: field.fieldName,
                      }}
                      setOpenEquationIds={setOpenEquationIds}
                      setSelectedChip={setSelectedChip}
                      setEquationAnchor={setEquationAnchor}
                      side="annotation"
                    />
                  </Box>
                  <EquationPopover
                    open={
                      openEquationIds.includes(field.id) && !!equationAnchor
                    }
                    anchorEl={equationAnchor}
                    onClose={() => {
                      setOpenEquationIds([]);
                      setEquationAnchor(null);
                    }}
                    variableName={field.fieldName}
                    customVariables={filterContext.customVariables || []}
                  />

                  <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                    <FormControl size="small" sx={{ minWidth: 120 }}>
                      <InputLabel>Type</InputLabel>
                      <Select
                        value={field.type}
                        onChange={(e: any) => {
                          const newType = e.target.value;
                          let updates: any = { type: newType };
                          if (["sum", "avg", "min", "max"].includes(newType)) {
                            let subFields = field.subFields || [];
                            if (
                              (!subFields || subFields.length === 0) &&
                              field.fieldName
                            ) {
                              const found: any = availableFields.find(
                                (opt: any) => opt.name === field.fieldName,
                              );
                              if (found?.subFields?.length > 0) {
                                subFields = found.subFields;
                              }
                            }
                            if (
                              (!subFields || subFields.length === 0) &&
                              field.listCondition?.subFieldOptions
                            ) {
                              subFields = field.listCondition.subFieldOptions;
                            }
                            if (subFields && subFields.length > 0) {
                              updates.subField = subFields[0];
                              updates.subFields = subFields;
                            }
                          }
                          updateProjectionField(field.id, updates);
                        }}
                        label="Type"
                      >
                        <MenuItem value="include">Include</MenuItem>
                        <MenuItem value="exclude">Exclude</MenuItem>
                        <MenuItem value="round">Round</MenuItem>
                        {field.isArray && <MenuItem value="map">Map</MenuItem>}
                        {field.isArray && <MenuItem value="min">Min</MenuItem>}
                        {field.isArray && <MenuItem value="max">Max</MenuItem>}
                        {field.isArray && <MenuItem value="sum">Sum</MenuItem>}
                        {field.isArray && (
                          <MenuItem value="avg">Average</MenuItem>
                        )}
                        {field.isArray && (
                          <MenuItem value="count">Count</MenuItem>
                        )}
                      </Select>
                    </FormControl>
                    {field.type === "map" && (
                      <Button
                        variant="outlined"
                        size="small"
                        sx={{ ml: 1, alignSelf: "center" }}
                        onClick={() => {
                          setMapDialogFieldId(field.id);
                          setMapDialogOpen(true);
                        }}
                      >
                        {field.mapSaved && field.mapOutputFieldName
                          ? `${field.mapOutputFieldName}_mapped`
                          : "Map Annotations"}
                      </Button>
                    )}
                    {field.isArray &&
                      ["sum", "avg", "min", "max"].includes(field.type) &&
                      field.subFields &&
                      field.subFields.length > 0 && (
                        <>
                          <FormControl size="small" sx={{ minWidth: 150 }}>
                            <InputLabel>Subfield</InputLabel>
                            <Select
                              value={field.subField || ""}
                              onChange={(e: any) =>
                                updateProjectionField(field.id, {
                                  subField: e.target.value,
                                })
                              }
                              label="Subfield"
                            >
                              {(
                                field.subFields ||
                                field.listCondition?.subFieldOptions ||
                                []
                              ).map((opt: any) => {
                                const value =
                                  typeof opt === "object" &&
                                  opt !== null &&
                                  opt.label
                                    ? opt.label
                                    : String(opt);
                                return (
                                  <MenuItem key={value} value={value}>
                                    {value}
                                  </MenuItem>
                                );
                              })}
                            </Select>
                          </FormControl>
                          <FormControl size="small" sx={{ minWidth: 120 }}>
                            <InputLabel>Aggregation Output</InputLabel>
                            <Select
                              value={field.aggregationOutputType || "include"}
                              onChange={(e: any) =>
                                updateProjectionField(field.id, {
                                  aggregationOutputType: e.target.value,
                                })
                              }
                              label="Aggregation Output"
                            >
                              <MenuItem value="include">Include</MenuItem>
                              <MenuItem value="exclude">Exclude</MenuItem>
                              <MenuItem value="round">Round</MenuItem>
                            </Select>
                          </FormControl>
                          {field.aggregationOutputType === "round" && (
                            <TextField
                              label="Decimals"
                              type="number"
                              value={field.roundDecimals}
                              onChange={(e: any) =>
                                updateProjectionField(field.id, {
                                  roundDecimals: Math.max(
                                    0,
                                    Math.min(10, parseInt(e.target.value) || 0),
                                  ),
                                })
                              }
                              size="small"
                              sx={{ width: 100 }}
                              slotProps={{ htmlInput: { min: 0, max: 10 } }}
                            />
                          )}
                        </>
                      )}
                  </Box>

                  {field.type === "round" && (
                    <TextField
                      label="Decimals"
                      type="number"
                      value={field.roundDecimals}
                      onChange={(e: any) =>
                        updateProjectionField(field.id, {
                          roundDecimals: Math.max(
                            0,
                            Math.min(10, parseInt(e.target.value) || 0),
                          ),
                        })
                      }
                      size="small"
                      sx={{ width: 100 }}
                      slotProps={{ htmlInput: { min: 0, max: 10 } }}
                    />
                  )}

                  <IconButton
                    onClick={() => removeProjectionField(field.id)}
                    color="error"
                    size="small"
                  >
                    <DeleteIcon />
                  </IconButton>
                </Box>
              </Paper>
            ))}
          </Box>
        )}
      </Paper>

      <MapAnnotationsDialog
        open={mapDialogOpen}
        onClose={() => setMapDialogOpen(false)}
        arrayField={projectionFields.find(
          (f: any) => f.id === mapDialogFieldId,
        )}
        mapProjectionFields={mapProjectionFields}
        setMapProjectionFields={setMapProjectionFields}
        onSave={({ outputFieldName, mongoMapQuery }: any) => {
          setProjectionFields((fields: any[]) =>
            fields.map((f: any) =>
              f.id === mapDialogFieldId
                ? {
                    ...f,
                    mapSaved: true,
                    mapOutputFieldName: outputFieldName,
                    mapMongoMapQuery: mongoMapQuery,
                  }
                : f,
            ),
          );
        }}
      />

      <MongoQueryDialog />
    </Box>
  );
};

export default AnnotationBuilderContent;
