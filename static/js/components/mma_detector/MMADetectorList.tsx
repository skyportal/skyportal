import { useState } from "react";

import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Typography from "@mui/material/Typography";

import { useGetMMADetectorsQuery } from "../../ducks/mmadetector";
import MMADetectorEventsDialog from "./MMADetectorEventsDialog";

interface MMADetectorListProps {
  isMobile?: boolean;
}

const MMADetectorList = ({ isMobile = false }: MMADetectorListProps) => {
  const { data: mmadetectorList } = useGetMMADetectorsQuery();
  const [selected, setSelected] = useState<any>(null);
  return (
    <List>
      {(mmadetectorList ?? []).map((mmadetector: any) => (
        <ListItemButton
          key={`${mmadetector.id}_info`}
          sx={{ flexDirection: "column", textAlign: "center" }}
          divider
          onClick={() => setSelected(mmadetector)}
          aria-label={`show gcn events for ${mmadetector.nickname}`}
        >
          <Typography
            variant={(isMobile ? "h7" : "h6") as any}
            sx={{ fontWeight: "400" }}
          >
            {mmadetector.name} ({mmadetector.nickname})
          </Typography>
          <Typography
            variant={isMobile ? "body2" : "body1"}
            sx={{
              color: "text.secondary",
            }}
          >
            {!mmadetector.lat && !mmadetector.lon
              ? "..."
              : `Latitude: ${mmadetector.lat?.toFixed(
                  4,
                )} / Longitude: ${mmadetector.lon?.toFixed(4)}`}
          </Typography>
          {mmadetector.elevation !== null && (
            <Typography
              variant={isMobile ? "body2" : "body1"}
              sx={{
                color: "text.secondary",
              }}
            >
              Elevation: {mmadetector.elevation}
            </Typography>
          )}
        </ListItemButton>
      ))}
      {selected && (
        <MMADetectorEventsDialog
          mmadetector={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </List>
  );
};

export default MMADetectorList;
