import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import ThumbUp from "@mui/icons-material/ThumbUp";
import ThumbDown from "@mui/icons-material/ThumbDown";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import makeStyles from "@mui/styles/makeStyles";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import * as sourceActions from "../../ducks/source";

export const useStyles = makeStyles(() => ({
  chip: {
    fontSize: "1.2rem",
    fontWeight: "bold",
  },
  classificationDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  classificationDeleteDisabled: {
    opacity: 0,
  },
}));

const ClassificationRow = ({ classifications, fontSize }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const currentUser = useSelector((state) => state.profile);
  const groupUsers = useSelector((state) => state.group?.group_users);
  const currentGroupUser = groupUsers?.filter(
    (groupUser) => groupUser.user_id === currentUser.id,
  )[0];

  useEffect(() => {
    if (
      currentGroupUser?.admin !== undefined &&
      currentGroupUser?.admin !== null
    ) {
      window.localStorage.setItem(
        "CURRENT_GROUP_ADMIN",
        JSON.stringify(currentGroupUser.admin),
      );
    }
  }, [currentGroupUser]);

  const isGroupAdmin = JSON.parse(
    window.localStorage.getItem("CURRENT_GROUP_ADMIN"),
  );
  const [dialogOpen, setDialogOpen] = useState(false);
  const [votesVisible, setVotesVisible] = useState(false);
  const [classificationToDelete, setClassificationToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setClassificationToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setClassificationToDelete(null);
  };

  const addVote = (classification_id, vote) => {
    dispatch(
      sourceActions.addClassificationVote(classification_id, { vote }),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Vote registered"));
      }
    });
  };

  const switchVotesVisible = () => {
    setVotesVisible(!votesVisible);
  };

  const deleteClassification = () => {
    dispatch(sourceActions.deleteClassification(classificationToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Classification deleted"));
          closeDialog();
        }
      },
    );
  };

  const classification = classifications[0];

  const classifications_classes = useSelector(
    (state) => state.config.classificationsClasses,
  );

  const upvoterIds = [];
  const downvoterIds = [];
  let upvoteValue = 1;
  let downvoteValue = -1;
  let upvoteColor = "disabled";
  let downvoteColor = "disabled";

  classification.votes?.forEach((s) => {
    if (s.vote === 1) {
      upvoterIds.push(s.id);
      if (s.voter_id === currentUser.id) {
        upvoteValue = 0;
        upvoteColor = "success";
      }
    } else if (s.vote === -1) {
      downvoterIds.push(s.id);
      if (s.voter_id === currentUser.id) {
        downvoteValue = 0;
        downvoteColor = "error";
      }
    }
  });

  const defaultColor = (isML) => {
    let color = "#000000";
    if (isML) {
      color = "#3063ab";
    }
    return color;
  };

  const permission =
    currentUser.permissions.includes("System admin") ||
    currentUser.permissions.includes("Manage groups") ||
    isGroupAdmin ||
    currentUser.username === classification.author_name;

  const clsProb = classification.probability
    ? classification.probability
    : "null";
  return (
    <div>
      <Tooltip
        key={`${classification.modified}tt`}
        disableFocusListener
        disableTouchListener
        title={
          <div>
            <div>
              {classifications.map((cls) => (
                <span key={cls.id}>
                  P=
                  {clsProb} ({cls.taxname})
                  <br />
                  <i>{cls.author_name}</i>
                  <br />
                </span>
              ))}
            </div>
            <div>
              <Button
                key={classification.id}
                id="delete_classification"
                classes={{
                  root: classes.classificationDelete,
                  disabled: classes.classificationDeleteDisabled,
                }}
                onClick={() => openDialog(classification.id)}
                disabled={!permission}
              >
                <DeleteIcon />
              </Button>
              <ConfirmDeletionDialog
                deleteFunction={deleteClassification}
                dialogOpen={dialogOpen}
                closeDialog={closeDialog}
                resourceName="classification"
              />
            </div>
            <div>
              <Button
                key={classification.id}
                id="down_vote"
                onClick={() => switchVotesVisible()}
              >
                <font color="white">
                  {votesVisible ? (
                    <VisibilityOffIcon color="primary" />
                  ) : (
                    <VisibilityIcon color="primary" />
                  )}{" "}
                  &nbsp; Votes Visible?
                </font>
              </Button>
            </div>
            <div>
              <Button
                key={classification.id}
                id="down_vote"
                onClick={() => addVote(classification.id, downvoteValue)}
              >
                <ThumbDown color={downvoteColor} />
                <font color="white">
                  {" "}
                  {votesVisible ? (
                    <> &nbsp; {`${downvoterIds.length} vote(s)`} </>
                  ) : (
                    <> </>
                  )}
                </font>
              </Button>
            </div>
            <div>
              <Button
                key={classification.id}
                id="up_vote"
                onClick={() => addVote(classification.id, upvoteValue)}
              >
                <ThumbUp color={upvoteColor} />
                <font color="white">
                  {" "}
                  {votesVisible ? (
                    <> &nbsp; {`${upvoterIds.length} vote(s)`} </>
                  ) : (
                    <> </>
                  )}
                </font>
              </Button>
            </div>
            {classification.ml && (
              <span>PS: This classification comes from a ML classifier.</span>
            )}
          </div>
        }
      >
        {classifications_classes?.origin && classification.origin ? (
          <Chip
            label={
              <span
                style={{
                  display: "flex",
                  flexDirection: "row",
                  alignItems: "center",
                  fontSize,
                }}
              >
                {classification.ml ? (
                  <span>
                    {classification.probability < 0.1
                      ? `ML: ${classification.classification}?`
                      : `ML: ${classification.classification}`}
                  </span>
                ) : (
                  <span>
                    {classification.probability < 0.1
                      ? `${classification.classification}?`
                      : classification.classification}
                  </span>
                )}
              </span>
            }
            key={`${classification.modified}tb`}
            size="small"
            className={classes.chip}
            style={{
              color: classifications_classes?.origin
                ? classifications_classes.origin[classification.origin]
                : defaultColor(classification?.ml),
            }}
          />
        ) : (
          <Chip
            label={
              <span
                style={{
                  display: "flex",
                  flexDirection: "row",
                  alignItems: "center",
                  fontSize,
                }}
              >
                {classification.ml ? (
                  <span>
                    {classification.probability < 0.1
                      ? `ML: ${classification.classification}?`
                      : `ML: ${classification.classification}`}
                  </span>
                ) : (
                  <span>
                    {classification.probability < 0.1
                      ? `${classification.classification}?`
                      : classification.classification}
                  </span>
                )}
              </span>
            }
            key={`${classification.modified}tb`}
            size="small"
            className={classes.chip}
            style={{
              backgroundColor: classifications_classes?.classification
                ? classifications_classes.classification[
                    classification.classification
                  ]
                : "#999999",
              color: defaultColor(classification?.ml),
            }}
          />
        )}
      </Tooltip>
    </div>
  );
};

ClassificationRow.propTypes = {
  classifications: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      classification: PropTypes.string,
      created_at: PropTypes.string,
      author_name: PropTypes.string,
      modified: PropTypes.string,
      probability: PropTypes.number,
      ml: PropTypes.bool,
      origin: PropTypes.string,
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        }),
      ),
      votes: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          vote: PropTypes.number,
        }),
      ),
    }),
  ).isRequired,
  fontSize: PropTypes.string,
};

ClassificationRow.defaultProps = {
  fontSize: "1rem",
};

const groupBy = (array, key) =>
  array.reduce((result, cv) => {
    // if we've seen this key before, add the value, else generate
    // a new list for this key
    (result[cv[key]] = result[cv[key]] || []).push(cv);
    return result;
  }, {});

export const getSortedClasses = (classifications) => {
  // Here we compute the most recent non-zero probability class for each taxonomy
  const filteredClasses = classifications.filter((i) => i.probability > 0);
  const groupedClasses = groupBy(filteredClasses, "taxonomy_id");
  const sortedClasses = [];

  Object.keys(groupedClasses)?.forEach((item) =>
    sortedClasses.push(
      groupedClasses[item].sort((a, b) => (a.modified < b.modified ? 1 : -1)),
    ),
  );

  return sortedClasses;
};

function ShowClassification({
  classifications,
  taxonomyList,
  shortened,
  fontSize,
}) {
  const sorted_classifications = (classifications || []).sort((a, b) =>
    a.created_at > b.created_at ? -1 : 1,
  );

  const classificationsGrouped = sorted_classifications.reduce((r, a) => {
    r[a.classification] = [...(r[a.classification] || []), a];
    return r;
  }, {});

  const keys = Object.keys(classificationsGrouped);
  keys.forEach((key) => {
    classificationsGrouped[key].forEach((item, index) => {
      let taxname = taxonomyList.filter(
        (i) => i.id === classificationsGrouped[key][index].taxonomy_id,
      );
      if (taxname.length > 0) {
        taxname = taxname[0].name;
      } else {
        taxname = "Unknown taxonomy";
      }
      classificationsGrouped[key][index].taxname = taxname;
    });
  });

  const title = shortened ? "" : <b>Classification: </b>;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "0.25rem",
        maxWidth: "100%",
      }}
    >
      {title}
      {keys.map((key) => (
        <ClassificationRow
          key={key}
          classifications={classificationsGrouped[key]}
          fontSize={fontSize}
        />
      ))}
    </div>
  );
}

ShowClassification.propTypes = {
  classifications: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
  taxonomyList: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
  shortened: PropTypes.bool,
  fontSize: PropTypes.string,
};
ShowClassification.defaultProps = {
  shortened: false,
  fontSize: "1rem",
};

export default ShowClassification;
