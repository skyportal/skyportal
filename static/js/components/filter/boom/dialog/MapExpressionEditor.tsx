import { useState, useMemo } from "react";
import {
  Box,
  Typography,
  TextField,
  Paper,
  Popover,
  Button,
  IconButton,
} from "@mui/material";
import {
  Info,
  Add as AddIcon,
  Delete as DeleteIcon,
} from "@mui/icons-material";
import Latex from "react-latex-next";
import AutocompleteFields from "../condition/AutocompleteFields";
import { normalizeFieldValue } from "../../../../utils/conditionHelpers";

// Helper function to escape LaTeX special characters for display
const escapeLatexForDisplay = (text: any) => {
  if (!text) return text;
  // Escape underscores to prevent subscript rendering
  // Replace _ with \_ to show it as literal underscore
  return text.replace(/_/g, "\\_");
};

interface MapExpressionEditorProps {
  mapFields: any[];
  onMapFieldsChange: (...a: any[]) => void;
  arrayField: string;
  subFieldOptions: any[];
  customVariables?: any[];
}

const MapExpressionEditor = ({
  mapFields,
  onMapFieldsChange,
  customVariables = [],
}: MapExpressionEditorProps) => {
  const [openEquationIds, setOpenEquationIds] = useState<any[]>([]);
  const [, setSelectedChip] = useState<any>(null);
  const [equationAnchor, setEquationAnchor] = useState<any>(null);

  // Convert customVariables to fieldOptions format
  const fieldOptions = useMemo(() => {
    return customVariables.map((v: any) => ({
      label: normalizeFieldValue(v.name),
      value: normalizeFieldValue(v.name),
      group: "Arithmetic Variables",
      isVariable: true,
    }));
  }, [customVariables]);

  const handleAddField = () => {
    onMapFieldsChange([...mapFields, { fieldName: "", expression: "" }]);
  };

  const handleRemoveField = (index: number) => {
    onMapFieldsChange(mapFields.filter((_: any, i: number) => i !== index));
  };

  const handleFieldChange = (index: number, field: string, value: any) => {
    const updated = [...mapFields];
    updated[index] = { ...updated[index], [field]: value };
    onMapFieldsChange(updated);
  };

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        <Info fontSize="small" sx={{ verticalAlign: "middle", mr: 0.5 }} />
        Define fields to create in each transformed array element. Each field
        can use an arithmetic variable.
      </Typography>

      <Paper
        variant="outlined"
        sx={{
          p: 2,
          mb: 2,
          backgroundColor: "background.paper",
        }}
      >
        {mapFields.map((field: any, index: number) => (
          <Box
            key={index}
            sx={{
              mb: index < mapFields.length - 1 ? 3 : 2,
              pb: index < mapFields.length - 1 ? 3 : 0,
              borderBottom: index < mapFields.length - 1 ? "1px solid" : "none",
              borderColor: "grey.300",
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
              <Typography variant="subtitle2" sx={{ flex: 1 }}>
                Field {index + 1}
              </Typography>
              {mapFields.length > 1 && (
                <IconButton
                  size="small"
                  onClick={() => handleRemoveField(index)}
                  color="error"
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              )}
            </Box>

            <Box sx={{ mb: 2 }}>
              <Typography
                variant="caption"
                color="text.secondary"
                gutterBottom
                sx={{ display: "block" }}
              >
                Field Name
              </Typography>
              <TextField
                fullWidth
                size="small"
                value={field.fieldName}
                onChange={(e: any) =>
                  handleFieldChange(index, "fieldName", e.target.value)
                }
                placeholder="name"
              />
            </Box>

            <Box>
              <Typography
                variant="caption"
                color="text.secondary"
                gutterBottom
                sx={{ display: "block" }}
              >
                Expression
              </Typography>
              <AutocompleteFields
                fieldOptions={fieldOptions}
                value={field.expression}
                onChange={(value: any) =>
                  handleFieldChange(index, "expression", value)
                }
                conditionOrBlock={{ id: `map-expression-editor-${index}` }}
                setOpenEquationIds={setOpenEquationIds}
                setSelectedChip={setSelectedChip}
                setEquationAnchor={setEquationAnchor}
                side="left"
              />
            </Box>
          </Box>
        ))}

        <Button
          startIcon={<AddIcon />}
          onClick={handleAddField}
          size="small"
          sx={{ mt: 1 }}
        >
          Add Field
        </Button>
      </Paper>

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
              // Extract the field index from the condition ID
              const conditionId = openEquationIds[0];
              const match = conditionId?.match(/map-expression-editor-(\d+)/);
              let expressionValue = "";

              if (match) {
                const fieldIndex = parseInt(match[1], 10);
                expressionValue = mapFields[fieldIndex]?.expression || "";
              }

              const variableOption = fieldOptions.find(
                (opt: any) => opt.label === expressionValue && opt.isVariable,
              );

              if (variableOption) {
                const eqObj = customVariables?.find(
                  (eq: any) => eq.name === variableOption.label,
                );
                const equation = eqObj ? eqObj.variable : null;
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
    </Box>
  );
};

export default MapExpressionEditor;
