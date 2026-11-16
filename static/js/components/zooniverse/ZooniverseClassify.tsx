import { useCallback, useEffect, useState } from "react";

import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import { showNotification } from "baselayer/components/Notifications";

import { useGetCandidateQuery } from "../../ducks/candidate/candidate";
import { useGetSourceQuery } from "../../ducks/source";
import { useAppDispatch } from "../../types/hooks";
import VegaPhotometry from "../plot/VegaPhotometry";
import ThumbnailList from "../thumbnail/ThumbnailList";

const useStyles = makeStyles()((theme) => ({
  page: {
    padding: "1rem",
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "1rem",
  },
  // The scanning-page row: cutouts, light curve, then what we know about it.
  row: {
    display: "grid",
    gridTemplateColumns: "minmax(18rem, 1fr) minmax(20rem, 1.4fr) 14rem",
    gap: "1rem",
    alignItems: "start",
    [theme.breakpoints.down("md")]: { gridTemplateColumns: "1fr" },
  },
  info: {
    display: "flex",
    flexDirection: "column",
    gap: "0.35rem",
    fontSize: "0.9rem",
  },
  ask: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "0.75rem",
    paddingTop: "0.5rem",
    borderTop: `1px solid ${theme.palette.divider}`,
  },
  answers: {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.5rem",
    justifyContent: "center",
  },
  fallbackImage: { maxWidth: "100%", height: "auto", background: "#000" },
  meta: { color: theme.palette.text.secondary, fontSize: "0.85rem" },
}));

interface Answer {
  label: string;
}

interface Task {
  question?: string;
  answers?: Answer[];
}

interface AuthResponse {
  linked: boolean;
  login: string | null;
  authorize_url: string;
}

interface SkyPortalEffects {
  save_groups: { id: number; name: string }[];
  class_map: Record<string, string>;
  taxonomy_id: number | null;
}

interface SubjectResponse {
  subject: {
    id: string;
    metadata: Record<string, string>;
    locations: Record<string, string>[];
  } | null;
  task_key?: string;
  task?: Task;
  skyportal?: SkyPortalEffects;
}

const ZooniverseClassify = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  const [data, setData] = useState<SubjectResponse | null>(null);
  const [auth, setAuth] = useState<AuthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [writeToSkyPortal, setWriteToSkyPortal] = useState(true);

  const objId = data?.subject?.metadata?.["skyportal_obj_id"];
  // Subjects are exported from either a candidate or a source page, so try
  // both: whichever the object is, the panels below get their data.
  const { data: candidate, isError: notACandidate } = useGetCandidateQuery(
    objId as string,
    { skip: !objId },
  );
  const { data: source } = useGetSourceQuery(objId as string, {
    skip: !objId || !notACandidate,
  });

  const loadAuth = useCallback(async () => {
    try {
      const response = await fetch("/api/zooniverse/auth");
      const body = await response.json();
      setAuth(body.status === "success" ? body.data : null);
    } catch {
      setAuth(null);
    }
  }, []);

  const loadSubject = useCallback(async () => {
    setData(null);
    setError(null);
    try {
      const response = await fetch("/api/zooniverse/subject");
      const body = await response.json();
      if (body.status !== "success") {
        setError(body.message || "Could not load a subject");
        return;
      }
      setData(body.data);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    loadSubject();
    loadAuth();
  }, [loadSubject, loadAuth]);

  const classify = async (answerIndex: number) => {
    if (!data?.subject) return;
    setSubmitting(true);
    try {
      const response = await fetch("/api/zooniverse/classification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_id: data.subject.id,
          task: data.task_key,
          // Panoptes stores the answer index, which is what its aggregation
          // (and the consensus reducer) works in.
          value: answerIndex,
          obj_id: objId,
          // Omitting the groups keeps the answer in Panoptes only.
          save_group_ids: writeToSkyPortal
            ? data.skyportal?.save_groups.map((group) => group.id)
            : [],
        }),
      });
      const body = await response.json();
      if (body.status === "success") {
        const problem =
          body.data?.save_error || body.data?.classification_error;
        if (problem) {
          dispatch(
            showNotification(
              `Recorded in Zooniverse, but ${problem}`,
              "warning",
            ),
          );
        } else {
          dispatch(showNotification("Classification submitted"));
        }
        await loadSubject();
      } else {
        dispatch(
          showNotification(body.message || "Submission failed", "error"),
        );
      }
    } catch (e) {
      dispatch(showNotification(String(e), "error"));
    } finally {
      setSubmitting(false);
    }
  };

  if (error) {
    return (
      <Paper className={classes.page}>
        <Typography variant="h5">Zooniverse</Typography>
        <Typography>{error}</Typography>
      </Paper>
    );
  }

  if (!data) {
    return (
      <Paper className={classes.page}>
        <CircularProgress />
      </Paper>
    );
  }

  if (!data.subject) {
    return (
      <Paper className={classes.page}>
        <Typography variant="h5">Zooniverse</Typography>
        <Typography>
          Nothing left to classify in this workflow&apos;s queue.
        </Typography>
        <div>
          <Button variant="outlined" onClick={loadSubject}>
            Check again
          </Button>
        </div>
      </Paper>
    );
  }

  const imageUrl = data.subject.locations
    .map((location) => Object.values(location)[0])
    .find(Boolean);
  const pageUrl = data.subject.metadata?.["skyportal_url"];
  const answers = data.task?.answers || [];
  const saveGroups = data.skyportal?.save_groups || [];
  const obj = (candidate || source) as any;

  return (
    <Paper className={classes.page}>
      <div className={classes.header}>
        <Typography variant="h5">Zooniverse</Typography>
        {auth &&
          (auth.linked ? (
            <span className={classes.meta}>
              signed in as {auth.login || "a Zooniverse volunteer"}
            </span>
          ) : (
            <Button
              variant="outlined"
              size="small"
              href={auth.authorize_url}
              // Classifications are attributed to whoever is signed in; without
              // this they are recorded against the instance itself.
            >
              Sign in with Zooniverse
            </Button>
          ))}
      </div>

      <div className={classes.row}>
        {obj ? (
          <ThumbnailList
            ra={obj.ra}
            dec={obj.dec}
            thumbnails={obj.thumbnails || []}
            size="100%"
            minSize="6rem"
            maxSize="8.8rem"
            titleSize="0.7rem"
            useGrid={false}
            columns={3}
            noMargin
          />
        ) : (
          // No SkyPortal record reachable: fall back to the subject image, so
          // the page still works for a volunteer without candidate access.
          imageUrl && (
            <img
              className={classes.fallbackImage}
              src={imageUrl}
              alt={objId || "subject"}
            />
          )
        )}
        {objId && (
          <VegaPhotometry
            sourceId={objId}
            style={{ width: "100%", minHeight: "18rem", maxHeight: "18rem" }}
          />
        )}
        <div className={classes.info}>
          {objId && (
            <b>
              <a
                href={pageUrl || `/source/${objId}`}
                target="_blank"
                rel="noreferrer"
              >
                {objId}
              </a>
            </b>
          )}
          {obj && (
            <>
              <span>
                {Number(obj.ra).toFixed(6)}, {Number(obj.dec).toFixed(6)}
              </span>
              {obj.is_source && (
                <span className={classes.meta}>already saved as a source</span>
              )}
            </>
          )}
          <span className={classes.meta}>subject {data.subject.id}</span>
        </div>
      </div>

      <div className={classes.ask}>
        <Typography variant="h6">
          {data.task?.question || "Classify this subject"}
        </Typography>
        <div className={classes.answers}>
          {answers.map((answer, index) => (
            <Button
              key={answer.label}
              variant="contained"
              disabled={submitting}
              onClick={() => classify(index)}
            >
              {answer.label}
            </Button>
          ))}
        </div>
        {saveGroups.length > 0 && (
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={writeToSkyPortal}
                onChange={(event) => setWriteToSkyPortal(event.target.checked)}
              />
            }
            label={
              <span className={classes.meta}>
                also save and classify in SkyPortal (
                {saveGroups.map((group) => group.name).join(", ")})
              </span>
            }
          />
        )}
      </div>
    </Paper>
  );
};

export default ZooniverseClassify;
