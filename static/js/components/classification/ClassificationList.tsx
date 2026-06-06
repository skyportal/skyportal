import { useGetProfileQuery } from "../../ducks/profile";
import React, { useEffect, useState } from "react";
import DeleteIcon from "@mui/icons-material/Delete";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";
import GroupIcon from "@mui/icons-material/Group";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Divider from "@mui/material/Divider";
import { makeStyles } from "tss-react/mui";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import * as sourceActions from "../../ducks/source";
import { useGetTaxonomiesQuery } from "../../ducks/taxonomies";
import { useGetConfigQuery } from "../../ducks/config";
import { useAppSelector, useAppDispatch } from "../../types/hooks";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  classification: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "column",
    minHeight: "80px",
    maxHeight: "80px",
    marginBottom: "5px",
    padding: 0,
    alignItems: "start",
    justifyContent: "space-between",
    overflowAnchor: "none",
  },
  classificationHeader: {
    flexGrow: "4",
    flexDirection: "row",
    alignItems: "start",
  },
  classificationTime: {
    flexGrow: "4",
    color: "gray",
    fontSize: "80%",
  },
  classificationMessage: {
    maxWidth: "30em",
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
    maxWidth: "30em",
  },
  classificationDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
}));

const ClassificationList = () => {
  const { classes: styles } = useStyles();

  const dispatch = useAppDispatch();
  const { data: taxonomyList = [] } = useGetTaxonomiesQuery();
  const source = useAppSelector((state: any) => state.source);
  const obj = source;
  const { data: userProfile } = useGetProfileQuery();
  // `state.group` (the ambient single-group slice) was removed during the RTK
  // Query migration; this component never fetched a group, so `groupUsers` was
  // only populated incidentally. Preserve the prior (commonly empty) behaviour.
  const groupUsers: any[] | undefined = undefined;
  const { data: config } = useGetConfigQuery();
  const classifications_classes = config?.["classificationsClasses"] as
    | Record<string, Record<string, string>>
    | undefined;
  const currentGroupUser = (groupUsers as any[] | undefined)?.filter(
    (groupUser: any) => groupUser.user_id === userProfile?.id,
  )[0];
  // const acls = useGetProfileQuery().data?.acls;
  let { classifications } = obj;
  const [hideML, setHideML] = useState(false);

  const hideMLClassifications =
    useGetProfileQuery().data?.preferences?.["hideMLClassifications"];

  useEffect(() => {
    setHideML(hideMLClassifications);
  }, [hideMLClassifications]);

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
  const [classificationToDelete, setClassificationToDelete] =
    useState<any>(null);
  const openDialog = (id: any) => {
    setDialogOpen(true);
    setClassificationToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setClassificationToDelete(null);
  };

  const deleteClassification = () => {
    dispatch(sourceActions.deleteClassification(classificationToDelete)).then(
      (result: any) => {
        if (result.status === "success") {
          dispatch(showNotification("Classification deleted"));
          closeDialog();
        }
      },
    );
  };

  classifications = classifications || [];

  // newest classifications on top reverse sort the classifications by created_at
  let sorted_classifications = classifications.sort((a: any, b: any) =>
    a.created_at > b.created_at ? -1 : 1,
  );

  if (hideML) {
    // remove ML based classifications
    sorted_classifications = sorted_classifications.filter(
      (classification: any) => classification?.ml === false,
    );
  }

  const defaultColor = (isML: any) => {
    let color = "#000000";
    if (isML) {
      color = "#3063ab";
    }
    return color;
  };

  const items = sorted_classifications.map(
    ({
      id,
      author_name,
      created_at,
      classification,
      probability,
      origin,
      ml,
      taxonomy_id,
      groups,
      obj_id,
    }: any) => {
      // Meta-object provenance: when this classification was aggregated from a
      // different underlying source (SuperObj member), show which one.
      const fromLinkedObj = obj_id && obj.id && obj_id !== obj.id;
      let taxname: any = taxonomyList.filter((i: any) => i.id === taxonomy_id);
      if (taxname.length > 0) {
        taxname = taxname[0].name;
      } else {
        taxname = "Unknown taxonomy";
      }
      const permission =
        userProfile?.permissions.includes("System admin") ||
        userProfile?.permissions.includes("Manage groups") ||
        isGroupAdmin ||
        userProfile?.username === author_name;
      return (
        <React.Fragment key={`classification_${id}`}>
          <ListItem className={styles.classification}>
            <div className={styles.classificationHeader}>
              <span className={(styles as any).classificationUser}>
                <span>{author_name}</span>
              </span>
              &nbsp;
              <span className={styles.classificationTime}>
                {dayjs().to(dayjs.utc(`${created_at}Z`))}
              </span>
              &nbsp;
              <Tooltip
                title={groups?.map((group: any) => group.name)?.join(", ")}
              >
                <GroupIcon
                  fontSize="small"
                  style={{ paddingTop: "6px", paddingBottom: "0px" }}
                />
              </Tooltip>
              {fromLinkedObj && (
                <Tooltip title={`From linked source ${obj_id}`}>
                  <Chip
                    label={obj_id}
                    size="small"
                    variant="outlined"
                    component="a"
                    href={`/source/${obj_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    clickable
                    style={{ marginLeft: "0.4em", height: "18px" }}
                  />
                </Tooltip>
              )}
            </div>
            <div
              className={styles.wrap}
              data-testid={`classificationDiv_${id}`}
            >
              <div className={styles.classificationMessage}>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "row",
                    alignItems: "center",
                  }}
                >
                  {origin && classifications_classes?.["origin"] ? (
                    <span
                      style={{
                        fontWeight: "bold",
                        fontSize: "120%",
                        color:
                          classifications_classes["origin"][origin] ||
                          defaultColor(ml),
                        marginRight: "0.1em",
                      }}
                    >
                      {ml ? (
                        <Tooltip title="classification from an ML classifier">
                          <span>
                            {probability < 0.1
                              ? `ML: ${classification}?`
                              : `ML: ${classification}`}
                          </span>
                        </Tooltip>
                      ) : (
                        <span>
                          {probability < 0.1
                            ? `${classification}?`
                            : `${classification}`}
                        </span>
                      )}
                    </span>
                  ) : (
                    <span
                      style={{
                        fontWeight: "bold",
                        fontSize: "120%",
                        marginRight: "0.1em",
                        color: defaultColor(ml),
                      }}
                    >
                      {ml ? (
                        <Tooltip title="classification from an ML classifier">
                          <span>
                            {probability < 0.1
                              ? `ML: ${classification}?`
                              : `ML: ${classification}`}
                          </span>
                        </Tooltip>
                      ) : (
                        <span>
                          {probability < 0.1
                            ? `${classification}?`
                            : `${classification}`}
                        </span>
                      )}
                    </span>
                  )}
                  {origin ? (
                    <span>{`(P=${probability}, origin=${origin})`}</span>
                  ) : (
                    <span>{`(P=${probability})`}</span>
                  )}
                </div>
                <div>
                  <i>{taxname}</i>
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
            </div>
          </ListItem>
          <Divider style={{ height: "1px" }} />
        </React.Fragment>
      );
    },
  );

  return (
    <div style={{ display: classifications.length > 0 ? "block" : "none" }}>
      <List
        sx={{
          maxHeight: Math.min(
            360,
            parseInt((classifications.length * 85) as any, 10),
          ),
          width: "100%",
          overflowY: "auto",
        }}
      >
        {items}
      </List>
      <FormControlLabel
        label="Hide ML-based?"
        control={
          <Checkbox
            {...({
              color: "primary",
              title: "Hide ML-based?",
              type: "checkbox",
              onChange: (event: any) => setHideML(event.target.checked),
              checked: hideML || false,
            } as any)}
          />
        }
      />
    </div>
  );
};

export default ClassificationList;
