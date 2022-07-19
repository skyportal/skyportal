import React from "react";
import PropTypes from "prop-types";

import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";
import CardMedia from "@mui/material/CardMedia";

const useStyles = makeStyles(() => ({
  cardDiv: {
    minWidth: "18.75rem",
    minHeight: "18.75rem",
  },
  title: {
    fontSize: "0.875rem",
  },
  media: {
    minHeight: "18.75rem",
  },
}));

const SkyCam = ({ telescope }) => {
  const classes = useStyles();

  if (!telescope.skycam_link) {
    return <div />;
  }

  const handleImageError = (e) => {
    e.target.onerror = null;
    e.target.src = "/static/images/static.jpg";
  };

  return (
    <Card className={classes.cardDiv}>
      <CardContent>
        <Typography className={classes.title} color="textSecondary">
          Current Conditions
        </Typography>
      </CardContent>
      <CardMedia
        component="img"
        image={telescope.skycam_link}
        title={`${telescope.nickname} SkyCam`}
        className={classes.media}
        onError={handleImageError}
      />
    </Card>
  );
};

SkyCam.propTypes = {
  telescope: PropTypes.shape({
    skycam_link: PropTypes.string,
    nickname: PropTypes.string,
  }).isRequired,
};

export default SkyCam;
