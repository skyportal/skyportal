import React from "react";

import {
  QuickFilter as MuiQuickFilter,
  QuickFilterControl,
  QuickFilterClear,
} from "@mui/x-data-grid";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import IconButton from "@mui/material/IconButton";
import SearchIcon from "@mui/icons-material/Search";
import CancelIcon from "@mui/icons-material/Cancel";

// Always-expanded quick-filter search box for the MUI X DataGrid toolbar.
//
// The deprecated `GridToolbarQuickFilter` from @mui/x-data-grid v8 renders an
// *expandable* search: by default the text input is mounted but collapsed
// (opacity: 0, width: var(--trigger-width)) behind a search-icon button, and
// only becomes visible/interactable after the trigger is clicked. Because the
// input is present in the DOM, Selenium can locate it via wait_for_xpath but
// then fails to interact with it ("element could not be scrolled into view" /
// ElementNotInteractableException). This wrapper uses the composable QuickFilter
// API with the `expanded` state controlled to `true` so the input is always
// rendered visible (and never auto-collapses on blur), restoring the
// mui-datatables behavior the frontend tests rely on.
const QuickFilter = () => (
  <MuiQuickFilter expanded>
    <QuickFilterControl
      render={(
        { ref, slotProps: controlSlotProps, ...controlProps },
        state,
      ) => (
        <TextField
          {...controlProps}
          inputRef={ref}
          aria-label="Search"
          placeholder="Search…"
          size="small"
          slotProps={{
            // Preserve the htmlInput props QuickFilterControl sets (searchbox
            // role, control id, blur handler) while adding the search/clear
            // adornments.
            ...controlSlotProps,
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: state.value ? (
                <InputAdornment position="end">
                  <QuickFilterClear
                    render={
                      <IconButton
                        size="small"
                        edge="end"
                        aria-label="Clear search"
                      >
                        <CancelIcon fontSize="small" />
                      </IconButton>
                    }
                  />
                </InputAdornment>
              ) : null,
              ...controlSlotProps?.input,
            },
          }}
        />
      )}
    />
  </MuiQuickFilter>
);

export default QuickFilter;
