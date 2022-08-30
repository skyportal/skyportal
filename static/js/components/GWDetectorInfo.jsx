import React from "react";
import { useSelector } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import { Divider } from "@mui/material";

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
  gwdetector_header: {
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

const GWDetectorInfo = () => {
  const classes = useStyles();
  const { gwdetectorList } = useSelector((state) => state.gwdetectors);
  // return a list of gwdetectors with their information
  return gwdetectorList ? (
    <List className={classes.root}>
      {gwdetectorList.map((gwdetector) => (
        <div key={`${gwdetector.id}_list_item`}>
          <ListItem
            id={`${gwdetector.name}_info`}
            className={classes.listItem}
            key={`${gwdetector.id}_info`}
          >
            <div
              className={classes.gwdetector_header}
              key={`${gwdetector.id}_header`}
            >
              <h2 className={classes.h2}>
                {gwdetector.name} ({gwdetector.nickname})
              </h2>
            </div>
            <h3 className={classes.h3} key={`${gwdetector.id}_location`}>
              Location : {gwdetector.lat ? gwdetector.lat.toFixed(4) : null},{" "}
              {gwdetector.lon ? gwdetector.lon.toFixed(4) : null}
            </h3>
          </ListItem>
          <Divider />
        </div>
      ))}
    </List>
  ) : (
    <h2 className={classes.h2}>No gwdetector selected</h2>
  );
};

export default GWDetectorInfo;
