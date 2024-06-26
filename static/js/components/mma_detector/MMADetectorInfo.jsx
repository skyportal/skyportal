import React from "react";
import { useSelector } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Divider from "@mui/material/Divider";

const useStyles = makeStyles(() => ({
  root: {
    width: "100%",
    height: "100%",
    padding: "1rem",
    gap: "1rem",
    maxHeight: "85vh",
    overflowY: "auto",
  },
  listItem: {
    display: "flex",
    flexDirection: "column",
    justifyItems: "left",
    alignItems: "left",
  },
  mmadetector_header: {
    display: "flex",
    flexDirection: "row",
    justifyItems: "center",
    alignItems: "center",
    gap: "0.5rem",
  },
  h2: {
    textAlign: "left",
    fontSize: "1.4rem",
    padding: "0",
    margin: "0",
  },
  h3: {
    textAlign: "left",
    fontSize: "1rem",
    marginTop: "0.5rem",
    padding: "0",
    margin: "0",
  },
}));

const MMADetectorInfo = () => {
  const classes = useStyles();
  const { mmadetectorList } = useSelector((state) => state.mmadetectors);
  // return a list of mmadetectors with their information
  return mmadetectorList ? (
    <List className={classes.root}>
      {mmadetectorList.map((mmadetector) => (
        <div key={`${mmadetector.id}_list_item`}>
          <ListItem
            id={`${mmadetector.name}_info`}
            className={classes.listItem}
            key={`${mmadetector.id}_info`}
          >
            <div
              className={classes.mmadetector_header}
              key={`${mmadetector.id}_header`}
            >
              <h2 className={classes.h2}>
                {mmadetector.name} ({mmadetector.nickname})
              </h2>
            </div>
            <h3 className={classes.h3} key={`${mmadetector.id}_location`}>
              Location : {mmadetector.lat ? mmadetector.lat.toFixed(4) : null},{" "}
              {mmadetector.lon ? mmadetector.lon.toFixed(4) : null}
            </h3>
          </ListItem>
          <Divider />
        </div>
      ))}
    </List>
  ) : (
    <h2 className={classes.h2}>No mmadetector selected</h2>
  );
};

export default MMADetectorInfo;
