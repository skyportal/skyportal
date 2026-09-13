import { useMemo } from "react";

import Typography from "@mui/material/Typography";

import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";

interface BrokerFilterPreviewProps {
  previewing: boolean;
  previewError: string | null;
  previewData: unknown;
}

const message = (text: string, color?: string) => (
  <Typography variant="body2" color={color} sx={{ mt: 1 }}>
    {text}
  </Typography>
);

const BrokerFilterPreview = ({
  previewing,
  previewError,
  previewData,
}: BrokerFilterPreviewProps) => {
  const results = Array.isArray(previewData)
    ? (previewData as Record<string, unknown>[])
    : [];

  // Declared before the early returns below so the hook runs on every render.
  const Toolbar = useMemo(
    () =>
      function PreviewToolbar() {
        return (
          <DataGridToolbar
            title={`${results.length} result${results.length !== 1 ? "s" : ""}`}
          />
        );
      },
    [results.length],
  );

  if (previewing) return message("Running preview…");
  if (previewError) return message(previewError, "error");
  if (previewData === undefined) return null;

  const [first] = results;
  if (!first) return message("No results.", "text.secondary");

  const columns = Object.keys(first).map((field) => ({ field, flex: 1 }));
  const rows = results.map((row, index) => ({
    ...Object.fromEntries(
      Object.entries(row).map(([key, value]) => [key, String(value ?? "")]),
    ),
    _rowId: index,
  }));

  return (
    <StyledDataGrid
      autoHeight
      rows={rows}
      columns={columns}
      getRowId={(row: any) => row._rowId}
      initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
      pageSizeOptions={[10, 25, 50]}
      slots={{ toolbar: Toolbar }}
      showToolbar
      sx={{ mt: 2 }}
    />
  );
};

export default BrokerFilterPreview;
