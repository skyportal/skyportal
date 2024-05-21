import React, { useEffect, useState } from "react";
import makeStyles from "@mui/styles/makeStyles";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import DeleteIcon from "@mui/icons-material/Delete";
import Link from "@mui/material/Link";
import moment from "moment";
import {
  deletePublicSourcePage,
  fetchPublicSourcePages,
} from "../../../ducks/public_pages/public_source_page";

const useStyles = makeStyles(() => ({
  versionHistory: {
    width: "100%",
  },
  versionHistoryLine: {
    border: "1px solid #e0e0e0",
    display: "flex",
    padding: "0.25rem 0.5rem",
    justifyContent: "space-between",
    alignItems: "center",
    borderRadius: "0.5rem",
    marginBottom: "0.5rem",
  },
  noVersion: {
    display: "flex",
    justifyContent: "center",
    padding: "1rem 0",
    color: "gray",
    fontWeight: "bold",
  },
}));

const SourcePublishHistory = ({ source_id, newPageGenerate = null }) => {
  const styles = useStyles();
  const dispatch = useDispatch();
  const [versions, setVersions] = useState([]);
  const [isVersions, setIsVersions] = useState(true);

  useEffect(() => {
    dispatch(fetchPublicSourcePages(source_id, 10)).then((data) => {
      setVersions(data.data);
      setIsVersions(data.data.length > 0);
    });
  }, [dispatch, source_id]);

  useEffect(() => {
    if (newPageGenerate) {
      setVersions([{ PublicSourcePage: newPageGenerate }, ...versions]);
      setIsVersions(true);
    }
  }, [newPageGenerate]);

  const deleteVersion = (id) => {
    dispatch(deletePublicSourcePage(id)).then((data) => {
      if (data.status === "success") {
        setIsVersions(versions.length > 1);
        setVersions(versions.filter((obj) => obj.PublicSourcePage.id !== id));
      }
    });
  };
  const displayDate = (date) => {
    // Parse the date with Moment.js
    const dateObj = moment(date);

    // Format the date into a string with up to 2 fractional second digits
    const dateString = dateObj.format("MM/DD/YYYY HH:mm:ss");
    return `${dateString} UTC`;
  };

  return (
    <div className={styles.versionHistory}>
      {isVersions && versions?.length > 0 ? (
        versions.map((obj) => {
          const version = obj.PublicSourcePage;
          return (
            <div
              className={styles.versionHistoryLine}
              key={`version_${version.id}}`}
            >
              <b>{displayDate(version.created_at)}</b>
              <div>
                <div>Photometry: {version?.options?.photometry}</div>
                <div>Classifications: {version?.options?.classifications}</div>
              </div>
              <Link
                href={`/public/sources/${source_id}/version/${version?.hash}`}
                target="_blank"
                rel="noreferrer"
                underline="hover"
              >
                Link to this version
              </Link>
              <button type="button" onClick={() => deleteVersion(version.id)}>
                <DeleteIcon />
              </button>
            </div>
          );
        })
      ) : (
        <div className={styles.noVersion}>
          {isVersions ? (
            <CircularProgress size={24} />
          ) : (
            <div>NO PUBLIC PAGE AVAILABLE!</div>
          )}
        </div>
      )}
    </div>
  );
};

SourcePublishHistory.propTypes = {
  source_id: PropTypes.string.isRequired,
  newPageGenerate: PropTypes.shape({
    PublicSourcePage: PropTypes.shape({
      id: PropTypes.number,
      created_at: PropTypes.string,
      hash: PropTypes.string,
      data: PropTypes.shape({
        photometry: PropTypes.string,
        classifications: PropTypes.string,
      }),
    }),
  }),
};

SourcePublishHistory.defaultProps = {
  newPageGenerate: null,
};

export default SourcePublishHistory;
