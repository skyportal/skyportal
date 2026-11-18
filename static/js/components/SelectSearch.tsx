import { useState } from "react";
import ListSubheader from "@mui/material/ListSubheader";
import TextField from "@mui/material/TextField";

export const matchesSearch = (label: unknown, search: string) => {
  const text = String(label ?? "").toLowerCase();
  return search
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((token) => text.includes(token));
};

export const useSelectSearch = (testId?: string) => {
  const [search, setSearch] = useState("");

  const searchHeader = (
    <ListSubheader sx={{ p: 1, lineHeight: "unset" }}>
      <TextField
        size="small"
        autoFocus
        fullWidth
        placeholder="Search..."
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        slotProps={{
          htmlInput: testId ? { "data-testid": testId } : {},
        }}
        onKeyDown={(event) => {
          if (event.key !== "Escape") {
            event.stopPropagation();
          }
        }}
      />
    </ListSubheader>
  );

  return {
    searchHeader,
    matches: (label: unknown) => matchesSearch(label, search),
    resetSearch: () => setSearch(""),
  };
};
