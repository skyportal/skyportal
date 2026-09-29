import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

const WidgetLoading = () => (
  <Box
    sx={{
      flex: 1,
      minHeight: "6rem",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <CircularProgress />
  </Box>
);

export default WidgetLoading;
