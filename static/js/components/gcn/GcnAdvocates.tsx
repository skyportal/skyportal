import { useGetProfileQuery } from "../../ducks/profile";
import Chip from "@mui/material/Chip";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import { makeStyles } from "tss-react/mui";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import { useAppDispatch } from "../../types/hooks";
import {
  useAddGcnEventUserMutation,
  useDeleteGcnEventUserMutation,
} from "../../ducks/gcnEvents";
import { userLabel } from "../../utils/format";

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
  addIcon: {
    height: "0.75rem",
    cursor: "pointer",
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
  gcnEventDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
}));

interface GcnAdvocatesProps {
  gcnEvent: {
    dateobs?: string;
    event_users: any[];
  };
  show_title?: boolean;
}

const GcnAdvocates = ({ gcnEvent, show_title = false }: GcnAdvocatesProps) => {
  const { classes: styles } = useStyles();

  const dispatch = useAppDispatch();
  const { data: userProfile } = useGetProfileQuery();
  const [addGcnEventUser] = useAddGcnEventUserMutation();
  const [deleteGcnEventUser] = useDeleteGcnEventUserMutation();

  const addUser = async () => {
    if (!gcnEvent.dateobs) {
      return;
    }
    try {
      await addGcnEventUser({
        userID: userProfile!.id,
        gcnEventDateobs: gcnEvent.dateobs,
      }).unwrap();
      dispatch(showNotification("GCN Event User successfully added."));
    } catch {
      // Error notification is handled by the base query.
    }
  };

  const deleteUser = async (id: number) => {
    if (!gcnEvent.dateobs) {
      return;
    }
    try {
      await deleteGcnEventUser({
        userID: id,
        gcnEventDateobs: gcnEvent.dateobs,
      }).unwrap();
      dispatch(showNotification("GCN Event User successfully deleted."));
    } catch {
      // Error notification is handled by the base query.
    }
  };

  return (
    <div className={styles.root}>
      {show_title && <h4 className={styles.title}>Advocates:</h4>}
      <div className={styles.chips}>
        {gcnEvent?.event_users?.map((event_user) => (
          <Tooltip
            key={userLabel(event_user, true)}
            title={
              <>
                <Button
                  size="small"
                  type="button"
                  name={`deleteGcnEventAdvocateButton${event_user.username}`}
                  onClick={() => deleteUser(event_user.user_id)}
                  className={styles.gcnEventDelete}
                >
                  <DeleteIcon />
                </Button>
              </>
            }
          >
            <Chip size="small" label={userLabel(event_user, true)} />
          </Tooltip>
        ))}
      </div>
      <div>
        <AddIcon
          fontSize="small"
          className={styles.addIcon}
          onClick={addUser}
        />
      </div>
    </div>
  );
};

export default GcnAdvocates;
