import { ReactNode } from "react";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";

interface ToggleRowProps {
  checked: boolean;
  name: string;
  onToggle: (checked: boolean) => void;
  title: string;
  text?: ReactNode;
}

const ToggleRow = ({
  checked,
  name,
  onToggle,
  title,
  text,
}: ToggleRowProps) => (
  <Box
    onClick={() => onToggle(!checked)}
    sx={{
      display: "flex",
      alignItems: "center",
      gap: 1,
      padding: "0.5rem 0.5rem 0.5rem 0.125rem",
      borderRadius: 1.5,
      cursor: "pointer",
      userSelect: "none",
      "&:hover": { backgroundColor: "action.hover" },
    }}
  >
    <Checkbox
      checked={checked}
      name={name}
      onClick={(event) => event.stopPropagation()}
      onChange={(event) => onToggle(event.target.checked)}
      icon={<RadioButtonUncheckedIcon />}
      checkedIcon={<CheckCircleIcon />}
      sx={{ padding: 0.5, color: "action.active" }}
    />
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
        {title}
      </Typography>
      {text && (
        <Typography
          variant="caption"
          color="textSecondary"
          component="div"
          sx={{ lineHeight: 1.3 }}
        >
          {text}
        </Typography>
      )}
    </Box>
  </Box>
);

export default ToggleRow;
