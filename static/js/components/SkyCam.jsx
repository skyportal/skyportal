import React from 'react';
import PropTypes from 'prop-types';

import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import Typography from '@material-ui/core/Typography';
import { makeStyles } from '@material-ui/core/styles';
import CardMedia from '@material-ui/core/CardMedia';

const useStyles = makeStyles(() => ({
    cardDiv: {
      minWidth: 300,
      minHeight: 300
    },
    title: {
      fontSize: 14,
    },
    media: {
      minHeight: 300
    }
  }
));

const SkyCam = ({ telescope }) => {

  const classes = useStyles();

  if (!telescope.skycam_link){
    return <div></div>;
  } else {
    return (
      <Card className={classes.cardDiv}>
        <CardContent>
          <Typography className={classes.title} color="textSecondary">
            Current Conditions
          </Typography>
        </CardContent>
        <CardMedia
          image={telescope.skycam_link}
          title={`${telescope.nickname} SkyCam`}
          className={classes.media}/>
      </Card>
    )
  }

};

SkyCam.propTypes = {
  telescope: PropTypes.shape({
    skycam_link: PropTypes.string
  }).isRequired
};

export default SkyCam;
