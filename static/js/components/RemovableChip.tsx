import CancelIcon from "@mui/icons-material/Cancel";
import Chip, { ChipProps } from "@mui/material/Chip";

// Chip for a Select's renderValue whose cross removes the value without opening the menu.
// The cross collapses until hover where the device can hover, so the chip fits its label.
const RemovableChip = ({ sx, ...props }: ChipProps) => (
  <Chip
    {...props}
    deleteIcon={<CancelIcon onMouseDown={(event) => event.stopPropagation()} />}
    sx={[
      {
        "@media (hover: hover)": {
          "&:not(:hover):not(.Mui-focusVisible) .MuiChip-deleteIcon": {
            width: 0,
            margin: 0,
            opacity: 0,
          },
          "& .MuiChip-deleteIcon": {
            transition: "width 0.15s, margin 0.15s, opacity 0.15s",
          },
        },
      },
      ...(Array.isArray(sx) ? sx : [sx]),
    ]}
  />
);

export default RemovableChip;
