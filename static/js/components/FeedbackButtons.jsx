import React, { useState } from 'react';
import PropTypes from 'prop-types';
import makeStyles from '@mui/styles/makeStyles';
import Box from '@mui/material/Box';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import Button from './Button';
import { useProfileGlobal } from './utils/useProfileGlobal';

const useStyles = makeStyles((theme) => ({
  container: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
    padding: '0.5rem 0',
  },
  successMsg: {
    color: theme.palette.success.main,
    fontWeight: 'bold',
    fontSize: '0.9rem',
    marginLeft: '0.5rem',
  }
}));

const FeedbackButtons = ({ sourceId }) => {
  const classes = useStyles();
  const { profileData } = useProfileGlobal();
  const [submitted, setSubmitted] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleFeedback = (type) => {
    setFeedback(type);
    setSubmitted(true);
    // In a real implementation this would trigger an API call to retrain the active profile's classifier
    setTimeout(() => {
      setSubmitted(false);
      setFeedback(null);
    }, 3000);
  };

  return (
    <Box className={classes.container}>
      {submitted ? (
        <span className={classes.successMsg}>
          Feedback for &quot;{profileData.name}&quot; recorded! Retraining model...
        </span>
      ) : (
        <>
          <Button
            primary
            size="small"
            endIcon={<CheckCircleIcon />}
            onClick={() => handleFeedback('interesting')}
          >
            Interesting
          </Button>
          <Button
            secondary
            size="small"
            endIcon={<CancelIcon />}
            onClick={() => handleFeedback('noise')}
          >
            Mark as Noise
          </Button>
        </>
      )}
    </Box>
  );
};

FeedbackButtons.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

export default FeedbackButtons;
