import { DragEvent, useState } from "react";
import { Box, Tooltip } from "@mui/material";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";

import { dropItem } from "./blockTree";

const DRAG_TYPE = "application/x-boom-filter-item";
let draggedId: string | null = null;

export type DropPosition = "before" | "after" | "into" | null;

export const DragHandle = ({ itemId, sx }: { itemId: string; sx?: any }) => (
  <Tooltip title="Drag to move, hold Alt to copy">
    <Box
      component="span"
      draggable
      aria-label="Drag to move, hold Alt to copy"
      onDragStart={(e: DragEvent<HTMLElement>) => {
        e.stopPropagation();
        draggedId = itemId;
        e.dataTransfer.setData(DRAG_TYPE, itemId);
        e.dataTransfer.effectAllowed = "copyMove";
        const item = e.currentTarget.closest("[data-filter-item]");
        if (item) e.dataTransfer.setDragImage(item, 0, 0);
      }}
      onDragEnd={() => {
        draggedId = null;
      }}
      sx={{
        display: "flex",
        cursor: "grab",
        color: "text.disabled",
        "&:hover": { color: "text.secondary" },
        ...sx,
      }}
    >
      <DragIndicatorIcon fontSize="small" />
    </Box>
  </Tooltip>
);

interface DropTargetOptions {
  filters: any[];
  setFilters: (...a: any[]) => void;
  parentBlockId: string | null;
  anchorId: string;
  positionAt: (e: DragEvent<HTMLElement>) => DropPosition;
}

export const halfPosition = (e: DragEvent<HTMLElement>): DropPosition => {
  const rect = e.currentTarget.getBoundingClientRect();
  return e.clientY < rect.top + rect.height / 2 ? "before" : "after";
};

export const edgePosition = (e: DragEvent<HTMLElement>): DropPosition => {
  const rect = e.currentTarget.getBoundingClientRect();
  if (e.clientY < rect.top + 10) return "before";
  if (e.clientY > rect.bottom - 10) return "after";
  return "into";
};

export const useDropTarget = ({
  filters,
  setFilters,
  parentBlockId,
  anchorId,
  positionAt,
}: DropTargetOptions) => {
  const [position, setPosition] = useState<DropPosition>(null);

  const accepts = (e: DragEvent<HTMLElement>) =>
    !!draggedId && e.dataTransfer.types.includes(DRAG_TYPE);

  const resolve = (e: DragEvent<HTMLElement>): DropPosition => {
    const at = positionAt(e);
    return at !== "into" && !parentBlockId ? "into" : at;
  };

  const dropProps = {
    "data-filter-item": anchorId,
    onDragOver: (e: DragEvent<HTMLElement>) => {
      if (!accepts(e)) return;
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = e.altKey ? "copy" : "move";
      const at = resolve(e);
      if (at !== position) setPosition(at);
    },
    onDragLeave: (e: DragEvent<HTMLElement>) => {
      if (!e.currentTarget.contains(e.relatedTarget as Node)) {
        setPosition(null);
      }
    },
    onDrop: (e: DragEvent<HTMLElement>) => {
      setPosition(null);
      if (!accepts(e)) return;
      e.preventDefault();
      e.stopPropagation();
      const at = resolve(e);
      const itemId = draggedId as string;
      draggedId = null;
      setFilters(
        at === "into"
          ? dropItem(filters, itemId, anchorId, null, false, e.altKey)
          : dropItem(
              filters,
              itemId,
              parentBlockId as string,
              anchorId,
              at === "after",
              e.altKey,
            ),
      );
    },
  };

  return { position, dropProps };
};

export const dropIndicatorSx = (position: DropPosition) => {
  if (position === "into") {
    return { outline: 2, outlineStyle: "dashed", outlineColor: "primary.main" };
  }
  if (!position) return {};
  return {
    "&::after": {
      content: '""',
      position: "absolute",
      left: 0,
      right: 0,
      [position === "before" ? "top" : "bottom"]: -4,
      height: 3,
      borderRadius: 1,
      bgcolor: "primary.main",
      pointerEvents: "none",
      zIndex: 4,
    },
  };
};
