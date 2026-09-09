import { useEffect, useState } from "react";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Tooltip from "@mui/material/Tooltip";
import { alpha } from "@mui/material/styles";

import ErrorIcon from "@mui/icons-material/ErrorOutlineOutlined";
import WarningIcon from "@mui/icons-material/WarningAmberOutlined";
import SuccessIcon from "@mui/icons-material/CheckCircleOutlineOutlined";
import InfoIcon from "@mui/icons-material/InfoOutlined";
import CloseIcon from "@mui/icons-material/Close";

import { PanelEmptyState } from "./HeaderPanel";
import { useAppSelector } from "../types/hooks";

interface Alert {
  id?: string | number;
  note?: string;
  type?: string;
}

export type Severity = "error" | "warning" | "success";

const severityOf = (type?: string): Severity =>
  type === "error" ? "error" : type === "warning" ? "warning" : "success";

const severityIcon = {
  error: <ErrorIcon />,
  warning: <WarningIcon />,
  success: <SuccessIcon />,
};

interface AlertGroup {
  alert: Alert;
  index: number;
  duplicates: number;
}

export const useAlerts = (visible: boolean) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [seenCount, setSeenCount] = useState(0);
  const incoming = useAppSelector(
    (state) => (state as any).notifications.notes,
  ) as Alert[];

  useEffect(() => {
    const unique = new Set(
      [...alerts, ...incoming].filter(
        (alert) => !alert.note?.includes("No WebSocket connection"),
      ),
    );
    setAlerts([...unique]);
  }, [incoming]);

  useEffect(() => {
    if (visible) setSeenCount(alerts.length);
  }, [visible, alerts.length]);

  const groups: AlertGroup[] = [];
  for (const [index, alert] of alerts.entries()) {
    const previous = groups[groups.length - 1];
    if (previous && previous.alert.note === alert.note) {
      previous.duplicates += 1;
      previous.index = index;
    } else {
      groups.push({ alert, index, duplicates: 0 });
    }
  }

  const worstSeverity: Severity = alerts.some((alert) => alert.type === "error")
    ? "error"
    : alerts.some((alert) => alert.type === "warning")
      ? "warning"
      : "success";

  return {
    groups,
    count: alerts.length,
    unseenCount: Math.max(0, alerts.length - seenCount),
    worstSeverity,
    deleteAll: () => setAlerts([]),
    deleteGroup: (lastIndex: number, duplicates: number) =>
      setAlerts(
        alerts.filter(
          (_, index) => index > lastIndex || index < lastIndex - duplicates,
        ),
      ),
  };
};

interface AlertListProps {
  groups: AlertGroup[];
  onDelete: (lastIndex: number, duplicates: number) => void;
}

const AlertList = ({ groups, onDelete }: AlertListProps) => {
  if (groups.length === 0)
    return <PanelEmptyState icon={<InfoIcon />} text="No alerts" />;

  return (
    <List disablePadding>
      {groups.map(({ alert, index, duplicates }, position) => {
        const severity = severityOf(alert.type);
        return (
          <ListItem
            key={alert.id}
            divider={position < groups.length - 1}
            sx={{
              alignItems: "flex-start",
              gap: 1.5,
              px: 2,
              py: 1.5,
              borderLeft: 3,
              borderLeftColor: `${severity}.main`,
              bgcolor: (theme) => alpha(theme.palette[severity].main, 0.14),
            }}
          >
            <Box
              sx={{
                flexShrink: 0,
                display: "flex",
                color: `${severity}.main`,
                "& svg": { fontSize: "1.25rem" },
              }}
            >
              {severityIcon[severity]}
            </Box>
            <Box
              sx={{
                flexGrow: 1,
                minWidth: 0,
                fontSize: "0.875rem",
                lineHeight: 1.45,
                overflowWrap: "anywhere",
              }}
            >
              {alert.note}
            </Box>
            {duplicates > 0 && (
              <Chip
                label={`×${duplicates + 1}`}
                size="small"
                sx={{
                  flexShrink: 0,
                  height: "1.25rem",
                  fontSize: "0.7rem",
                  fontWeight: 600,
                }}
              />
            )}
            <Tooltip title="Delete">
              <IconButton
                size="small"
                data-testid={`deleteNoteButton${alert.id}`}
                onClick={() => onDelete(index, duplicates)}
                sx={{ flexShrink: 0, mt: -0.5, mr: -0.5 }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </ListItem>
        );
      })}
    </List>
  );
};

export default AlertList;
