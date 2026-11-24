import { ReactNode } from "react";
import Box from "@mui/material/Box";
import Popover from "@mui/material/Popover";

interface EditPopoverProps {
  anchor: HTMLElement | null;
  onClose: () => void;
  title: string;
  width?: string;
  children: ReactNode;
}

const EditPopover = ({
  anchor,
  onClose,
  title,
  width = "22rem",
  children,
}: EditPopoverProps) => (
  <Popover
    open={Boolean(anchor)}
    anchorEl={anchor}
    onClose={onClose}
    anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
  >
    <Box
      sx={{
        width,
        maxWidth: "calc(100vw - 2rem)",
        p: 2,
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
      }}
    >
      <Box sx={{ fontWeight: 600 }}>{title}</Box>
      {children}
    </Box>
  </Popover>
);

export const EditPopoverActions = ({ children }: { children: ReactNode }) => (
  <Box
    sx={{
      display: "flex",
      justifyContent: "flex-end",
      alignItems: "center",
      gap: 1,
    }}
  >
    {children}
  </Box>
);

export default EditPopover;
