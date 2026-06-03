import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { makeStyles } from "tss-react/mui";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";

import { useAppSelector, useAppDispatch } from "../../types/hooks";
import FilterPlugins from "./FilterPlugins";

import * as groupActions from "../../ducks/group";
import * as filterActions from "../../ducks/filter";
import * as streamActions from "../../ducks/stream";

const useStyles = makeStyles()((theme) => ({
  paper: {
    width: "100%",
    padding: theme.spacing(1),
    textAlign: "left",
    color: theme.palette.text.primary,
  },
  nested: {
    paddingLeft: theme.spacing(1),
  },
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
  accordion_details: {
    flexDirection: "column",
  },
  button_add: {
    maxWidth: "8.75rem",
  },
  formControl: {
    margin: theme.spacing(1),
    minWidth: "12rem",
  },
  selectEmpty: {
    marginTop: theme.spacing(2),
  },
  root: {
    minWidth: "18rem",
  },
  bullet: {
    display: "inline-block",
    margin: "0 2px",
    transform: "scale(0.8)",
  },
  title: {
    fontSize: "0.875rem",
  },
  big_font: {
    fontSize: "1rem",
  },
  pos: {
    marginBottom: "0.75rem",
  },
  header: {
    paddingBottom: 10,
  },
}));

const Filter = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  const [filterLoadError, setFilterLoadError] = useState("");
  const [groupLoadError, setGroupLoadError] = useState("");
  const [streamLoadError, setStreamLoadError] = useState("");

  const { fid } = useParams();
  const loadedId = useAppSelector((state) => state.filter.id);

  useEffect(() => {
    const fetchFilter = async () => {
      if (!fid) {
        return;
      }
      const data = (await dispatch(filterActions.fetchFilter(fid))) as any;
      if (data.status === "error") {
        setFilterLoadError(data.message);
      }
    };
    if (loadedId !== fid) {
      fetchFilter();
    }
  }, [fid, loadedId, dispatch]);

  const group_id = useAppSelector((state) => state.filter.group_id);
  const stream_id = useAppSelector((state) => state.filter.stream_id);

  useEffect(() => {
    const fetchGroup = async () => {
      const data = (await dispatch(groupActions.fetchGroup(group_id))) as any;
      if (data.status === "error") {
        setGroupLoadError(data.message);
        if (groupLoadError.length > 1) {
          dispatch(showNotification(groupLoadError, "error"));
        }
      }
    };
    if (group_id) fetchGroup();
  }, [group_id, dispatch, groupLoadError]);

  useEffect(() => {
    const fetchStream = async () => {
      const data = (await dispatch(
        streamActions.fetchStream(stream_id),
      )) as any;
      if (data.status === "error") {
        setStreamLoadError(data.message);
        if (streamLoadError.length > 1) {
          dispatch(showNotification(streamLoadError, "error"));
        }
      }
    };
    if (stream_id) fetchStream();
  }, [stream_id, dispatch, streamLoadError]);

  const filter = useAppSelector((state) => state.filter);
  const group = useAppSelector((state) => state.group) as any;
  const stream = useAppSelector((state) => state.stream) as any;

  if (filterLoadError) {
    return <div>{filterLoadError}</div>;
  }

  // renders
  if (!filter) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <div>
      <Typography variant="h6" className={classes.header}>
        Filter:&nbsp;&nbsp;
        {filter.name}
      </Typography>

      <Grid container spacing={2}>
        <Grid size={{ sm: 12, md: 12 }}>
          <Card className={classes.root}>
            <CardContent>
              {group && stream && (
                <Typography
                  className={classes.title}
                  color="textSecondary"
                  gutterBottom
                >
                  Group: <Link to={`/group/${group.id}`}>{group.name}</Link>
                  <br />
                  Group id: {group.id}
                  <br />
                  Stream: {stream.name}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ sm: 12, md: 12 }}>
          <FilterPlugins {...({ group } as any)} />
        </Grid>
      </Grid>
    </div>
  );
};

export default Filter;
