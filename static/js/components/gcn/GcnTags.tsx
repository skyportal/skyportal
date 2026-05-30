import React, { useState } from "react";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import { makeStyles } from "tss-react/mui";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import AddGcnTag from "./AddGcnTag";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import * as gcnTagsActions from "../../ducks/gcnTags";

const useStyles = makeStyles()(() => ({
  root: {
    margin: "0",
    padding: "0",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  title: {
    margin: 0,
    marginRight: "0.45rem",
    padding: "0",
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: 0,
      marginBottom: 0,
      marginLeft: "0.05rem",
      marginRight: "0.05rem",
    },
  },
  tagDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
}));

interface GcnTagsProps {
  gcnEvent: {
    dateobs: string;
    tags?: string[];
    aliases?: string[];
    localizations?: { id?: number; localization_name?: string; tags?: any[] }[];
    [key: string]: any;
  };
  show_title?: boolean;
  addTags?: boolean;
}

const GcnTags = ({
  gcnEvent,
  show_title = false,
  addTags = true,
}: GcnTagsProps) => {
  const { classes: styles } = useStyles();

  const dispatch = useAppDispatch();

  const userProfile = useAppSelector((state) => state.profile);

  const gcn_tags_classes = useAppSelector(
    (state) => state.config.gcnTagsClasses,
  );

  const [dialogOpen, setDialogOpen] = useState(false);
  const [tagToDelete, setTagToDelete] = useState<any>(null);
  const openDialog = (tag: any) => {
    setDialogOpen(true);
    setTagToDelete(tag);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setTagToDelete(null);
  };

  const deleteTag = () => {
    dispatch(gcnTagsActions.deleteGcnTag(gcnEvent.dateobs, tagToDelete)).then(
      (result: any) => {
        if (result.status === "success") {
          dispatch(showNotification("GCN Event Tag deleted"));
          closeDialog();
        }
      },
    );
  };

  const gcnTags: string[] = [];
  if (gcnEvent?.tags) {
    gcnEvent.tags.forEach((tag) => {
      gcnTags.push(tag);
    });
  }

  // we want to look through the gcnEvent.aliases.
  // If one starts by LVC#, we grab what is after the #
  // and use it later as a link for the LVC tag
  let graceid =
    gcnEvent?.aliases?.find((alias) => alias.startsWith("LVC#")) || null;
  if (graceid) {
    [, graceid] = graceid.split("#");
  }
  // same for Fermi
  let fermiid =
    gcnEvent?.aliases?.find((alias) => alias.startsWith("FERMI#")) || null;
  if (fermiid) {
    [, fermiid] = fermiid.split("#");
  }
  const gcnTagsUnique = [...new Set(gcnTags)];

  const localizationTags: string[] = [];
  gcnEvent.localizations?.forEach((loc) => {
    loc.tags?.forEach((tag: any) => {
      localizationTags.push(tag.text);
    });
  });
  const localizationTagsUnique = [...new Set(localizationTags)];

  const permission =
    userProfile.permissions.includes("System admin") ||
    userProfile.permissions.includes("Manage GCNs");

  return (
    <div className={styles.root}>
      {show_title && <h4 className={styles.title}>Tags:</h4>}
      <div className={styles.chips} {...({ name: "gcn_triggers-tags" } as any)}>
        {gcnTagsUnique.map((tag) => (
          <Tooltip
            key={tag}
            title={
              <>
                <Button
                  size="small"
                  type="button"
                  name={`deleteTagButton${tag}`}
                  onClick={() => openDialog(tag)}
                  disabled={!permission}
                  className={styles.tagDelete}
                >
                  <DeleteIcon />
                </Button>
                <ConfirmDeletionDialog
                  deleteFunction={deleteTag}
                  dialogOpen={dialogOpen}
                  closeDialog={closeDialog}
                  resourceName="tag"
                />
              </>
            }
          >
            {}
            {graceid && tag === "LVC" ? (
              <Chip
                className={(styles as any)[tag]}
                size="small"
                label={tag}
                key={tag}
                component="a"
                clickable
                target="_blank"
                href={
                  graceid
                    ? `https://gracedb.ligo.org/superevents/${graceid}/view/`
                    : undefined
                }
              />
            ) : fermiid && tag === "Fermi" ? (
              <Chip
                className={(styles as any)[tag]}
                size="small"
                label={tag}
                key={tag}
                component="a"
                clickable
                target="_blank"
                href={
                  fermiid
                    ? `http://heasarc.gsfc.nasa.gov/FTP/fermi/data/gbm/triggers/${gcnEvent?.dateobs.slice(
                        0,
                        4,
                      )}/${fermiid}/quicklook/`
                    : undefined
                }
              />
            ) : (
              <Chip
                size="small"
                label={tag}
                key={tag}
                style={{
                  backgroundColor:
                    gcn_tags_classes && tag in gcn_tags_classes
                      ? gcn_tags_classes[tag]
                      : "#999999",
                }}
              />
            )}
          </Tooltip>
        ))}
        {localizationTagsUnique.map((tag) => (
          <Chip
            size="small"
            label={tag}
            key={tag}
            // if there is a class for this tag, apply it, otherwise use the basic grey color
            style={{
              backgroundColor:
                gcn_tags_classes && tag in gcn_tags_classes
                  ? gcn_tags_classes[tag]
                  : "#999999",
            }}
          />
        ))}
      </div>
      {addTags && permission && (
        <div>
          <AddGcnTag gcnEvent={gcnEvent as any} />
        </div>
      )}
    </div>
  );
};

export default GcnTags;
