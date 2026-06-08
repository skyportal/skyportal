import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Typography from "@mui/material/Typography";

import { useGetMMADetectorsQuery } from "../../ducks/mmadetector";

interface MMADetectorListProps {
  isMobile?: boolean;
}

const MMADetectorList = ({ isMobile = false }: MMADetectorListProps) => {
  const { data: mmadetectorList } = useGetMMADetectorsQuery();
  return (
    <List>
      {(mmadetectorList ?? []).map((mmadetector: any) => (
        <ListItem
          key={`${mmadetector.id}_info`}
          sx={{ flexDirection: "column", textAlign: "center" }}
          divider
        >
          <Typography
            variant={(isMobile ? "h7" : "h6") as any}
            sx={{ fontWeight: "400" }}
          >
            {mmadetector.name} ({mmadetector.nickname})
          </Typography>
          <Typography
            variant={isMobile ? "body2" : "body1"}
            color="text.secondary"
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
              color="text.secondary"
            >
              Elevation: {mmadetector.elevation}
            </Typography>
          )}
        </ListItem>
      ))}
    </List>
  );
};

export default MMADetectorList;
