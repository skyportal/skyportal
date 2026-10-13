import CancelIcon from "@mui/icons-material/Cancel";
import Chip, { ChipProps } from "@mui/material/Chip";

// Chip for a Select's renderValue whose cross removes the value without opening the menu.
const RemovableChip = (props: ChipProps) => (
  <Chip
    {...props}
    deleteIcon={<CancelIcon onMouseDown={(event) => event.stopPropagation()} />}
  />
);

export default RemovableChip;
