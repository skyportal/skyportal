import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import DeleteIcon from "@mui/icons-material/Delete";
import Tooltip from "@mui/material/Tooltip";
import GroupIcon from "@mui/icons-material/Group";
import ListItem from "@mui/material/ListItem";
import makeStyles from "@mui/styles/makeStyles";
import { FixedSizeList } from "react-window";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";

import * as sourceActions from "../ducks/source";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  classification: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "column",
    minHeight: "4rem",
    paddingBottom: "0.5rem",
    paddingLeft: "0.5rem",
    alignItems: "start",
    justifyContent: "space-between",
    overflowAnchor: "none",
  },
  classificationHeader: {
    flexGrow: "4",
    flexDirection: "row",
    paddingTop: "0.5rem",
    paddingBottom: "0.5rem",
    alignItems: "start",
  },
  classificationTime: {
    flexGrow: "4",
    color: "gray",
    fontSize: "80%",
  },
  classificationMessage: {
    maxWidth: "20em",
  },
  classificationUserDomain: {
    color: "lightgray",
    fontSize: "80%",
    paddingRight: "0.5em",
  },
  wrap: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "start",
    minHeight: "1.6875rem",
    maxWidth: "20em",
  },
  classificationDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
}));

const ClassificationList = () => {
  const styles = useStyles();

  const dispatch = useDispatch();
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const source = useSelector((state) => state.source);
  const obj = source;
  const userProfile = useSelector((state) => state.profile);
  const groupUsers = useSelector((state) => state.group?.group_users);
  const classifications_classes = useSelector(
    (state) => state.config.classificationsClasses
  );
  const currentGroupUser = groupUsers?.filter(
    (groupUser) => groupUser.user_id === userProfile.id
  )[0];
  // const acls = useSelector((state) => state.profile.acls);
  let { classifications } = obj;

  useEffect(() => {
    if (
      currentGroupUser?.admin !== undefined &&
      currentGroupUser?.admin !== null
    ) {
      window.localStorage.setItem(
        "CURRENT_GROUP_ADMIN",
        JSON.stringify(currentGroupUser.admin)
      );
    }
  }, [currentGroupUser]);

  const isGroupAdmin = JSON.parse(
    window.localStorage.getItem("CURRENT_GROUP_ADMIN")
  );

  const [dialogOpen, setDialogOpen] = useState(false);
  const [classificationToDelete, setClassificationToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setClassificationToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setClassificationToDelete(null);
  };

  const deleteClassification = () => {
    dispatch(sourceActions.deleteClassification(classificationToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Classification deleted"));
          closeDialog();
        }
      }
    );
  };

  classifications = classifications || [];

  // newest classifications on top reverse sort the classifications by created_at
  const sorted_classifications = classifications.sort((a, b) =>
    a.created_at > b.created_at ? -1 : 1
  );

  const items = sorted_classifications.map(
    ({
      id,
      author_name,
      created_at,
      classification,
      probability,
      origin,
      taxonomy_id,
      groups,
    }) => {
      let taxname = taxonomyList.filter((i) => i.id === taxonomy_id);
      if (taxname.length > 0) {
        taxname = taxname[0].name;
      } else {
        taxname = "Unknown taxonomy";
      }
      const permission =
        userProfile.permissions.includes("System admin") ||
        userProfile.permissions.includes("Manage groups") ||
        isGroupAdmin ||
        userProfile.username === author_name;
      return (
        <ListItem key={id} className={styles.classification}>
          <div className={styles.classificationHeader}>
            <span className={styles.classificationUser}>
              <span>{author_name}</span>
            </span>
            &nbsp;
            <span className={styles.classificationTime}>
              {dayjs().to(dayjs.utc(`${created_at}Z`))}
            </span>
            &nbsp;
            <Tooltip title={groups?.map((group) => group.name)?.join(", ")}>
              <GroupIcon
                fontSize="small"
                style={{ paddingTop: "6px", paddingBottom: "0px" }}
              />
            </Tooltip>
          </div>
          <div className={styles.wrap} data-testid={`classificationDiv_${id}`}>
            <div className={styles.classificationMessage}>
              {origin && classifications_classes?.origin ? (
                <span
                  style={{
                    fontWeight: "bold",
                    fontSize: "120%",
                    color: classifications_classes.origin[origin] || "black",
                  }}
                >
                  {classification}
                </span>
              ) : (
                <span style={{ fontWeight: "bold", fontSize: "120%" }}>
                  {classification}
                </span>
              )}{" "}
              {origin ? (
                <span>{`(P=${probability}, origin=${origin})`}</span>
              ) : (
                <span>{`(P=${probability})`}</span>
              )}
              <div>
                <i>{taxname}</i>
              </div>
            </div>
          </div>
          <div>
            <Button
              size="small"
              type="button"
              name={`deleteClassificationButton${id}`}
              onClick={() => openDialog(id)}
              disabled={!permission}
              className={styles.classificationDelete}
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
        </ListItem>
      );
    }
  );

  const Row = ({ index }) => items[index];

  return (
    <div
      style={{ display: classifications.length > 0 ? "block" : "none" }}
      className={styles.classifications}
    >
      <FixedSizeList
        className={styles.classifications}
        height={Math.min(360, parseInt(classifications.length * 100, 10))}
        width={350}
        itemSize={150}
        itemCount={items.length}
      >
        {Row}
      </FixedSizeList>
    </div>
  );
};

ClassificationList.propTypes = {};

export default ClassificationList;
