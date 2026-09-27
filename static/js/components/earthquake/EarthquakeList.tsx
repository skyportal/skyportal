import { Link } from "react-router-dom";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Typography from "@mui/material/Typography";

interface EarthquakeListProps {
  earthquakes: any[];
  isMobile?: boolean;
}

const EarthquakeList = ({
  earthquakes,
  isMobile = false,
}: EarthquakeListProps) => (
  <List>
    {earthquakes.map((earthquake) => {
      const notice = earthquake.notices?.[0];
      return (
        <ListItemButton
          key={earthquake.event_id}
          component={Link}
          to={`/earthquakes/${earthquake.event_id}`}
          sx={{ flexDirection: "column", textAlign: "center" }}
          divider
        >
          <Typography
            variant={(isMobile ? "h7" : "h6") as any}
            sx={{ fontWeight: "400" }}
          >
            {earthquake.event_id}
          </Typography>
          {notice && (
            <>
              <Typography
                variant={isMobile ? "body2" : "body1"}
                sx={{ color: "text.secondary" }}
              >
                {notice.date} / Magnitude: {notice.magnitude}
              </Typography>
              <Typography
                variant={isMobile ? "body2" : "body1"}
                sx={{ color: "text.secondary" }}
              >
                Latitude: {notice.lat?.toFixed(4)} / Longitude:{" "}
                {notice.lon?.toFixed(4)} / Depth: {notice.depth}
              </Typography>
            </>
          )}
        </ListItemButton>
      );
    })}
  </List>
);

export default EarthquakeList;
