import { useState } from "react";
import { Link } from "react-router-dom";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";

import Button from "../Button";
import EditDialog from "../source/EditDialog";
import { latestSummary } from "./ShowSummaries";
import { useGetUsersQuery } from "../../ducks/users";

interface SummaryHistoryItem {
  summary?: string | null;
  is_bot?: boolean;
  set_by_user_id?: number;
  set_at_utc?: string;
  analysis_id?: number;
}

interface SummaryHistoryListProps {
  items: SummaryHistoryItem[];
  objId?: string | undefined;
}

const SummaryHistoryList = ({ items, objId }: SummaryHistoryListProps) => {
  const users = useGetUsersQuery({ slim: true }).data?.users;
  return (
    <Box sx={{ maxHeight: "60vh", overflowY: "auto" }}>
      {items.map((item, index) => {
        const username = users?.find(
          (user: any) => user.id === item.set_by_user_id,
        )?.username;
        const showAnalysisLink =
          item.is_bot && objId && typeof item.analysis_id === "number";
        return (
          <Box
            key={`${item.set_at_utc}-${index}`}
            sx={{
              py: 1.25,
              "& + &": { borderTop: 1, borderColor: "divider" },
            }}
          >
            {item.summary?.trim() ? (
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                {item.summary}
              </Typography>
            ) : (
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", fontStyle: "italic" }}
              >
                Cleared
              </Typography>
            )}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                mt: 0.5,
                color: "text.secondary",
                fontSize: "0.75rem",
              }}
            >
              {item.is_bot && (
                <SmartToyOutlinedIcon sx={{ fontSize: "0.9rem" }} />
              )}
              {username ?? (item.is_bot ? "AI" : users ? "a deleted user" : "")}
              {item.set_at_utc &&
                ` · ${dayjs(item.set_at_utc).format("YYYY-MM-DD HH:mm")}`}
              {showAnalysisLink && (
                <Box
                  component={Link}
                  to={`/source/${objId}/analysis/${item.analysis_id}`}
                  sx={{ ml: 0.5, color: "primary.main" }}
                >
                  analysis
                </Box>
              )}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
};

interface UpdateSummaryProps {
  summary?: string | null | undefined;
  summaryHistory?: SummaryHistoryItem[] | null | undefined;
  showAISummaries?: boolean;
  chip?: boolean;
  objId?: string | undefined;
  onSave: (summary: string | null) => Promise<unknown>;
}

const UpdateSummary = ({
  summary,
  summaryHistory,
  showAISummaries = true,
  chip = false,
  objId,
  onSave,
}: UpdateSummaryProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [tab, setTab] = useState<"edit" | "history">("edit");
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const history = summaryHistory ?? [];

  const open = (nextTab: "edit" | "history") => {
    setMenuAnchor(null);
    setText(latestSummary(summaryHistory, showAISummaries) ?? "");
    setTab(nextTab);
    setDialogOpen(true);
  };

  const save = async (value: string | null) => {
    setSaving(true);
    const saved = await onSave(value).then(
      () => true,
      () => false,
    );
    setSaving(false);
    if (saved) setDialogOpen(false);
  };

  const editing = tab === "edit";

  return (
    <>
      {chip ? (
        <Chip
          size="small"
          variant="outlined"
          label="Add summary"
          onClick={() => open("edit")}
          data-testid="add-summary-button"
          sx={{
            borderStyle: "dashed",
            color: "text.secondary",
            "&:hover": { borderColor: "primary.main", color: "primary.main" },
          }}
        />
      ) : (
        <>
          <IconButton
            size="small"
            aria-label="Summary options"
            data-testid="summary-menu-button"
            onClick={(event) => setMenuAnchor(event.currentTarget)}
            sx={{ color: "text.secondary" }}
          >
            <MoreVertIcon fontSize="small" />
          </IconButton>
          <Menu
            anchorEl={menuAnchor}
            open={Boolean(menuAnchor)}
            onClose={() => setMenuAnchor(null)}
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            transformOrigin={{ vertical: "top", horizontal: "right" }}
          >
            <MenuItem dense onClick={() => open("edit")}>
              Edit
            </MenuItem>
            {history.length > 0 && (
              <MenuItem dense onClick={() => open("history")}>
                History
              </MenuItem>
            )}
          </Menu>
        </>
      )}
      <EditDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title="Summary"
        maxWidth="sm"
        leftAction={
          editing &&
          summary && (
            <Button secondary disabled={saving} onClick={() => save(null)}>
              Clear
            </Button>
          )
        }
        actions={
          editing && (
            <Button
              primary
              disabled={saving || !text.trim()}
              onClick={() => save(text)}
            >
              Save
            </Button>
          )
        }
      >
        {history.length > 0 && (
          <Tabs
            value={tab}
            onChange={(_, value) => setTab(value)}
            sx={{
              minHeight: 36,
              mt: -1,
              borderBottom: 1,
              borderColor: "divider",
              "& .MuiTab-root": { minHeight: 36, py: 0.5 },
            }}
          >
            <Tab value="edit" label="Edit" />
            <Tab value="history" label={`History (${history.length})`} />
          </Tabs>
        )}
        {editing ? (
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
        ) : (
          <SummaryHistoryList items={history} objId={objId} />
        )}
      </EditDialog>
    </>
  );
};

export default UpdateSummary;
