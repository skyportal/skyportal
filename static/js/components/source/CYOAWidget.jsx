import React, { useEffect, useState, useCallback } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";

import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import Divider from "@mui/material/Divider";

const useStyles = makeStyles((theme) => ({
  container: {
    padding: "0.5rem 0",
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    flexWrap: "wrap",
  },
  reasoning: {
    padding: "0.25rem 0",
    color: theme.palette.text.primary,
  },
  flagsContainer: {
    display: "flex",
    gap: "0.25rem",
    flexWrap: "wrap",
    marginTop: "0.5rem",
  },
  metaText: {
    fontSize: "0.875rem",
    color: theme.palette.text.secondary,
    display: "flex",
    gap: "1rem",
  },
  feedbackSection: {
    marginTop: "0.5rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
  },
}));

const confidenceColor = {
  high: "success",
  medium: "warning",
  low: "error",
};

const CYOAWidget = ({ sourceId }) => {
  const classes = useStyles();
  const currentUser = useSelector((state) => state.profile);

  const [verdict, setVerdict] = useState(null);
  const [loading, setLoading] = useState(true);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(null);

  const fetchVerdict = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/sources/${sourceId}/annotations`, {
        headers: {
          "Content-Type": "application/json",
        },
      });
      if (!response.ok) {
        setVerdict(null);
        setLoading(false);
        return;
      }
      const result = await response.json();
      const annotations = result?.data || [];

      const cyoaAnnotation = annotations.find(
        (a) => a.origin === "CYOA-Llama-3.3",
      );

      const userFeedback = annotations.find(
        (a) =>
          a.origin === `CYOA-Human-${currentUser?.id}` ||
          a.origin?.startsWith("CYOA-Human-"),
      );

      if (cyoaAnnotation) {
        setVerdict(cyoaAnnotation.data);
      } else {
        setVerdict(null);
      }

      if (userFeedback) {
        setFeedbackGiven(userFeedback.data?.feedback || null);
      }
    } catch {
      setVerdict(null);
    }
    setLoading(false);
  }, [sourceId, currentUser?.id]);

  useEffect(() => {
    fetchVerdict();
  }, [fetchVerdict]);

  const submitFeedback = async (feedbackType) => {
    setFeedbackSubmitting(true);
    try {
      const payload = {
        origin: `CYOA-Human-${currentUser?.id}`,
        data: {
          feedback: feedbackType,
          ai_class: verdict?.cyoa_ai_class,
          timestamp: new Date().toISOString(),
        },
        group_ids: currentUser?.accessible_groups?.map((g) => g.id) || [],
      };

      const response = await fetch(`/api/sources/${sourceId}/annotations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setFeedbackGiven(feedbackType);
      }
    } catch (err) {
      console.error("Failed to submit CYOA feedback:", err);
    }
    setFeedbackSubmitting(false);
  };

  if (loading) {
    return <CircularProgress size={24} />;
  }

  if (!verdict) {
    return (
      <Typography variant="body2" color="text.secondary">
        No anomalous verdict found.
      </Typography>
    );
  }

  return (
    <div className={classes.container}>
      {/* Top Meta info - Classification and Stats */}
      <div className={classes.row}>
        <Typography variant="subtitle1" style={{ fontWeight: "bold" }}>
          Classification: {verdict.cyoa_ai_class || "Unknown"}
        </Typography>
        <Chip
          label={`Confidence: ${verdict.cyoa_confidence || "medium"}`}
          color={confidenceColor[verdict.cyoa_confidence] || "default"}
          size="small"
        />
      </div>

      <div className={classes.metaText}>
        {verdict.cyoa_rank && <span>Anomaly Rank: #{verdict.cyoa_rank}</span>}
        {verdict.cyoa_score && (
          <span>Score: {Number(verdict.cyoa_score).toFixed(4)}</span>
        )}
      </div>

      <Divider />

      {/* LLM Reasoning - standard text blob */}
      <div>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Automated Reasoning:
        </Typography>
        {verdict.cyoa_reasoning ? (
          <Typography variant="body1" className={classes.reasoning}>
            {verdict.cyoa_reasoning}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No reasoning provided.
          </Typography>
        )}
      </div>

      {/* Flag metadata */}
      {(verdict.cyoa_flags?.length > 0 || verdict.cyoa_follow_up) && (
        <div className={classes.flagsContainer}>
          {verdict.cyoa_follow_up && (
            <Chip
              label={verdict.cyoa_follow_up}
              size="small"
              color="primary"
              variant="outlined"
            />
          )}
          {verdict.cyoa_flags?.map((flag) => (
            <Chip key={flag} label={flag} size="small" variant="outlined" />
          ))}
        </div>
      )}

      {/* Feedback Section */}
      <div className={classes.feedbackSection}>
        <Typography variant="body2" style={{ fontWeight: "bold" }} gutterBottom>
          Human Feedback
        </Typography>
        {feedbackGiven ? (
          <Typography variant="body2" color="text.secondary">
            You marked this as: <strong>{feedbackGiven}</strong>
          </Typography>
        ) : (
          <div className={classes.row}>
            <Button
              variant="outlined"
              size="small"
              color="primary"
              startIcon={<ThumbUpIcon />}
              onClick={() => submitFeedback("interesting")}
              disabled={feedbackSubmitting}
            >
              Interesting Object
            </Button>
            <Button
              variant="outlined"
              size="small"
              color="secondary"
              startIcon={<ThumbDownIcon />}
              onClick={() => submitFeedback("noise")}
              disabled={feedbackSubmitting}
            >
              Instrumental Noise
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

CYOAWidget.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

export default CYOAWidget;
