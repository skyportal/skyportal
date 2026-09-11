import { ReactNode, useEffect } from "react";

import Box from "@mui/material/Box";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Divider from "@mui/material/Divider";
import Paper from "@mui/material/Paper";
import Popper from "@mui/material/Popper";
import Typography from "@mui/material/Typography";

const POPPER_MODIFIERS = [
  { name: "offset", options: { offset: [0, 8] } },
  { name: "preventOverflow", options: { padding: 8 } },
];

interface HeaderPanelProps {
  anchorEl: HTMLElement | null;
  onClose: () => void;
  header: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}

const HeaderPanel = ({
  anchorEl,
  onClose,
  header,
  actions,
  children,
}: HeaderPanelProps) => {
  const open = Boolean(anchorEl);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  return (
    <Popper
      open={open}
      anchorEl={anchorEl}
      placement="bottom"
      modifiers={POPPER_MODIFIERS}
      sx={{ zIndex: (theme) => theme.zIndex.modal }}
    >
      <ClickAwayListener onClickAway={onClose}>
        <Paper
          elevation={8}
          sx={{
            borderRadius: 2,
            width: "26rem",
            maxWidth: "calc(100vw - 1rem)",
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              pr: 1.5,
              bgcolor: "action.hover",
            }}
          >
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>{header}</Box>
            {actions}
          </Box>
          <Divider />
          <Box sx={{ maxHeight: "60vh", overflowY: "auto" }}>{children}</Box>
        </Paper>
      </ClickAwayListener>
    </Popper>
  );
};

export const PanelEmptyState = ({
  icon,
  text,
}: {
  icon: ReactNode;
  text: string;
}) => (
  <Box
    sx={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: 1,
      px: 3,
      py: 4,
      color: "text.disabled",
    }}
  >
    {icon}
    <Typography variant="body2" color="text.secondary">
      {text}
    </Typography>
  </Box>
);

export default HeaderPanel;
