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
  interferometer_header: {
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

const InterferometerInfo = () => {
  const classes = useStyles();
  const { interferometerList } = useSelector((state) => state.interferometers);
  // return a list of interferometers with their information
  return interferometerList ? (
    <List className={classes.root}>
      {interferometerList.map((interferometer) => (
        <div key={`${interferometer.id}_list_item`}>
          <ListItem
            id={`${interferometer.name}_info`}
            className={classes.listItem}
            key={`${interferometer.id}_info`}
          >
            <div
              className={classes.interferometer_header}
              key={`${interferometer.id}_header`}
            >
              <h2 className={classes.h2}>
                {interferometer.name} ({interferometer.nickname})
              </h2>
            </div>
            <h3 className={classes.h3} key={`${interferometer.id}_location`}>
              Location :{" "}
              {interferometer.lat ? interferometer.lat.toFixed(4) : null},{" "}
              {interferometer.lon ? interferometer.lon.toFixed(4) : null}
            </h3>
          </ListItem>
          <Divider />
        </div>
      ))}
    </List>
  ) : (
    <h2 className={classes.h2}>No interferometer selected</h2>
  );
};

export default InterferometerInfo;
