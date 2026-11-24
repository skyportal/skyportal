import { alpha, type Theme } from "@mui/material/styles";

const softButtonsSx = (theme: Theme) => ({
  "& .MuiButton-root": {
    textTransform: "none",
    fontWeight: 500,
    fontSize: "0.85rem",
    borderRadius: "8px",
    px: 1.5,
    boxShadow: "none",
  },
  "& .MuiButton-endIcon": { ml: 0.25, mr: -0.5 },
  "& .MuiButton-colorGrey:not(.Mui-disabled)": {
    bgcolor: alpha(theme.palette.text.primary, 0.06),
    color: "text.primary",
    "&:hover": { bgcolor: alpha(theme.palette.text.primary, 0.11) },
  },
});

export default softButtonsSx;
