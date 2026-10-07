import {
  Dialog,
  DialogTitle,
  DialogContent,
  Typography,
  Box,
  IconButton,
  Chip,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Paper,
} from "@mui/material";
import {
  Close as CloseIcon,
  Download as DownloadIcon,
} from "@mui/icons-material";
import ReactJson from "react-json-view";

interface FullscreenResultsDialogProps {
  isFullscreen: boolean;
  setIsFullscreen: (...a: any[]) => void;
  displayResults: { data?: any[] };
  summary: string;
  expandedCells: Set<any>;
  handleDownloadResults: (...a: any[]) => void;
}

const FullscreenResultsDialog = ({
  isFullscreen,
  setIsFullscreen,
  displayResults,
  summary,
  expandedCells,
  handleDownloadResults,
}: FullscreenResultsDialogProps) => {
  return (
    <Dialog
      open={isFullscreen}
      onClose={() => setIsFullscreen(false)}
      maxWidth={false}
      fullScreen
      sx={{
        "& .MuiDialog-paper": {
          margin: 0,
          maxHeight: "100vh",
          height: "100vh",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          pb: 1,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="h6">Query Results</Typography>
          <Chip
            label={summary}
            size="small"
            color={displayResults.data?.length ? "success" : "default"}
          />
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <IconButton
            onClick={handleDownloadResults}
            disabled={!displayResults.data?.length}
            title="Download results as JSON"
            sx={{ color: "text.secondary" }}
          >
            <DownloadIcon />
          </IconButton>
          <IconButton
            onClick={() => setIsFullscreen(false)}
            sx={{ color: "text.secondary" }}
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent
        sx={{
          p: 0,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          height: "100%",
        }}
      >
        {(displayResults.data?.length ?? 0) > 0 ? (
          <TableContainer
            component={Paper}
            sx={{
              flex: 1,
              overflow: "auto",
              "& .MuiTable-root": { minWidth: 650 },
            }}
          >
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  {Object.keys(displayResults.data?.[0] || {})
                    .filter((key) => key !== "_id")
                    .map((key) => (
                      <TableCell
                        key={key}
                        sx={{
                          fontWeight: "bold",
                          backgroundColor: "grey.100",
                          whiteSpace: "nowrap",
                          minWidth: 120,
                        }}
                      >
                        {key}
                      </TableCell>
                    ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {displayResults.data?.map((row: any, rowIndex: number) => (
                  <TableRow
                    key={rowIndex}
                    sx={{
                      height: "auto",
                      minHeight: "fit-content",
                      "& .MuiTableCell-root": {
                        height: "auto",
                        minHeight: "fit-content",
                      },
                    }}
                  >
                    {Object.keys(row)
                      .filter((key) => key !== "_id")
                      .map((key) => {
                        const value = row[key];
                        const cellKey = `${rowIndex}-${key}`;
                        const isExpanded = expandedCells.has(cellKey);
                        return (
                          <TableCell
                            key={key}
                            sx={{
                              verticalAlign: "top",
                              height: "auto",
                              minHeight: "fit-content",
                            }}
                          >
                            {value === null || value === undefined ? (
                              <Typography
                                variant="body2"
                                sx={{
                                  wordBreak: "break-word",
                                  whiteSpace: "pre-wrap",
                                  fontStyle: "italic",
                                  color: "text.secondary",
                                }}
                              >
                                {value === null ? "null" : "undefined"}
                              </Typography>
                            ) : typeof value === "object" ? (
                              (() => {
                                try {
                                  JSON.stringify(value);
                                  return (
                                    <Box
                                      sx={{
                                        maxWidth: 300,
                                        maxHeight: isExpanded ? "none" : 100,
                                        overflow: isExpanded
                                          ? "visible"
                                          : "hidden",
                                        position: "relative",
                                        minHeight: "fit-content",
                                        height: "auto",
                                        "& .react-json-view": {
                                          height: "auto !important",
                                          minHeight: "fit-content",
                                        },
                                      }}
                                    >
                                      <ReactJson
                                        src={value}
                                        theme="rjv-default"
                                        collapsed={
                                          key === "annotations"
                                            ? false
                                            : !isExpanded
                                        }
                                        displayDataTypes={false}
                                        displayObjectSize={false}
                                        enableClipboard={false}
                                        name={false}
                                        style={{
                                          fontSize: "12px",
                                          lineHeight: "1.4",
                                          height: "auto",
                                          minHeight: "fit-content",
                                        }}
                                      />
                                    </Box>
                                  );
                                } catch (error) {
                                  return (
                                    <Typography
                                      variant="body2"
                                      sx={{
                                        wordBreak: "break-word",
                                        whiteSpace: "pre-wrap",
                                        color: "error.main",
                                      }}
                                    >
                                      {`[Invalid Object: ${(error as any).message}]`}
                                    </Typography>
                                  );
                                }
                              })()
                            ) : (
                              <Typography
                                variant="body2"
                                sx={{
                                  wordBreak: "break-word",
                                  whiteSpace: "pre-wrap",
                                }}
                              >
                                {String(value)}
                              </Typography>
                            )}
                          </TableCell>
                        );
                      })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography variant="body1" color="text.secondary">
              No results to display
            </Typography>
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default FullscreenResultsDialog;
