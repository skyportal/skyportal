import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

interface BrokerFilterPreviewProps {
  previewing: boolean;
  previewError: string | null;
  previewData: unknown;
}

const BrokerFilterPreview = ({
  previewing,
  previewError,
  previewData,
}: BrokerFilterPreviewProps) => {
  if (previewing) {
    return (
      <Typography variant="body2" sx={{ mt: 1 }}>
        Running preview…
      </Typography>
    );
  }
  if (previewError) {
    return (
      <Typography variant="body2" color="error" sx={{ mt: 1 }}>
        {previewError}
      </Typography>
    );
  }
  const rows = Array.isArray(previewData)
    ? (previewData as Record<string, unknown>[])
    : [];
  if (previewData === undefined) return null;
  if (rows.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
        No results.
      </Typography>
    );
  }
  // rows is non-empty here, but indexing is still possibly-undefined to tsc.
  const cols = Object.keys(rows[0] ?? {});
  return (
    <>
      <Typography variant="body2" sx={{ mt: 2 }}>
        {rows.length} result{rows.length !== 1 ? "s" : ""}
      </Typography>
      <Paper variant="outlined" sx={{ overflowX: "auto", mt: 1 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              {cols.map((c) => (
                <TableCell key={c}>{c}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, i) => (
              <TableRow key={i}>
                {cols.map((c) => (
                  <TableCell key={c}>{String(row[c] ?? "")}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </>
  );
};

export default BrokerFilterPreview;
