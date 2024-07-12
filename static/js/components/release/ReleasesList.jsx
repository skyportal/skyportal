import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import VisibilityIcon from "@mui/icons-material/Visibility";
import AddIcon from "@mui/icons-material/Add";
import { deletePublicRelease } from "../../ducks/public_pages/public_release";
import Button from "../Button";
import ReleaseForm from "./ReleaseForm";

export function truncateText(text, length) {
  if (text !== null) {
    return text.length < length ? text : `${text.substring(0, length)}...`;
  }
  return "";
}

const useStyles = makeStyles(() => ({
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
  },
  itemNameDescription: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  },
  itemButtons: {
    display: "flex",
  },
}));

const ReleasesList = () => {
  const styles = useStyles();
  const dispatch = useDispatch();
  const releases = useSelector((state) => state.publicReleases);
  const [releaseToEdit, setReleaseToEdit] = useState({});
  const [openReleaseList, setOpenReleaseList] = useState(false);
  const [openReleaseForm, setOpenReleaseForm] = useState(false);

  const deleteRelease = (id) => {
    dispatch(deletePublicRelease(id));
  };

  function handleViewEdit(release) {
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
      <div className={styles.listHeader}>
        <Button
          onClick={() => {
            handleViewList();
          }}
        >
          View releases {openReleaseList ? <ExpandLess /> : <ExpandMore />}
        </Button>
        <Button
          onClick={() => {
            handleViewEdit({});
          }}
        >
          <AddIcon />
        </Button>
      </div>
      {openReleaseList && !openReleaseForm && (
        <div>
          {releases.map((release) => (
            <div key={`release_${release.id}`} className={styles.item}>
              <div className={styles.itemNameDescription}>
                <div style={{ fontWeight: "bold" }}>{release.name}</div>
                <div>{truncateText(release.description, 40)}</div>
              </div>
              {release.group_ids.length > 0 && (
                <div className={styles.itemButtons}>
                  <Button
                    href={`/public/releases/${release.link_name}`}
                    target="_blank"
                  >
                    <VisibilityIcon />
                  </Button>
                  <Button
                    onClick={() => {
                      handleViewEdit(release);
                    }}
                  >
                    <EditIcon />
                  </Button>
                  <Button
                    onClick={() => {
                      deleteRelease(release.id);
                    }}
                  >
                    <DeleteIcon />
                  </Button>
                </div>
              )}
            </div>
          ))}
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
