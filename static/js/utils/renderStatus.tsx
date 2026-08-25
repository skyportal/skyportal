import Box from "@mui/material/Box";

import { STATUS_COLORS } from "./constants";

export const renderStatus = (item: any) => {
  if (!item?.status) return null;
  const match = Object.keys(STATUS_COLORS).find((key) =>
    item.status.startsWith(key),
  );
  const color =
    (STATUS_COLORS as Record<string, string>)[match ?? ""] || "grey";
  return (
    <Box
      sx={{
        backgroundColor: color,
        color: "white",
        padding: "0.4rem 0.7rem",
        borderRadius: "1rem",
        width: "fit-content",
        // errors can be long: only they are allowed to wrap
        whiteSpace: item.status.includes("error") ? "normal" : "nowrap",
      }}
    >
      {item.status}
    </Box>
  );
};
