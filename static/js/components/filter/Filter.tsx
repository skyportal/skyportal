import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";

import { makeStyles } from "tss-react/mui";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import FilterPlugins from "./FilterPlugins";

import { useGetGroupQuery } from "../../ducks/group";
import { useGetFilterQuery } from "../../ducks/filter";
import { useGetStreamQuery } from "../../ducks/stream";

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

  const { fid } = useParams();

  const { data: filter, error: filterError } = useGetFilterQuery(fid ?? "", {
    skip: !fid,
  }) as any;
  const filterLoadError = filterError
    ? ((filterError as any)?.error ?? "Failed to load filter")
    : "";

  const group_id = filter?.group_id;
  const stream_id = filter?.stream_id;

  const { data: group, error: groupError } = useGetGroupQuery(group_id, {
    skip: !group_id,
  }) as any;

  useEffect(() => {
    if (groupError) {
      const message = (groupError as any)?.error ?? "Failed to load group";
      if (message.length > 1) {
        dispatch(showNotification(message, "error"));
      }
    }
  }, [groupError, dispatch]);

  const { data: stream } = useGetStreamQuery(stream_id ?? "", {
    skip: !stream_id,
  });

  if (filterLoadError) {
    return <div>{filterLoadError}</div>;
  }

  // renders
  if (filter == null) {
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

      {/* overflow must stay visible for the filter builder's sticky block headers */}
      <Grid container spacing={2} sx={{ overflow: "visible" }}>
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
                  Stream: {stream["name"]}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ sm: 12, md: 12 }} sx={{ overflow: "visible" }}>
          <FilterPlugins {...({ group } as any)} />
        </Grid>
      </Grid>
    </div>
  );
};

export default Filter;
