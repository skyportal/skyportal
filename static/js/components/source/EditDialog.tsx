import { ReactNode } from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Typography from "@mui/material/Typography";

import Button from "../Button";
import softButtonsSx from "../softButtons";

interface EditDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  maxWidth?: "xs" | "sm";
  actions?: ReactNode;
  leftAction?: ReactNode;
  children: ReactNode;
}

const EditDialog = ({
  open,
  onClose,
  title,
  description,
  maxWidth = "xs",
  actions,
  leftAction,
  children,
}: EditDialogProps) => (
  <Dialog
    open={open}
    onClose={onClose}
    maxWidth={maxWidth}
    fullWidth
    slotProps={{
      paper: {
        sx: (theme) => ({ borderRadius: "12px", ...softButtonsSx(theme) }),
      },
    }}
  >
    <DialogTitle sx={{ pb: 0 }}>
      {title}
      {description && (
        <Typography
          variant="body2"
          sx={{ color: "text.secondary", fontWeight: 400, mt: 0.5 }}
        >
          {description}
        </Typography>
      )}
    </DialogTitle>
    <DialogContent
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        pt: "1rem !important",
      }}
    >
      {children}
    </DialogContent>
    <DialogActions sx={{ px: 3, pb: 2 }}>
      {leftAction && <Box sx={{ mr: "auto" }}>{leftAction}</Box>}
      <Button onClick={onClose}>{actions ? "Cancel" : "Close"}</Button>
      {actions}
    </DialogActions>
  </Dialog>
);

export const emptyChipSx = { borderStyle: "dashed", color: "text.secondary" };

export default EditDialog;
