import { useState } from "react";
import { IconButton, Tooltip, Typography } from "@mui/material";
import BookmarkAddIcon from "@mui/icons-material/BookmarkAddOutlined";

interface SaveBlockComponentProps {
  setSaveDialog: (...a: any[]) => void;
  setSaveName: (...a: any[]) => void;
  setSaveError: (...a: any[]) => void;
  setFilters: (...a: any[]) => void;
  isCustomBlock?: boolean | undefined;
  isCollapsed?: boolean | undefined;
  block: any;
}

const isComplete = (b: any): boolean => {
  if (b.category === "block") {
    return b.children.length > 0 && b.children.every(isComplete);
  }
  if (b.category !== "condition") return false;
  if (b.isListVariable) return !!b.field;
  if (
    ["$exists", "$isNumber", "$anyElementTrue", "$allElementsTrue"].includes(
      b.operator,
    )
  ) {
    return true;
  }
  return !!b.field && !!b.operator && b.value !== "" && b.value != null;
};

const SaveBlockComponent = ({
  setSaveDialog,
  setSaveName,
  setSaveError,
  setFilters,
  isCustomBlock,
  isCollapsed,
  block,
}: SaveBlockComponentProps) => {
  const [showError, setShowError] = useState(false);

  const handleSaveBlock = () => {
    if (!isComplete(block)) {
      setShowError(true);
      setTimeout(() => setShowError(false), 3000);
      return;
    }
    const markTrue = (b: any): any =>
      b.id === block.id
        ? { ...b, isTrue: true }
        : {
            ...b,
            children: (b.children ?? []).map((child: any) =>
              child.category === "block" ? markTrue(child) : child,
            ),
          };
    setFilters((prevFilters: any[]) => prevFilters.map(markTrue));
    setSaveDialog({ open: true, block: { ...block, isTrue: true } });
    setSaveName("");
    setSaveError("");
  };

  return (
    <>
      {(!isCustomBlock || !isCollapsed) && (
        <Tooltip
          describeChild
          title="Save this block as a reusable custom block, to insert in any filter from Add. It does not save the filter."
        >
          <IconButton
            size="small"
            aria-label="Save as a custom block"
            onClick={handleSaveBlock}
          >
            <BookmarkAddIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
      {showError && (
        <Typography
          variant="caption"
          color="error"
          sx={{ mt: 1, display: "block" }}
        >
          Please fill all fields before saving.
        </Typography>
      )}
    </>
  );
};

export default SaveBlockComponent;
