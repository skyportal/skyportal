import { useState } from "react";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import StarIcon from "@mui/icons-material/Star";
import StarBorderIcon from "@mui/icons-material/StarBorder";

import { useGetProfileQuery } from "../../ducks/profile";
import {
  useAddToWatchListMutation,
  useRemoveFromWatchListMutation,
} from "../../ducks/followup_requests";

interface WatcherButtonProps {
  followupRequest: { id: number; watchers?: { user_id?: number }[] };
  serverSide?: boolean;
}

const WatcherButton = ({
  followupRequest,
  serverSide = false,
}: WatcherButtonProps) => {
  const { data: currentUser } = useGetProfileQuery();
  const [addToWatchList] = useAddToWatchListMutation();
  const [removeFromWatchList] = useRemoveFromWatchListMutation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isWatching = followupRequest.watchers?.some(
    (watcher) => watcher.user_id === currentUser?.id,
  );

  const toggleWatch = async () => {
    setIsSubmitting(true);
    const mutation = isWatching ? removeFromWatchList : addToWatchList;
    await mutation({
      id: followupRequest.id,
      params: serverSide ? { refreshRequests: true } : {},
    });
    setIsSubmitting(false);
  };

  return (
    <Tooltip
      title={`click to ${isWatching ? "stop following" : "follow"} this request`}
    >
      <IconButton onClick={toggleWatch} disabled={isSubmitting} size="large">
        {isWatching ? <StarIcon /> : <StarBorderIcon />}
      </IconButton>
    </Tooltip>
  );
};

export default WatcherButton;
