import { Popover, Box, Typography, Paper, Chip } from "@mui/material";
import BlockComponent from "../block/BlockComponent";

// Helper function to normalize field/value objects to strings
// Supports:
// - String values (legacy): "fieldName"
// - Object with metadata (new): { name: "fieldName", _meta: {...} }
const normalizeValue = (val: any) => {
  if (!val) return "";
  if (typeof val === "string") return val;
  if (typeof val === "object" && val.name) return val.name;
  return String(val);
};

interface ValueChipProps {
  value?: any;
  customVariables?: any[];
  customListVariables?: any[];
  customSwitchCases?: any[];
  fieldOptionsList: any[];
}

// Helper component to render a chip for field/variable values
const ValueChip = ({
  value,
  customVariables = [],
  customListVariables = [],
  customSwitchCases = [],
  fieldOptionsList = [],
}: ValueChipProps) => {
  // Normalize value to handle both string and object formats
  const normalizedValue = normalizeValue(value);

  if (!normalizedValue || normalizedValue === "") {
    return (
      <span style={{ fontStyle: "italic", color: "#9ca3af" }}>(empty)</span>
    );
  }

  // Check if it's an arithmetic variable (yellow)
  const variable = customVariables.find((v: any) => v.name === normalizedValue);
  if (variable) {
    return (
      <Chip
        label={normalizedValue}
        size="small"
        sx={{
          background: "#fde68a",
          color: "#b45309",
          fontWeight: 700,
          border: "1.5px solid #fbbf24",
          fontSize: "0.875rem",
        }}
      />
    );
  }

  // Check if it's a list variable (green)
  const listVariable = customListVariables.find(
    (lv: any) => lv.name === normalizedValue,
  );
  if (listVariable) {
    return (
      <Chip
        label={normalizedValue}
        size="small"
        sx={{
          background: "#bbf7d0",
          color: "#166534",
          fontWeight: 700,
          border: "1.5px solid #4ade80",
          fontSize: "0.875rem",
        }}
      />
    );
  }

  // Check if it's a switch case (grey)
  const switchCase = customSwitchCases.find(
    (sc: any) => sc.name === normalizedValue,
  );
  if (switchCase) {
    return (
      <Chip
        label={normalizedValue}
        size="small"
        sx={{
          background: "#e5e7eb",
          color: "#374151",
          fontWeight: 700,
          border: "1.5px solid #9ca3af",
          fontSize: "0.875rem",
        }}
      />
    );
  }

  // Check if it's a field (blue)
  const field = fieldOptionsList.find((f: any) => f.label === normalizedValue);
  if (field) {
    return (
      <Chip
        label={normalizedValue}
        size="small"
        sx={{
          background: "#dbeafe",
          color: "#1e40af",
          fontWeight: 600,
          border: "1.5px solid #60a5fa",
          fontSize: "0.875rem",
        }}
      />
    );
  }

  // Default - just plain text (could be a literal value)
  return (
    <Typography
      variant="body2"
      component="span"
      sx={{
        backgroundColor: "#f9fafb",
        color: "#1f2937",
        px: 1.5,
        py: 0.5,
        borderRadius: 1,
        fontFamily: "monospace",
        border: "1px solid #e5e7eb",
        display: "inline-block",
      }}
    >
      {normalizedValue}
    </Typography>
  );
};

interface SwitchCasePopoverProps {
  switchPopoverAnchor?: any;
  setSwitchPopoverAnchor: (value: any) => void;
  customSwitchCases: any[];
  customVariables?: any[];
  customListVariables?: any[];
  fieldOptionsList: any[];
}

const SwitchCasePopover = ({
  switchPopoverAnchor,
  setSwitchPopoverAnchor,
  customSwitchCases,
  customVariables = [],
  customListVariables = [],
  fieldOptionsList,
}: SwitchCasePopoverProps) => {
  const isOpen = Boolean(switchPopoverAnchor);

  const handleClose = () => {
    const anchorElement = switchPopoverAnchor;
    setSwitchPopoverAnchor(null);
    (window as any).currentSwitchCase = null;

    if (anchorElement) {
      setTimeout(() => {
        if (anchorElement && typeof anchorElement.focus === "function") {
          try {
            anchorElement.focus();
          } catch {
            document.body.focus();
          }
        }
      }, 100);
    }
  };

  const renderSwitchCaseContent = () => {
    const switchCase = (window as any).currentSwitchCase;
    if (!switchCase) {
      return null;
    }

    const { name, switchCondition } = switchCase;
    const cases = switchCondition?.value?.cases || [];
    const defaultValue = switchCondition?.value?.default || "";

    return (
      <Box
        sx={{
          p: 3,
          width: 1000,
          maxWidth: "95vw",
          background:
            "linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 50%, #d1d5db 100%)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            mb: 3,
            pb: 2,
            borderBottom: "2px solid",
            borderColor: "#6b7280",
          }}
        >
          <Box
            sx={{
              width: 4,
              height: 32,
              backgroundColor: "#6b7280",
              borderRadius: 1,
            }}
          />
          <Typography variant="h6" sx={{ fontWeight: 600, color: "#374151" }}>
            Switch Case: {name}
          </Typography>
        </Box>

        <Box
          sx={{
            maxHeight: "70vh",
            overflowY: "auto",
            overflowX: "hidden",
            pr: 1,
          }}
        >
          {cases.map((caseItem: any, index: number) => (
            <Paper
              key={index}
              sx={{
                mb: 3,
                p: 2.5,
                border: "1px solid",
                borderColor: "#d1d5db",
                backgroundColor: "white",
                borderRadius: 2,
                boxShadow: "0 2px 8px 0 rgba(107,114,128,0.12)",
                transition: "all 0.2s",
                "&:hover": {
                  borderColor: "#6b7280",
                  boxShadow: "0 4px 12px 0 rgba(107,114,128,0.18)",
                },
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  mb: 2,
                }}
              >
                <Box
                  sx={{
                    width: 24,
                    height: 24,
                    borderRadius: "50%",
                    backgroundColor: "#6b7280",
                    color: "white",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  {index + 1}
                </Box>
                <Typography
                  variant="subtitle2"
                  sx={{ fontWeight: 600, color: "#374151" }}
                >
                  CASE {index + 1}
                </Typography>
              </Box>

              {/* Display the block conditions (read-only) */}
              {caseItem.block &&
              caseItem.block.children &&
              caseItem.block.children.length > 0 ? (
                <Box sx={{ mb: 2, width: "100%", minWidth: 0 }}>
                  <BlockComponent
                    block={caseItem.block}
                    parentBlockId={null}
                    isRoot={true}
                    fieldOptionsList={fieldOptionsList}
                    customVariables={customVariables}
                    customListVariables={customListVariables}
                    customSwitchCases={customSwitchCases}
                    localFilters={[caseItem.block]}
                    setLocalFilters={() => {}} // Read-only
                    disableSwitchOption={true}
                  />
                </Box>
              ) : (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 2, pl: 1, fontStyle: "italic" }}
                >
                  No conditions
                </Typography>
              )}

              {/* Display THEN value */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  mt: 2,
                  pl: 1,
                  pt: 2,
                  borderTop: "1px dashed",
                  borderColor: "#d1d5db",
                }}
              >
                <Typography
                  variant="caption"
                  sx={{ fontWeight: 700, minWidth: 50, color: "#374151" }}
                >
                  THEN:
                </Typography>
                <Box sx={{ flex: 1 }}>
                  <ValueChip
                    value={caseItem.then}
                    customVariables={customVariables}
                    customListVariables={customListVariables}
                    customSwitchCases={customSwitchCases}
                    fieldOptionsList={fieldOptionsList}
                  />
                </Box>
              </Box>
            </Paper>
          ))}

          {/* Display DEFAULT value */}
          <Paper
            sx={{
              p: 2.5,
              border: "2px solid",
              borderColor: "#6b7280",
              backgroundColor: "white",
              borderRadius: 2,
              boxShadow: "0 2px 8px 0 rgba(107,114,128,0.15)",
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: 700, color: "#374151", minWidth: 80 }}
              >
                DEFAULT:
              </Typography>
              <Box sx={{ flex: 1 }}>
                <ValueChip
                  value={defaultValue}
                  customVariables={customVariables}
                  customListVariables={customListVariables}
                  customSwitchCases={customSwitchCases}
                  fieldOptionsList={fieldOptionsList}
                />
              </Box>
            </Box>
          </Paper>
        </Box>
      </Box>
    );
  };

  return (
    <Popover
      open={isOpen}
      anchorEl={switchPopoverAnchor}
      onClose={handleClose}
      anchorOrigin={{
        vertical: "bottom",
        horizontal: "left",
      }}
      transformOrigin={{
        vertical: "top",
        horizontal: "left",
      }}
      slotProps={{
        paper: {
          sx: {
            maxHeight: "85vh",
            overflowY: "visible",
            overflowX: "hidden",
            width: "auto",
            maxWidth: "95vw",
          },
        },
      }}
    >
      {renderSwitchCaseContent()}
    </Popover>
  );
};

export default SwitchCasePopover;
