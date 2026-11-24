import { styled } from "@mui/material/styles";

const FieldLabel = styled("span")(({ theme }) => ({
  color: theme.palette.text.secondary,
  fontWeight: 500,
  marginRight: theme.spacing(0.75),
  whiteSpace: "nowrap",
}));

export default FieldLabel;
