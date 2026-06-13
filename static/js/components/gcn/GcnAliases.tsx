import { useGetProfileQuery } from "../../ducks/profile";
import { useState } from "react";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import { makeStyles } from "tss-react/mui";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import AddGcnAlias from "./AddGcnAlias";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import { useDeleteGcnAliasMutation } from "../../ducks/gcnEvent";

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
  aliasDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
}));

interface GcnAliasesProps {
  gcnEvent: {
    dateobs?: string;
    aliases: string[];
    [key: string]: any;
  };
  show_title?: boolean;
}

const GcnAliases = ({ gcnEvent, show_title = false }: GcnAliasesProps) => {
  const { classes: styles } = useStyles();

  const dispatch = useAppDispatch();
  const [deleteGcnAlias] = useDeleteGcnAliasMutation();

  const { data: userProfile } = useGetProfileQuery();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [aliasToDelete, setAliasToDelete] = useState<string | null>(null);
  const openDialog = (tag: string) => {
    setDialogOpen(true);
    setAliasToDelete(tag);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setAliasToDelete(null);
  };

  const deleteAlias = () => {
    deleteGcnAlias({
      dateobs: gcnEvent.dateobs as string,
      params: { alias: aliasToDelete },
    })
      .unwrap()
      .then(() => {
        dispatch(showNotification("GCN Event Alias deleted"));
        closeDialog();
      })
      .catch(() => {
        // error notification handled by baseQuery
      });
  };

  const permission =
    userProfile?.permissions.includes("System admin") ||
    userProfile?.permissions.includes("Manage GCNs");

  return (
    <div className={styles.root}>
      {show_title && <h4 className={styles.title}>Aliases:</h4>}
      <div
        className={styles.chips}
        {...({ name: "gcn_triggers-aliases" } as any)}
      >
        {gcnEvent?.aliases?.map((alias) => (
          <Tooltip
            key={alias}
            title={
              <>
                <Button
                  size="small"
                  type="button"
                  name={`deleteAliasButton${alias}`}
                  onClick={() => openDialog(alias)}
                  disabled={!permission}
                  className={styles.aliasDelete}
                >
                  <DeleteIcon />
                </Button>
                <ConfirmDeletionDialog
                  deleteFunction={deleteAlias}
                  dialogOpen={dialogOpen}
                  closeDialog={closeDialog}
                  resourceName="alias"
                />
              </>
            }
          >
            <Chip
              size="small"
              label={alias}
              key={alias}
              clickable
              onClick={() => {
                window.open(
                  `https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/?event=${
                    alias.split("#")[1] || alias
                  }`,
                  "_blank",
                );
              }}
            />
          </Tooltip>
        ))}
      </div>
      <div>
        <AddGcnAlias gcnEvent={gcnEvent} />
      </div>
    </div>
  );
};

export default GcnAliases;
