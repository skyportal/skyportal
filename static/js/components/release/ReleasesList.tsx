import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { deletePublicRelease } from "../../ducks/public_pages/public_release";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import Button from "../Button";
import ReleaseForm from "./ReleaseForm";

export function truncateText(text: string | null, length: number) {
  if (text !== null && text !== "") {
    return text.length < length ? text : `${text.substring(0, length)}...`;
  }
  return "...";
}

const useStyles = makeStyles()(() => ({
  listHeader: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "0.4rem",
  },
  item: {
    display: "flex",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0.5rem 1rem",
    border: "1px solid #e0e0e0",
    borderRadius: "0.5rem",
    marginBottom: "0.3rem",
  },
  itemNameDescription: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  },
  itemDescription: {
    fontSize: "0.8rem",
  },
  itemButtons: {
    display: "flex",
  },
  noRelease: {
    display: "flex",
    justifyContent: "center",
    padding: "1.5rem 0",
    color: "gray",
  },
}));

const ReleasesList = () => {
  const { classes: styles } = useStyles();
  const dispatch = useAppDispatch();
  const releases = useAppSelector((state) => state.publicReleases);
  const manageSourcesAccess = useAppSelector(
    (state) => state.profile,
  ).permissions?.includes("Manage sources");
  const [releaseToEdit, setReleaseToEdit] = useState<any>({});
  const [openReleaseList, setOpenReleaseList] = useState(!manageSourcesAccess);
  const [openReleaseForm, setOpenReleaseForm] = useState(false);

  const deleteRelease = (id: number) => {
    dispatch(deletePublicRelease(id));
  };

  function handleViewEdit(release: any) {
    // If the form is closed, set the release to edit and open it, if not, close it
    if (!openReleaseForm) {
      setReleaseToEdit(release);
    }
    setOpenReleaseForm(!openReleaseForm);
  }

  function handleViewList() {
    // if the form is open, close it, if not, change the state of the list
    if (!openReleaseForm) {
      setOpenReleaseList(!openReleaseList);
    } else {
      setOpenReleaseForm(false);
    }
  }

  return (
    <div>
      {manageSourcesAccess && (
        <div className={styles.listHeader}>
          <Button
            onClick={() => {
              handleViewList();
            }}
            disabled={releases.length === 0}
          >
            Manage releases {openReleaseList ? <ExpandLess /> : <ExpandMore />}
          </Button>
          <Button
            onClick={() => {
              handleViewEdit({});
            }}
          >
            Add +
          </Button>
        </div>
      )}
      {(!manageSourcesAccess ||
        (releases.length > 0 && openReleaseList && !openReleaseForm)) && (
        <div>
          {releases.length > 0 ? (
            releases.map((release: any) => (
              <div key={`release_${release.id}`} className={styles.item}>
                <div className={styles.itemNameDescription}>
                  <div>{release.name}</div>
                  <div className={styles.itemDescription}>
                    {truncateText(release.description, 40)}
                  </div>
                </div>
                <div className={styles.itemButtons}>
                  <Button
                    href={`/public/releases/${release.link_name}`}
                    target="_blank"
                  >
                    <VisibilityIcon />
                  </Button>
                  {manageSourcesAccess && release.group_ids.length > 0 && (
                    <>
                      <Button onClick={() => handleViewEdit(release)}>
                        <EditIcon />
                      </Button>
                      <Button onClick={() => deleteRelease(release.id)}>
                        <DeleteIcon />
                      </Button>
                    </>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className={styles.noRelease}>No releases available yet!</div>
          )}
        </div>
      )}
      {openReleaseForm && (
        <ReleaseForm
          release={releaseToEdit}
          setRelease={setReleaseToEdit}
          setOpenReleaseForm={setOpenReleaseForm}
        />
      )}
    </div>
  );
};

export default ReleasesList;
