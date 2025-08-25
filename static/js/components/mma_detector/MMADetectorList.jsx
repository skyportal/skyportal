import React from "react";
import { useSelector } from "react-redux";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Typography from "@mui/material/Typography";

const MMADetectorList = () => {
  const { mmadetectorList } = useSelector((state) => state.mmadetectors);
  return (
    <List>
      {mmadetectorList.map((mmadetector) => (
        <ListItem
          key={`${mmadetector.id}_info`}
          sx={{ flexDirection: "column", textAlign: "center" }}
          divider
        >
          <Typography variant="h6" sx={{ fontWeight: "400" }}>
            {mmadetector.name} ({mmadetector.nickname})
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {!mmadetector.lat && !mmadetector.lon
              ? "..."
              : `Latitude: ${mmadetector.lat?.toFixed(
                  4,
                )} / Longitude: ${mmadetector.lon?.toFixed(4)}`}
          </Typography>
          {mmadetector.elevation !== null && (
            <Typography variant="body1" color="text.secondary">
              Elevation: {mmadetector.elevation}
            </Typography>
          )}
        </ListItem>
      ))}
    </List>
  );
};

export default MMADetectorList;
