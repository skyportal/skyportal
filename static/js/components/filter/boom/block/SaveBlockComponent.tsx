import { useState } from "react";
import { Button, Typography } from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";

interface SaveBlockComponentProps {
  setSaveDialog: (...a: any[]) => void;
  setSaveName: (...a: any[]) => void;
  setSaveError: (...a: any[]) => void;
  setFilters: (...a: any[]) => void;
  isCustomBlock?: boolean | undefined;
  isCollapsed?: boolean | undefined;
  block: any;
}

const SaveBlockComponent = ({
  setSaveDialog,
  setSaveName,
  setSaveError,
  setFilters,
  isCustomBlock,
  isCollapsed,
  block,
}: SaveBlockComponentProps) => {
  const [localSaveError, setLocalSaveError] = useState("");

  // TODO: Implement robust validation logic for the block
  const validateBlock = (b: any): boolean => {
    if (b.category === "condition") {
      if (b.isListVariable) {
        return !!b.field;
      }

      // Operators that don't require a value or accept boolean/special values
      const operatorsWithOptionalValue = [
        "$exists",
        "$isNumber",
        "$anyElementTrue",
        "$allElementsTrue",
      ];
      if (operatorsWithOptionalValue.includes(b.operator)) {
        return true; // Value is optional or can be any type (including false)
      }

      // Check if field and operator are present
      if (!b.field || !b.operator) {
        return false;
      }

      // Regular conditions need field, operator, and value
      return b.value !== "" && b.value !== null && b.value !== undefined;
    }
    if (b.category === "block") {
      return b.children.length > 0 && b.children.every(validateBlock);
    }
    return false;
  };

  const handleSaveBlock = () => {
    if (!validateBlock(block)) {
      setLocalSaveError("Please fill all fields before saving.");
      setTimeout(() => setLocalSaveError(""), 3000);
      return;
    }

    try {
      setFilters((prevFilters: any[]) => {
        const updateBlock = (b: any): any => {
          if (b.id !== block.id) {
            return {
              ...b,
              children: b.children
                ? b.children.map((child: any) =>
                    child.category === "block" ? updateBlock(child) : child,
                  )
                : [],
            };
          }
          return { ...b, isTrue: true };
        };
        return prevFilters.map(updateBlock);
      });
      const updatedBlock = { ...block, isTrue: true };
      setSaveDialog({ open: true, block: updatedBlock });
      setSaveName("");
      setSaveError("");
    } catch (error) {
      console.error("Error saving block:", error);
      setLocalSaveError("An error occurred while saving. Please try again.");
      setTimeout(() => setLocalSaveError(""), 3000);
    }
  };

  return (
    <>
      {/* Save Block Button (always right-aligned) */}
      {!isCustomBlock || !isCollapsed ? (
        <Button
          size="medium"
          startIcon={<SaveIcon />}
          variant="outlined"
          onClick={handleSaveBlock}
          sx={{
            minHeight: 40, // Match the typical height of a small Select component
            px: 2, // Add some horizontal padding to match Select width better
          }}
        >
          Save Block
        </Button>
      ) : null}
      {localSaveError && (
        <Typography
          variant="caption"
          color="error"
          sx={{ mt: 1, display: "block" }}
        >
          {localSaveError}
        </Typography>
      )}
    </>
  );
};

export default SaveBlockComponent;
