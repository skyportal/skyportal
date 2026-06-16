import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import { makeStyles } from "tss-react/mui";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import DynamicTagDisplay from "./DynamicTagDisplay";

import { dec_to_dms, ra_to_hours } from "../../units";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetRecentSourcesQuery } from "../../ducks/recentSources";
import WidgetPrefsDialog from "./WidgetPrefsDialog";

dayjs.extend(relativeTime);
dayjs.extend(utc);

export const useSourceListStyles = makeStyles<{
  invertThumbnails?: boolean | undefined;
}>()((theme, { invertThumbnails }) => ({
  stampContainer: {
    display: "contents",
  },
  stamp: {
    transition: "transform 0.1s",
    width: "6.6em",
    height: "6.6em",
    display: "block",
    "&:hover": {
      color: "rgba(255, 255, 255, 1)",
      boxShadow: "0 5px 15px rgba(51, 52, 92, 0.6)",
    },
    borderRadius: "4px",
  },
  inverted: {
    filter: invertThumbnails ? "invert(1)" : "unset",
    WebkitFilter: invertThumbnails ? "invert(1)" : "unset",
  },
  sourceListContainer: {
    height: "calc(100% - 2.5rem)",
    overflowY: "auto",
  },
  sourceList: {
    display: "block",
    alignItems: "center",
    listStyleType: "none",
    paddingLeft: 0,
    marginTop: 0,
  },
  sourceItem: {
    display: "flex",
    padding: "0.4rem",
    height: "100%",
  },
  sourceInfoContainer: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "flex-start",
    alignItems: "flex-start",
  },
  sourceName: {
    fontSize: "1rem",
    paddingBottom: 0,
    marginBottom: 0,
  },
  sourceNameLink: {
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
  },
  sourceContainer: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
    marginLeft: "8px",
    minHeight: "100%",
    alignItems: "flex-start",
  },
  sourceHeaderContainer: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    width: "100%",
  },
  sourceChipContainer: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
    marginTop: "auto",
    width: "100%",
  },
  sourceSavedSince: {
    display: "flex",
    justifyContent: "flex-end",
    flexDirection: "column",
    marginRight: "0.5rem",
  },
  classification: {
    fontSize: "0.90rem",
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
    fontWeight: "bold",
    fontStyle: "italic",
    marginLeft: "-0.09rem",
    marginTop: "-0.3rem",
  },
  sourceCoordinates: {
    marginTop: "0.1rem",
    display: "flex",
    flexDirection: "column",
    "& > span": {
      marginTop: "-0.2rem",
    },
  },
  sourceItemWithButton: {
    display: "flex",
    flexFlow: "column nowrap",
    justifyContent: "center",
    transition: "all 0.3s ease",
    "&:hover": {
      backgroundColor:
        theme.palette.mode === "light"
          ? theme.palette.secondary.light
          : (null as any),
    },
    marginBottom: "0.4rem",
    borderRadius: "8px",
  },
  root: {
    "& .MuiOutlinedInput-root": {
      "& fieldset": {
        borderColor: "#333333",
      },
      "&:hover fieldset": {
        borderColor: "#333333",
      },
      "&.Mui-focused fieldset": {
        borderColor: "#333333",
      },
    },
  },
  textField: {
    color: "#333333",
  },
  icon: {
    color: "#333333",
  },
  paper: {
    backgroundColor: "#F0F8FF",
  },
  // These rules help keep the progress wheel centered. Taken from the first example: https://material-ui.com/components/progress/
  progress: {
    display: "flex",
    // The below color rule is not for the progress container, but for CircularProgress. This component only accepts 'primary', 'secondary', or 'inherit'.
    color: theme.palette.info.main,
    "& > * + *": {
      marginLeft: theme.spacing(2),
    },
  },
  tagsContainer: {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.25rem",
    justifyContent: "flex-start",
    width: "100%",
  },
  tagChip: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: 0,
      marginBottom: 0,
      marginLeft: "0.05rem",
      marginRight: "0.05rem",
    },
  },
}));

const defaultPrefs: any = {
  maxNumSources: "25",
  groupIds: [],
  includeSitewideSources: false,
  displayTNS: true,
};

interface RecentSourcesListProps {
  sources?: any[] | undefined;
  styles: any;
  search?: boolean;
  displayTNS?: boolean;
}

const RecentSourcesList = ({
  sources = undefined,
  styles,
  search = false,
  displayTNS = true,
}: RecentSourcesListProps) => {
  const [thumbnailIdxs, setThumbnailIdxs] = useState<any>({});

  useEffect(() => {
    sources?.forEach((source) => {
      setThumbnailIdxs((prevState: any) => ({
        ...prevState,
        [source.obj_id]: 0,
      }));
    });
  }, [sources]);

  if (sources === undefined) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  if (sources.length === 0 && !search) {
    return <div>No recent sources available.</div>;
  }

  return (
    <div className={styles.sourceListContainer}>
      <ul className={styles.sourceList}>
        {sources.map((source, idx) => {
          const recentSourceName = `${source.obj_id}`;
          let classification = null;
          if (source.classifications.length > 0) {
            // Display the most recent non-zero probability class, and that isn't a ml classifier
            // if there are no results, then consider ML classifications too
            let filteredClasses = source.classifications?.filter(
              (i: any) => i.probability > 0 && i.ml === false,
            );
            if (filteredClasses.length === 0) {
              filteredClasses = source.classifications?.filter(
                (i: any) => i.probability > 0,
              );
            }
            const sortedClasses = filteredClasses.sort((a: any, b: any) =>
              a.modified < b.modified ? 1 : -1,
            );

            if (sortedClasses.length > 0) {
              classification = `(${sortedClasses[0].classification})`;
            }
          }

          const imgClasses = source.thumbnails[thumbnailIdxs[source.obj_id]]
            ?.is_grayscale
            ? `${styles.stamp} ${styles.inverted}`
            : `${styles.stamp}`;
          return (
            <li key={`recentSources_${source.obj_id}_${idx}`}>
              <Paper
                variant="outlined"
                square={false}
                data-testid={`recentSourceItem_${source.obj_id}_${source.created_at}`}
                className={styles.sourceItemWithButton}
              >
                <div className={styles.sourceItem}>
                  <Link
                    to={`/source/${source.obj_id}`}
                    className={styles.stampContainer}
                  >
                    <img
                      className={imgClasses}
                      src={
                        source.thumbnails[thumbnailIdxs[source.obj_id]]
                          ?.public_url ||
                        "/static/images/currently_unavailable.png"
                      }
                      alt={source.obj_id}
                      loading="lazy"
                      onError={(e) => {
                        // avoid infinite loop
                        if (
                          thumbnailIdxs[source.obj_id] ===
                          source.thumbnails.length - 1
                        ) {
                          (e.target as any).onerror = null;
                        }
                        setThumbnailIdxs((prevState: any) => ({
                          ...prevState,
                          [source.obj_id]: prevState[source.obj_id] + 1,
                        }));
                      }}
                    />
                  </Link>
                  <div className={styles.sourceContainer}>
                    <div className={styles.sourceHeaderContainer}>
                      <div className={styles.sourceInfoContainer}>
                        <Link
                          to={`/source/${source.obj_id}`}
                          className={styles.sourceName}
                        >
                          <span className={styles.sourceNameLink}>
                            {recentSourceName}
                          </span>
                        </Link>
                        {classification && (
                          <span className={styles.classification}>
                            {classification}
                          </span>
                        )}
                        <div className={styles.sourceCoordinates}>
                          <span
                            style={{ fontSize: "0.95rem", whiteSpace: "pre" }}
                          >
                            {`α: ${ra_to_hours(source.ra)}`}
                          </span>
                          <span
                            style={{ fontSize: "0.95rem", whiteSpace: "pre" }}
                          >
                            {`δ: ${dec_to_dms(source.dec)}`}
                          </span>
                        </div>
                      </div>
                      <div className={styles.sourceSavedSince}>
                        <span
                          style={{
                            textAlign: "right",
                            fontSize: "0.95rem",
                            fontStyle: "italic",
                            padding: 0,
                            margin: 0,
                          }}
                        >
                          {`${dayjs().to(dayjs.utc(`${source.created_at}Z`))}`
                            .replace("ago", "")
                            .replace("minutes", "min")
                            .replace("minute", "min")
                            .replace("a few", "few")}
                        </span>
                        <span
                          style={{
                            textAlign: "right",
                            fontSize: "0.95rem",
                            fontStyle: "italic",
                            padding: 0,
                            margin: 0,
                            marginTop: "-0.3rem",
                          }}
                        >
                          {` ago`}
                        </span>
                      </div>
                    </div>
                    <div className={styles.sourceChipContainer}>
                      {displayTNS && source?.tns_name?.length > 0 && (
                        <div
                          style={{
                            marginTop: source?.tags?.length > 0 ? "-3rem" : "0",
                          }}
                        >
                          <Chip
                            label={source.tns_name}
                            color={
                              source.tns_name.includes("SN")
                                ? "primary"
                                : "default"
                            }
                            size="small"
                            style={{
                              fontWeight: "bold",
                            }}
                            onClick={() => {
                              window.open(
                                `https://www.wis-tns.org/object/${
                                  source.tns_name.trim().includes(" ")
                                    ? source.tns_name.split(" ")[1]
                                    : source.tns_name
                                }`,
                                "_blank",
                              );
                            }}
                          />
                        </div>
                      )}
                      <div style={{ width: "100%" }}>
                        <DynamicTagDisplay source={source} styles={styles} />
                      </div>
                    </div>
                  </div>
                </div>
              </Paper>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

interface RecentSourcesProps {
  classes: {
    widgetPaperDiv: string;
    widgetIcon: string;
    widgetPaperFillSpace: string;
  };
}

const RecentSources = ({ classes }: RecentSourcesProps) => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const invertThumbnails = profile?.preferences?.["invertThumbnails"] as
    | boolean
    | undefined;
  const { classes: styles } = useSourceListStyles({ invertThumbnails });

  const { data: recentSources } = useGetRecentSourcesQuery();
  const prefs =
    (profile?.preferences?.["recentSources"] as any) || defaultPrefs;

  const recentSourcesPrefs = prefs
    ? { ...defaultPrefs, ...prefs }
    : defaultPrefs;

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div>
          <Typography variant="h6" display="inline">
            Recently Saved Sources
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              initialValues={recentSourcesPrefs}
              stateBranchName="recentSources"
              title="Recent Sources Preferences"
              onSubmit={updateUserPreferences}
            />
          </div>
        </div>
        <RecentSourcesList
          sources={recentSources}
          styles={styles}
          displayTNS={recentSourcesPrefs?.displayTNS !== false}
        />
      </div>
    </Paper>
  );
};

export default RecentSources;
