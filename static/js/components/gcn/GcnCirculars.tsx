import React from "react";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Typography from "@mui/material/Typography";

import { makeStyles } from "tss-react/mui";

const useStyles = makeStyles()(() => ({
  root: {
    margin: "0",
    padding: "0",
  },
  header: {
    fontSize: "1rem",
  },
}));

interface GcnCircularsProps {
  gcnEvent: {
    dateobs?: string;
    circulars?: Record<string, string>;
    [key: string]: any;
  };
}

const GcnCirculars = ({ gcnEvent }: GcnCircularsProps) => {
  const { classes } = useStyles();
  const { classes: styles } = useStyles();

  return (
    <div className={classes.root}>
      {gcnEvent.circulars && Object.keys(gcnEvent.circulars)?.length > 0 ? (
        <List>
          {gcnEvent?.circulars &&
            Object.keys(gcnEvent.circulars).map((id) => (
              <>
                <Divider component="li" />
                <ListItem key={id}>
                  <a
                    href={`https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/?circular=${id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {gcnEvent.circulars?.[id]}
                  </a>
                </ListItem>
              </>
            ))}
        </List>
      ) : (
        <Typography className={styles.header}>
          No circulars available for this event yet
        </Typography>
      )}
    </div>
  );
};

export default GcnCirculars;
