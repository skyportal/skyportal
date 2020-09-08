import React from "react";
import PropTypes from "prop-types";

import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";
import Typography from "@material-ui/core/Typography";
import { makeStyles } from "@material-ui/core/styles";
import CardMedia from "@material-ui/core/CardMedia";

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
