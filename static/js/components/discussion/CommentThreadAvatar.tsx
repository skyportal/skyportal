import { ReactNode } from "react";

import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import LandslideIcon from "@mui/icons-material/Landslide";
import SettingsInputAntennaIcon from "@mui/icons-material/SettingsInputAntenna";
import StorageIcon from "@mui/icons-material/Storage";
import Avatar from "@mui/material/Avatar";
import { deepOrange, deepPurple, brown, teal } from "@mui/material/colors";

import type { CommentThread } from "../../ducks/discussions";

export const RESOURCES: Record<
  CommentThread["resource_type"],
  { name: string; color: string; icon: ReactNode }
> = {
  sources: { name: "Source", color: teal[600], icon: <StorageIcon /> },
  gcn_event: {
    name: "GCN event",
    color: deepOrange[500],
    icon: <SettingsInputAntennaIcon />,
  },
  earthquake: {
    name: "Earthquake",
    color: brown[400],
    icon: <LandslideIcon />,
  },
  shift: { name: "Shift", color: deepPurple[400], icon: <CalendarMonthIcon /> },
};

const CommentThreadAvatar = ({
  type,
  size,
}: {
  type: CommentThread["resource_type"];
  size: number;
}) => {
  const { color, icon } = RESOURCES[type];
  return (
    <Avatar
      sx={{
        width: size,
        height: size,
        bgcolor: color,
        color: "common.white",
        "& svg": { fontSize: size * 0.5 },
      }}
    >
      {icon}
    </Avatar>
  );
};

export default CommentThreadAvatar;
