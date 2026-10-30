import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

interface EventInfoRowProps {
  label: string;
  children: React.ReactNode;
}

const EventInfoRow = ({ label, children }: EventInfoRowProps) => (
  <Box sx={{ display: "flex", alignItems: "center", gap: 2, minHeight: 28 }}>
    <Typography
      variant="body2"
      sx={{ width: 120, flexShrink: 0, color: "text.secondary" }}
    >
      {label}
    </Typography>
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 0.5,
        flex: 1,
        minWidth: 0,
      }}
    >
      {children}
    </Box>
  </Box>
);

export default EventInfoRow;
