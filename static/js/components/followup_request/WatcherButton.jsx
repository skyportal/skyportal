import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import PropTypes from "prop-types";

import IconButton from "@mui/material/IconButton";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import Tooltip from "@mui/material/Tooltip";
import Button from "../Button";

import * as followupRequestActions from "../../ducks/followup_requests";

const UnwatchButton = (requestID, textMode, serverSide = false) => {
  const dispatch = useDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    const params = {};
    if (serverSide) {
      params.refreshRequests = true;
    }
    await dispatch(
      followupRequestActions.removeFromWatchList(requestID, params),
    );
    setIsSubmitting(false);
  };
  if (textMode) {
    return (
      <Button
        secondary
        onClick={handleSubmit}
        disabled={isSubmitting}
        data-testid={`watchers-text-include_${requestID}`}
      >
        Stop watching
      </Button>
    );
  }
  return (
    <Tooltip title="click to stop following this request">
      <IconButton
        onClick={handleSubmit}
        data-testid={`watchers-include_${requestID}`}
        disabled={isSubmitting}
        size="large"
      >
        <StarIcon />
      </IconButton>
    </Tooltip>
  );
};

const WatchButton = (requestID, textMode, serverSide = false) => {
  const dispatch = useDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    const params = {};
    if (serverSide) {
      params.refreshRequests = true;
    }
    await dispatch(followupRequestActions.addToWatchList(requestID, params));
    setIsSubmitting(false);
  };
  if (textMode) {
    return (
      <Button
        secondary
        onClick={handleSubmit}
        disabled={isSubmitting}
        data-testid={`watchers-text-exclude_${requestID}`}
      >
        Start watching
      </Button>
    );
  }
  return (
    <Tooltip title="click to follow this request">
      <IconButton
        onClick={handleSubmit}
        data-testid={`watchers-exclude_${requestID}`}
        disabled={isSubmitting}
        size="large"
      >
        <StarBorderIcon />
      </IconButton>
    </Tooltip>
  );
};

const WatcherButton = ({ followupRequest, textMode, serverSide }) => {
  const currentUser = useSelector((state) => state.profile);

  if (!followupRequest) {
    return null;
  }
  const watcherIds = [];
  followupRequest.watchers?.forEach((s) => {
    watcherIds.push(s.user_id);
  });
  if (watcherIds.includes(currentUser.id)) {
    // eslint-disable-next-line no-return-assign
    return UnwatchButton(followupRequest.id, textMode, serverSide);
  }
  // eslint-disable-next-line no-return-assign
  return WatchButton(followupRequest.id, textMode, serverSide);
};

WatcherButton.propTypes = {
  followupRequest: PropTypes.shape({
    id: PropTypes.number,
    requester: PropTypes.shape({
      id: PropTypes.number,
      username: PropTypes.string,
    }),
    instrument: PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    }),
    status: PropTypes.string,
    allocation: PropTypes.shape({
      group: PropTypes.shape({
        name: PropTypes.string,
      }),
    }),
    watchers: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        username: PropTypes.string,
      }),
    ),
  }).isRequired,
  textMode: PropTypes.bool.isRequired,
  serverSide: PropTypes.bool,
};

WatcherButton.defaultProps = {
  serverSide: false,
};
export default WatcherButton;
