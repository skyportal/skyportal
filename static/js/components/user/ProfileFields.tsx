import { ReactNode } from "react";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

dayjs.extend(utc);

export const field = (label: ReactNode, value: ReactNode) => (
  <Typography variant="body2" component="div">
    <b>{label}:</b> {value}
  </Typography>
);

export const chips = (values: string[]) => (
  <Box
    component="span"
    sx={{ display: "inline-flex", flexWrap: "wrap", gap: 0.5 }}
  >
    {values.map((value) => (
      <Chip key={value} label={value} size="small" />
    ))}
  </Box>
);

export const memberSince = (createdAt: string) =>
  dayjs.utc(`${createdAt}Z`).format("MMMM D, YYYY");
