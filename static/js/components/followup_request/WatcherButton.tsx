import React, { useState } from "react";

import IconButton from "@mui/material/IconButton";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import Tooltip from "@mui/material/Tooltip";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import Button from "../Button";

import * as followupRequestActions from "../../ducks/followup_requests";

const UnwatchButton = (
  requestID: number,
  textMode: boolean,
  serverSide = false,
) => {
  const dispatch = useAppDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    const params: any = {};
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

const WatchButton = (
  requestID: number,
  textMode: boolean,
  serverSide = false,
) => {
  const dispatch = useAppDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    const params: any = {};
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

interface WatcherButtonProps {
  followupRequest: {
    id: number;
    requester?: { id?: number; username?: string };
    instrument?: { id?: number; name?: string };
    status?: string;
    allocation?: { group?: { name?: string } };
    watchers?: { id?: number; user_id?: number; username?: string }[];
  };
  textMode: boolean;
  serverSide?: boolean;
}

const WatcherButton = ({
  followupRequest,
  textMode,
  serverSide = false,
}: WatcherButtonProps) => {
  const currentUser = useAppSelector((state) => state.profile);

  if (!followupRequest) {
    return null;
  }
  const watcherIds: (number | undefined)[] = [];
  followupRequest.watchers?.forEach((s) => {
    watcherIds.push(s.user_id);
  });
  if (watcherIds.includes(currentUser.id)) {
    return UnwatchButton(followupRequest.id, textMode, serverSide);
  }

  return WatchButton(followupRequest.id, textMode, serverSide);
};

export default WatcherButton;
