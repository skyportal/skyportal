import { Link } from "react-router-dom";

import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import FeedbackIcon from "@mui/icons-material/FeedbackOutlined";

import { useGetProfileQuery } from "../../ducks/profile";

const FeedbackButton = () => {
  const { data: profile } = useGetProfileQuery();

  if (!profile || profile.is_anonymous) return null;

  return (
    <Tooltip title="Feedback">
      <IconButton
        component={Link}
        to="/feedback"
        aria-label="feedback"
        data-testid="feedbackButton"
        size="large"
        sx={{ p: 0, m: 0, display: { xs: "none", md: "inline-flex" } }}
      >
        <FeedbackIcon fontSize="large" sx={{ color: "#457b9d" }} />
      </IconButton>
    </Tooltip>
  );
};

export default FeedbackButton;
