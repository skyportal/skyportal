import { Link } from "react-router-dom";

import Badge from "@mui/material/Badge";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import FeedbackIcon from "@mui/icons-material/FeedbackOutlined";

import { HEADER_ICON_SX } from "../HeaderPanel";
import { useOpenFeedbackCount } from "../../ducks/feedback";
import { useGetProfileQuery } from "../../ducks/profile";

const FeedbackButton = () => {
  const { data: profile } = useGetProfileQuery();
  const openFeedback = useOpenFeedbackCount();

  if (!profile || profile.is_anonymous) return null;

  return (
    <Tooltip title="Feedback">
      <IconButton
        component={Link}
        to="/feedback"
        aria-label="feedback"
        data-testid="feedbackButton"
        sx={{ ...HEADER_ICON_SX, display: { xs: "none", md: "inline-flex" } }}
      >
        <Badge
          badgeContent={openFeedback}
          overlap="circular"
          color="warning"
          data-testid="feedbackBadge"
        >
          <FeedbackIcon fontSize="inherit" />
        </Badge>
      </IconButton>
    </Tooltip>
  );
};

export default FeedbackButton;
