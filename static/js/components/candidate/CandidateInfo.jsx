import { useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import React from "react";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Button from "../Button";
import RejectButton from "../RejectButton";
import EditSourceGroups from "../EditSourceGroups";
import SaveCandidateButton from "../SaveCandidateButton";
import { dec_to_dms, ra_to_hours } from "../../units";
import CandidatePlugins from "./CandidatePlugins";
import DisplayPhotStats from "../DisplayPhotStats";
import AddClassificationsScanningPage from "./AddClassificationsScanningPage";
import { getAnnotationValueString } from "../../utils/helpers";

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.2),
  },
  idButton: {
    textTransform: "none",
    marginBottom: theme.spacing(0.5),
    fontSize: "0.9rem",
  },
  groupsList: {
    display: "flex",
    flexDirection: "row",
    height: "1.6rem",
    alignItems: "center",
    gap: "0.1rem",
  },
  saveCandidateButton: {
    margin: "0.25rem 0",
  },
  infoItem: {
    display: "flex",
    "& > span": {
      paddingLeft: "0.25rem",
      paddingBottom: "0.1rem",
    },
    flexFlow: "row wrap",
    paddingBottom: "0.25rem",
  },
  position: {
    fontWeight: "bold",
    fontSize: "105%",
  },
  infoItemPadded: {
    "& > span": {
      paddingLeft: "0.25rem",
      paddingBottom: "0.1rem",
    },
    paddingBottom: "0.25rem",
  },
  classificationsList: {
    display: "flex",
    flexFlow: "row wrap",
    alignItems: "center",
  },
}));

const getMostRecentClassification = (classifications) => {
  // Display the most recent non-zero probability class
  const filteredClasses = classifications?.filter((i) => i.probability > 0);
  const sortedClasses = filteredClasses?.sort((a, b) =>
    a.modified < b.modified ? 1 : -1,
  );
  return sortedClasses?.length > 0
    ? `${sortedClasses[0].classification}`
    : null;
};

/**
 * Middle section in the Candidate card that displays information about the candidate
 * and the Save button
 */
const CandidateInfo = ({
  candidateObj,
  filterGroups,
  selectedAnnotationSortOptions,
}) => {
  const classes = useStyles();

  const allGroups = (useSelector((state) => state.groups.all) || []).filter(
    (g) => !g.single_user_group,
  );
  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible,
  );

  const candidateHasAnnotationWithSelectedKey = (obj) => {
    const annotation = obj.annotations.find(
      (a) => a.origin === selectedAnnotationSortOptions.origin,
    );
    if (annotation === undefined) {
      return false;
    }
    return selectedAnnotationSortOptions.key in annotation.data;
  };

  const getCandidateSelectedAnnotationValue = (obj) => {
    const annotation = obj.annotations.find(
      (a) => a.origin === selectedAnnotationSortOptions.origin,
    );
    return getAnnotationValueString(
      annotation.data[selectedAnnotationSortOptions.key],
    );
  };

  const recentHumanClassification =
    candidateObj.classifications && candidateObj.classifications.length > 0
      ? getMostRecentClassification(
          candidateObj.classifications.filter(
            (c) => c?.ml === false || c?.ml === null,
          ),
        )
      : null;

  const recentMLClassification =
    candidateObj.classifications && candidateObj.classifications.length > 0
      ? getMostRecentClassification(
          candidateObj.classifications.filter((c) => c?.ml === true),
        )
      : null;

  return (
    <div>
      {!candidateObj?.annotations ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div style={{ fontSize: "0.875rem", minWidth: "100%" }}>
          <span>
            <a
              href={`/source/${candidateObj.id}`}
              target="_blank"
              data-testid={candidateObj.id}
              rel="noreferrer"
            >
              <Button primary size="small" className={classes.idButton}>
                {candidateObj.id}&nbsp;
                <OpenInNewIcon fontSize="inherit" />
              </Button>
            </a>
          </span>
          {candidateObj.is_source ? (
            <div>
              <div>
                <Chip size="small" label="Previously Saved" color="primary" />
                <RejectButton objID={candidateObj.id} />
              </div>
              <div className={classes.infoItem}>
                <div className={classes.groupsList}>
                  <b>Saved groups: </b>
                  <EditSourceGroups
                    source={{
                      id: candidateObj.id,
                      currentGroupIds: candidateObj.saved_groups?.map(
                        (g) => g.id,
                      ),
                    }}
                    groups={allGroups}
                    icon
                  />
                </div>
                <span>
                  {candidateObj.saved_groups?.map((group) => (
                    <Chip
                      label={
                        group.nickname
                          ? group.nickname.substring(0, 15)
                          : group.name.substring(0, 15)
                      }
                      key={group.id}
                      size="small"
                      className={classes.chip}
                    />
                  ))}
                </span>
              </div>
            </div>
          ) : (
            <div>
              <Chip size="small" label="NOT SAVED" />
              <RejectButton objID={candidateObj.id} />
            </div>
          )}
          {/* If candidate is either unsaved or is not yet saved to all groups being filtered on, show the "Save to..." button */}{" "}
          {Boolean(
            !candidateObj.is_source ||
              (candidateObj.is_source &&
                filterGroups?.filter(
                  (g) =>
                    !candidateObj.saved_groups
                      ?.map((x) => x.id)
                      ?.includes(g.id),
                ).length),
          ) && (
            // eslint-disable-next-line react/jsx-indent
            <div className={classes.saveCandidateButton}>
              <SaveCandidateButton
                candidate={candidateObj}
                userGroups={
                  // Filter out groups the candidate is already saved to
                  candidateObj.is_source
                    ? userAccessibleGroups?.filter(
                        (g) =>
                          !candidateObj.saved_groups
                            ?.map((x) => x.id)
                            ?.includes(g.id),
                      )
                    : userAccessibleGroups
                }
                filterGroups={
                  // Filter out groups the candidate is already saved to
                  candidateObj.is_source
                    ? filterGroups?.filter(
                        (g) =>
                          !candidateObj.saved_groups
                            ?.map((x) => x.id)
                            ?.includes(g.id),
                      )
                    : filterGroups
                }
              />
            </div>
          )}
          {candidateObj.last_detected_at && (
            <div className={classes.infoItem}>
              <b>Last detected: </b>
              <span>
                {
                  String(candidateObj.last_detected_at)
                    .split(".")[0]
                    .split("T")[1]
                }
                &nbsp;&nbsp;
                {
                  String(candidateObj.last_detected_at)
                    .split(".")[0]
                    .split("T")[0]
                }
              </span>
            </div>
          )}
          <div className={classes.infoItem}>
            <b>Coordinates: </b>
            <div>
              <span className={classes.position}>
                {ra_to_hours(candidateObj.ra)} &nbsp;
                {dec_to_dms(candidateObj.dec)}
              </span>
            </div>
            <div>
              (&alpha;,&delta;= {candidateObj.ra.toFixed(3)}, &nbsp;
              {candidateObj.dec.toFixed(3)})
            </div>
            <div>
              (l,b= {candidateObj.gal_lon.toFixed(3)}, &nbsp;
              {candidateObj.gal_lat.toFixed(3)})
            </div>
          </div>
          <div className={classes.infoItem}>
            <CandidatePlugins candidate={candidateObj} />
          </div>
          {candidateObj.photstats && (
            <div className={classes.infoItem}>
              <DisplayPhotStats
                photstats={candidateObj.photstats[0]}
                display_header
              />
            </div>
          )}
          <div className={classes.infoItemPadded}>
            <b>Latest Classification(s): </b>
            <div className={classes.classificationsList}>
              {recentHumanClassification && (
                <span>
                  <Chip
                    size="small"
                    label={recentHumanClassification}
                    color="primary"
                    className={classes.chip}
                  />
                </span>
              )}
              {recentMLClassification && (
                <span>
                  <Chip
                    size="small"
                    label={
                      <span
                        style={{
                          display: "flex",
                          direction: "row",
                          alignItems: "center",
                        }}
                      >
                        <Tooltip title="classification from an ML classifier">
                          <span>{`ML: ${recentMLClassification}`}</span>
                        </Tooltip>
                      </span>
                    }
                    className={classes.chip}
                  />
                </span>
              )}
              <AddClassificationsScanningPage obj_id={candidateObj.id} />
            </div>
          </div>
          {selectedAnnotationSortOptions !== null &&
            candidateHasAnnotationWithSelectedKey(candidateObj) && (
              <div className={classes.infoItem}>
                <b>
                  {selectedAnnotationSortOptions.key} (
                  {selectedAnnotationSortOptions.origin}):
                </b>
                <span>{getCandidateSelectedAnnotationValue(candidateObj)}</span>
              </div>
            )}
        </div>
      )}
    </div>
  );
};

CandidateInfo.propTypes = {
  candidateObj: PropTypes.shape({
    id: PropTypes.string.isRequired,
    ra: PropTypes.number.isRequired,
    dec: PropTypes.number.isRequired,
    gal_lon: PropTypes.number.isRequired,
    gal_lat: PropTypes.number.isRequired,
    is_source: PropTypes.bool.isRequired,
    saved_groups: PropTypes.arrayOf(PropTypes.shape({})),
    last_detected_at: PropTypes.string,
    photstats: PropTypes.arrayOf(PropTypes.shape({})),
    classifications: PropTypes.arrayOf(PropTypes.shape({})),
    annotations: PropTypes.arrayOf(PropTypes.shape({})),
  }).isRequired,
  filterGroups: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
  selectedAnnotationSortOptions: PropTypes.shape({
    origin: PropTypes.string.isRequired,
    key: PropTypes.string.isRequired,
    order: PropTypes.string,
  }),
};

CandidateInfo.defaultProps = {
  selectedAnnotationSortOptions: null,
};

export default CandidateInfo;
