import { lazy, Suspense, useState } from "react";
import { Box, Tooltip, IconButton } from "@mui/material";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import ReplayIcon from "@mui/icons-material/Replay";

import { useGetTelescopesQuery } from "../../ducks/telescopes";
import WidgetCard from "./WidgetCard";
import WidgetLoading from "./WidgetLoading";

const TelescopeMap = lazy(() => import("../telescope/TelescopeMap"));

const LEGEND = [
  { label: "Daytime", color: "#f9d71c", radius: "50%" },
  { label: "Nighttime", color: "#0c1445", radius: "50%" },
  {
    label: "Networks and space-based instruments",
    color: "#5ca9d6",
    radius: 0,
  },
];

const Legend = () => (
  <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, p: 0.5 }}>
    {LEGEND.map(({ label, color, radius }) => (
      <Box key={label} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Box
          sx={{ width: 14, height: 14, borderRadius: radius, bgcolor: color }}
        />
        {label}
      </Box>
    ))}
  </Box>
);

const TelescopeMapWidget = () => {
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const [mapKey, setMapKey] = useState(0);

  return (
    <WidgetCard
      title="Telescopes"
      actions={
        <>
          <Tooltip title="Reset view">
            <IconButton size="small" onClick={() => setMapKey((k) => k + 1)}>
              <ReplayIcon fontSize="small" sx={{ color: "text.secondary" }} />
            </IconButton>
          </Tooltip>
          <Tooltip title={<Legend />} placement="bottom-end">
            <IconButton size="small" aria-label="Legend">
              <HelpOutlineOutlinedIcon
                fontSize="small"
                sx={{ color: "text.secondary" }}
              />
            </IconButton>
          </Tooltip>
        </>
      }
      bodySx={{ p: 0, overflow: "hidden" }}
    >
      <Box sx={{ position: "relative", height: "100%", overflow: "hidden" }}>
        <Suspense fallback={<WidgetLoading />}>
          <TelescopeMap key={mapKey} telescopes={telescopeList} />
        </Suspense>
      </Box>
    </WidgetCard>
  );
};

export default TelescopeMapWidget;
