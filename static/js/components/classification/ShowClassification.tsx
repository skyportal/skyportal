import { useGetProfileQuery } from "../../ducks/profile";
import { useEffect, useState } from "react";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import ThumbUp from "@mui/icons-material/ThumbUp";
import ThumbDown from "@mui/icons-material/ThumbDown";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import {
  useAddClassificationVoteMutation,
  useDeleteClassificationMutation,
} from "../../ducks/source";
import { useGetConfigQuery } from "../../ducks/config";

// preserve the legacy <font> tag (not a typed JSX intrinsic element)
const Font: any = "font";

export const useStyles = makeStyles()(() => ({
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

interface ClassificationRowProps {
  classifications: Record<string, any>[];
  fontSize?: string;
}

const ClassificationRow = ({
  classifications,
  fontSize = "1rem",
}: ClassificationRowProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [addClassificationVote] = useAddClassificationVoteMutation();
  const [deleteClassificationMutation] = useDeleteClassificationMutation();

  const { data: currentUser } = useGetProfileQuery();
  // The old global `group` slice (a single most-recently-fetched group) no
  // longer exists: the group duck is now RTK Query keyed by id, and no specific
  // group id is in scope here. As before, when no group is loaded the
  // membership lookup resolves to undefined.
  const groupUsers: any = undefined;
  const currentGroupUser = groupUsers?.filter(
    (groupUser: any) => groupUser.user_id === currentUser?.id,
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
    window.localStorage.getItem("CURRENT_GROUP_ADMIN") as string,
  );
  const [dialogOpen, setDialogOpen] = useState(false);
  const [votesVisible, setVotesVisible] = useState(false);
  const [classificationToDelete, setClassificationToDelete] = useState<
    any | null
  >(null);
  const openDialog = (id: any) => {
    setDialogOpen(true);
    setClassificationToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setClassificationToDelete(null);
  };

  const addVote = (classification_id: any, vote: number) => {
    addClassificationVote({ classification_id, data: { vote } })
      .unwrap()
      .then(() => {
        dispatch(showNotification("Vote registered"));
      })
      .catch(() => {
        // error notification handled by the baseQuery
      });
  };

  const switchVotesVisible = () => {
    setVotesVisible(!votesVisible);
  };

  const deleteClassification = () => {
    deleteClassificationMutation(classificationToDelete)
      .unwrap()
      .then(() => {
        dispatch(showNotification("Classification deleted"));
        closeDialog();
      })
      .catch(() => {
        // error notification handled by the baseQuery
      });
  };

  const classification = classifications[0]!;

  const classifications_classes = (useGetConfigQuery().data as any)
    ?.classificationsClasses;

  const upvoterIds: any[] = [];
  const downvoterIds: any[] = [];
  let upvoteValue = 1;
  let downvoteValue = -1;
  let upvoteColor: any = "disabled";
  let downvoteColor: any = "disabled";

  classification["votes"]?.forEach((s: any) => {
    if (s.vote === 1) {
      upvoterIds.push(s.id);
      if (s.voter_id === currentUser?.id) {
        upvoteValue = 0;
        upvoteColor = "success";
      }
    } else if (s.vote === -1) {
      downvoterIds.push(s.id);
      if (s.voter_id === currentUser?.id) {
        downvoteValue = 0;
        downvoteColor = "error";
      }
    }
  });

  const defaultColor = (isML: boolean) => {
    let color = "#000000";
    if (isML) {
      color = "#3063ab";
    }
    return color;
  };

  const permission =
    currentUser?.permissions.includes("System admin") ||
    currentUser?.permissions.includes("Manage groups") ||
    isGroupAdmin ||
    currentUser?.username === classification["author_name"];

  const clsProb = classification["probability"]
    ? classification["probability"]
    : "null";
  return (
    <div>
      <Tooltip
        key={`${classification["modified"]}tt`}
        disableFocusListener
        disableTouchListener
        title={
          <div>
            <div>
              {classifications.map((cls) => (
                <span key={cls["id"]}>
                  P=
                  {clsProb} ({cls["taxname"]})
                  <br />
                  <i>{cls["author_name"]}</i>
                  <br />
                </span>
              ))}
            </div>
            <div>
              <Button
                id="delete_classification"
                classes={{
                  root: classes.classificationDelete,
                  disabled: classes.classificationDeleteDisabled,
                }}
                onClick={() => openDialog(classification["id"])}
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
                key={classification["id"]}
                id="down_vote"
                onClick={() => switchVotesVisible()}
              >
                <Font color="white">
                  {votesVisible ? (
                    <VisibilityOffIcon color="primary" />
                  ) : (
                    <VisibilityIcon color="primary" />
                  )}{" "}
                  &nbsp; Votes Visible?
                </Font>
              </Button>
            </div>
            <div>
              <Button
                key={classification["id"]}
                id="down_vote"
                onClick={() => addVote(classification["id"], downvoteValue)}
              >
                <ThumbDown color={downvoteColor} />
                <Font color="white">
                  {" "}
                  {votesVisible ? (
                    <> &nbsp; {`${downvoterIds.length} vote(s)`} </>
                  ) : (
                    <> </>
                  )}
                </Font>
              </Button>
            </div>
            <div>
              <Button
                key={classification["id"]}
                id="up_vote"
                onClick={() => addVote(classification["id"], upvoteValue)}
              >
                <ThumbUp color={upvoteColor} />
                <Font color="white">
                  {" "}
                  {votesVisible ? (
                    <> &nbsp; {`${upvoterIds.length} vote(s)`} </>
                  ) : (
                    <> </>
                  )}
                </Font>
              </Button>
            </div>
            {classification["ml"] && (
              <span>PS: This classification comes from a ML classifier.</span>
            )}
          </div>
        }
      >
        {classifications_classes?.origin && classification["origin"] ? (
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
                {classification["ml"] ? (
                  <span>
                    {classification["probability"] < 0.1
                      ? `ML: ${classification["classification"]}?`
                      : `ML: ${classification["classification"]}`}
                  </span>
                ) : (
                  <span>
                    {classification["probability"] < 0.1
                      ? `${classification["classification"]}?`
                      : classification["classification"]}
                  </span>
                )}
              </span>
            }
            key={`${classification["modified"]}tb`}
            size="small"
            className={classes.chip}
            style={{
              color: classifications_classes?.origin
                ? classifications_classes.origin[classification["origin"]]
                : defaultColor(classification?.["ml"]),
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
                {classification["ml"] ? (
                  <span>
                    {classification["probability"] < 0.1
                      ? `ML: ${classification["classification"]}?`
                      : `ML: ${classification["classification"]}`}
                  </span>
                ) : (
                  <span>
                    {classification["probability"] < 0.1
                      ? `${classification["classification"]}?`
                      : classification["classification"]}
                  </span>
                )}
              </span>
            }
            key={`${classification["modified"]}tb`}
            size="small"
            className={classes.chip}
            style={{
              backgroundColor: classifications_classes?.classification
                ? classifications_classes.classification[
                    classification["classification"]
                  ]
                : "#999999",
              color: defaultColor(classification?.["ml"]),
            }}
          />
        )}
      </Tooltip>
    </div>
  );
};

const groupBy = (array: any[], key: string) =>
  array.reduce((result: Record<string, any[]>, cv: any) => {
    // if we've seen this key before, add the value, else generate
    // a new list for this key
    (result[cv[key]] = result[cv[key]] || []).push(cv);
    return result;
  }, {});

export const getSortedClasses = (classifications: any[]) => {
  // Here we compute the most recent non-zero probability class for each taxonomy
  const filteredClasses = classifications.filter((i) => i.probability > 0);
  const groupedClasses = groupBy(filteredClasses, "taxonomy_id");
  const sortedClasses: any[] = [];

  Object.keys(groupedClasses)?.forEach((item) =>
    sortedClasses.push(
      (groupedClasses[item] ?? []).sort((a: any, b: any) =>
        a.modified < b.modified ? 1 : -1,
      ),
    ),
  );

  return sortedClasses;
};

interface ShowClassificationProps {
  classifications: Record<string, any>[];
  taxonomyList: Record<string, any>[];
  shortened?: boolean;
  fontSize?: string;
}

function ShowClassification({
  classifications,
  taxonomyList,
  shortened = false,
  fontSize = "1rem",
}: ShowClassificationProps) {
  const sorted_classifications = (classifications || []).sort((a, b) =>
    a["created_at"] > b["created_at"] ? -1 : 1,
  );

  const classificationsGrouped = sorted_classifications.reduce(
    (r: Record<string, any[]>, a: any) => {
      r[a.classification] = [...(r[a.classification] || []), a];
      return r;
    },
    {},
  );

  const keys = Object.keys(classificationsGrouped);
  keys.forEach((key) => {
    const group = classificationsGrouped[key] ?? [];
    group.forEach((_item: any, index: number) => {
      let taxname: any = taxonomyList.filter(
        (i) => i["id"] === group[index].taxonomy_id,
      );
      if (taxname.length > 0) {
        taxname = taxname[0].name;
      } else {
        taxname = "Unknown taxonomy";
      }
      group[index].taxname = taxname;
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
          classifications={classificationsGrouped[key] ?? []}
          fontSize={fontSize}
        />
      ))}
    </div>
  );
}

export default ShowClassification;
