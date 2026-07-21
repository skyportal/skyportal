import { Popover, Paper } from "@mui/material";
import "katex/dist/katex.min.css";
import Latex from "react-latex-next";

interface EquationPopoverProps {
  open: boolean;
  anchorEl?: any;
  onClose: (...a: any[]) => void;
  variableName?: string;
  customVariables: any[];
}

const escapeLatexForDisplay = (text: any) => {
  if (!text) return text;
  return text.replace(/_/g, "\\_");
};

const EquationPopover = ({
  open,
  anchorEl,
  onClose,
  variableName,
  customVariables,
}: EquationPopoverProps) => {
  if (!open || !anchorEl || !variableName) return null;

  const eqObj = customVariables.find(
    (eq: any) => eq.variable === variableName || eq.name === variableName,
  );
  const equation = eqObj ? eqObj.variable : null;

  if (!equation) return null;

  const displayEquation = escapeLatexForDisplay(equation);

  return (
    <Popover
      open={open}
      anchorEl={anchorEl}
      onClose={onClose}
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
        <Latex>{`$$${displayEquation}$$`}</Latex>
      </Paper>
    </Popover>
  );
};

export default EquationPopover;
