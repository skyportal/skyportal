import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
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
    flexDirection: "column",
  },
}));

const ReleasesList = ({ releases, setReleases }) => {
  const styles = useStyles();
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const [isSubmit, setIsSubmit] = useState(false);
  const [releaseToEdit, setReleaseToEdit] = useState({});
  const [openReleaseEdit, setOpenReleaseEdit] = useState(false);
  const [openReleaseList, setOpenReleaseList] = useState(false);

  useEffect(() => {
    if (isSubmit) {
      setIsSubmit(false);
      setReleases(
        [
          ...releases.filter((release) => release.id !== releaseToEdit.id),
          releaseToEdit,
        ].sort((a, b) => a.name.localeCompare(b.name)),
      );
      setReleaseToEdit({});
      setOpenReleaseEdit(false);
      setOpenReleaseList(true);
    }
  }, [isSubmit]);

  const deleteRelease = (id) => {
    dispatch(deletePublicRelease(id)).then((data) => {
      if (data.status === "success") {
        setReleases(releases.filter((release) => release.id !== id));
      }
    });
  };

  function handleViewEdit(releaseToProcess) {
    if (!openReleaseEdit) setReleaseToEdit(releaseToProcess);
    setOpenReleaseEdit(!openReleaseEdit);
    setOpenReleaseList(false);
  }

  function handleViewList() {
    setOpenReleaseList(!openReleaseList);
    setOpenReleaseEdit(false);
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
      {openReleaseList && (
        <div>
          {releases.map((release) => (
            <div key={`release_${release.id}`} className={styles.item}>
              <div className={styles.itemNameDescription}>
                <div style={{ fontWeight: "bold", marginBottom: "1rem" }}>
                  {release.name}
                </div>
                <div>{truncateText(release.description, 40)}</div>
              </div>
              <div className={styles.itemButtons}>
                <Button
                  onClick={() => {
                    handleViewEdit(release);
                  }}
                  disabled={release.groups.some((release_group) =>
                    groups.includes(release_group),
                  )}
                >
                  <EditIcon />
                </Button>
                <Button
                  onClick={() => {
                    deleteRelease(release.id);
                  }}
                  disabled={release.groups.some((release_group) =>
                    groups.includes(release_group),
                  )}
                >
                  <DeleteIcon />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
      {openReleaseEdit && (
        <ReleaseForm
          release={releaseToEdit}
          setRelease={setReleaseToEdit}
          setIsSubmit={setIsSubmit}
        />
      )}
    </div>
  );
};

ReleasesList.propTypes = {
  releases: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      description: PropTypes.string,
    }),
  ).isRequired,
  setReleases: PropTypes.func.isRequired,
};

export default ReleasesList;
