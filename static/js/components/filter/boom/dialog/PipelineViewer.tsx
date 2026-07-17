import {
  Box,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Collapse,
  Paper,
  Chip,
  Tooltip,
  Button,
} from "@mui/material";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  ContentCopy as CopyIcon,
} from "@mui/icons-material";
import ReactJson from "react-json-view";

const STAGE_DESCRIPTIONS: Record<string, string> = {
  $match:
    "Filters documents to pass only those that match the specified condition(s)",
  $project: "Reshapes documents by including, excluding, or adding new fields",
  $lookup: "Performs a left outer join to documents from another collection",
  $unwind: "Deconstructs an array field to output a document for each element",
  $group:
    "Groups documents by a specified identifier and applies aggregation functions",
  $sort: "Sorts documents by specified field(s)",
  $limit: "Limits the number of documents passed to the next stage",
  $skip: "Skips a specified number of documents",
  $addFields: "Adds new fields to documents",
  $replaceRoot: "Replaces the input document with the specified document",
  $facet: "Processes multiple aggregation pipelines within a single stage",
  $bucket: "Categorizes documents into groups based on specified boundaries",
  $size: "Returns a count of the number of documents at this stage",
  $out: "Writes the resulting documents to a collection",
  $merge:
    "Writes the results of the aggregation pipeline to a specified collection",
  $filter: "Filters array elements based on specified criteria",
  $map: "Applies an expression to each element in an array",
  $reduce:
    "Applies an expression to each element in an array and combines them",
};

interface PipelineViewerProps {
  pipeline: any[];
  showPipeline: boolean;
  setShowPipeline: (...a: any[]) => void;
  pipelineView: string;
  setPipelineView: (...a: any[]) => void;
  expandedStages: Set<any>;
  handleStageToggle: (...a: any[]) => void;
  handleCopy: (...a: any[]) => void;
  handleCopyStage: (...a: any[]) => void;
}

const PipelineViewer = ({
  pipeline,
  showPipeline,
  setShowPipeline,
  pipelineView,
  setPipelineView,
  expandedStages,
  handleStageToggle,
  handleCopy,
  handleCopyStage,
}: PipelineViewerProps) => (
  <Box sx={{ mb: 3 }}>
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
      <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>
        MongoDB Pipeline ({pipeline.length} stage
        {pipeline.length !== 1 ? "s" : ""})
      </Typography>
      <IconButton size="small" onClick={() => setShowPipeline(!showPipeline)}>
        {showPipeline ? <ExpandLessIcon /> : <ExpandMoreIcon />}
      </IconButton>
    </Box>

    <Collapse in={showPipeline}>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
        <Tabs
          value={pipelineView}
          onChange={(_e: any, newValue: any) => setPipelineView(newValue)}
          aria-label="pipeline view tabs"
        >
          <Tab
            label="Complete Pipeline"
            value="complete"
            sx={{ textTransform: "none" }}
          />
          <Tab
            label="Stage by Stage"
            value="stages"
            sx={{ textTransform: "none" }}
          />
        </Tabs>
      </Box>

      <Box
        sx={{
          minHeight: "400px",
          position: "relative",
          backgroundColor: "background.paper",
        }}
      >
        {pipelineView === "complete" && (
          <Box
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              minHeight: "100%",
              backgroundColor: "background.paper",
            }}
          >
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 2,
              }}
            >
              <Typography variant="subtitle2" sx={{ fontWeight: "bold" }}>
                Complete Pipeline JSON:
              </Typography>
              <Button
                variant="outlined"
                size="small"
                startIcon={<CopyIcon />}
                onClick={handleCopy}
              >
                Copy to Clipboard
              </Button>
            </Box>
            <Box
              sx={{
                backgroundColor: "#f5f5f5",
                border: "1px solid #ddd",
                borderRadius: 1,
                p: 2,
                maxHeight: "400px",
                overflow: "auto",
              }}
            >
              <ReactJson src={pipeline} name={false} />
            </Box>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ mt: 2, display: "block" }}
            >
              This aggregation pipeline can be used directly with MongoDB&apos;s
              aggregate() method.
            </Typography>
          </Box>
        )}

        {pipelineView === "stages" && (
          <Box
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              minHeight: "100%",
              backgroundColor: "background.paper",
            }}
          >
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {pipeline.map((stage: any, index: number) => {
                const stageName = Object.keys(stage)[0] ?? "";
                const stageContent = stage[stageName];
                const description =
                  STAGE_DESCRIPTIONS[stageName] || "MongoDB aggregation stage";
                const isStageExpanded = expandedStages.has(index);
                return (
                  <Paper
                    key={index}
                    elevation={1}
                    sx={{ p: 2, border: "1px solid", borderColor: "divider" }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        mb: 1,
                      }}
                    >
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <Chip
                          label={`Stage ${index + 1}`}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                        <Typography
                          variant="h6"
                          sx={{
                            color: "primary.main",
                            fontFamily: "monospace",
                          }}
                        >
                          {stageName}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => handleStageToggle(index)}
                          sx={{ ml: 1 }}
                        >
                          {isStageExpanded ? (
                            <ExpandLessIcon />
                          ) : (
                            <ExpandMoreIcon />
                          )}
                        </IconButton>
                      </Box>
                      <Tooltip title={`Copy ${stageName} stage`}>
                        <IconButton
                          size="small"
                          onClick={() =>
                            handleCopyStage(stageName, stageContent)
                          }
                          sx={{ opacity: 0.7, "&:hover": { opacity: 1 } }}
                        >
                          <CopyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mb: 2, fontStyle: "italic" }}
                    >
                      {description}
                    </Typography>
                    <Collapse in={isStageExpanded}>
                      <Box
                        component="pre"
                        sx={{
                          backgroundColor: "#f8f9fa",
                          border: "1px solid #e9ecef",
                          borderRadius: 1,
                          p: 1.5,
                          overflow: "auto",
                          maxHeight: "300px",
                          fontFamily:
                            'Monaco, Consolas, "Courier New", monospace',
                          fontSize: "13px",
                          lineHeight: 1.4,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          margin: 0,
                        }}
                      >
                        {JSON.stringify(stageContent, null, 2)}
                      </Box>
                    </Collapse>
                  </Paper>
                );
              })}
            </Box>
          </Box>
        )}
      </Box>
    </Collapse>
  </Box>
);

export default PipelineViewer;
