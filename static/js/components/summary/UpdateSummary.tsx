import { useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

import Button from "../Button";
import EditPopover, { EditPopoverActions } from "../source/EditPopover";

interface UpdateSummaryProps {
  summary?: string | null | undefined;
  summaryHistory?:
    { summary?: string | null; is_bot?: boolean }[] | null | undefined;
  showAISummaries?: boolean;
  chip?: boolean;
  onSave: (summary: string | null) => Promise<unknown>;
}

const UpdateSummary = ({
  summary,
  summaryHistory,
  showAISummaries = true,
  chip = false,
  onSave,
}: UpdateSummaryProps) => {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);

  const open = (e: React.MouseEvent<HTMLElement | SVGSVGElement>) => {
    setText(
      summaryHistory?.find(
        (s) => s.summary && (showAISummaries || s.is_bot === false),
      )?.summary ?? "",
    );
    setAnchor(e.currentTarget as HTMLElement);
  };

  const save = async (value: string | null) => {
    setSaving(true);
    const saved = await onSave(value).then(
      () => true,
      () => false,
    );
    setSaving(false);
    if (saved) setAnchor(null);
  };

  return (
    <>
      {chip ? (
        <Chip
          size="small"
          variant="outlined"
          label="Add summary"
          onClick={open}
          data-testid="add-summary-button"
          sx={{
            borderStyle: "dashed",
            color: "text.secondary",
            "&:hover": { borderColor: "primary.main", color: "primary.main" },
          }}
        />
      ) : (
        <Tooltip title="Update Summary">
          <EditIcon
            fontSize="small"
            sx={{ height: "1rem", cursor: "pointer" }}
            onClick={open}
          />
        </Tooltip>
      )}
      <EditPopover
        anchor={anchor}
        onClose={() => setAnchor(null)}
        title="Summary"
        width="32rem"
      >
        <TextField
          size="small"
          value={text}
          minRows={4}
          maxRows={14}
          fullWidth
          multiline
          autoFocus
          onChange={(e) => setText(e.target.value)}
        />
        <EditPopoverActions>
          {summary && (
            <Tooltip title="Remove the summary">
              <span>
                <Button
                  secondary
                  size="small"
                  disabled={saving}
                  onClick={() => save(null)}
                >
                  Clear
                </Button>
              </span>
            </Tooltip>
          )}
          <Button
            primary
            size="small"
            disabled={saving || !text.trim()}
            onClick={() => save(text)}
          >
            Save
          </Button>
        </EditPopoverActions>
      </EditPopover>
    </>
  );
};

export default UpdateSummary;
