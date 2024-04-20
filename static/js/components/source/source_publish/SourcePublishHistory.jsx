import React, { useEffect, useState } from "react";
import makeStyles from "@mui/styles/makeStyles";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import { fetchPublicSourcePages } from "../../../ducks/public_pages/public_source_page";

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
}));

const SourcePublishHistory = ({ source_id }) => {
  const styles = useStyles();
  const dispatch = useDispatch();
  const [versions, setVersions] = useState([]);
  const [isVersions, setIsVersions] = useState(true);

  useEffect(() => {
    dispatch(fetchPublicSourcePages(source_id, 10)).then((data) => {
      setVersions(data.data);
      setIsVersions(data.status === "success");
    });
  }, [dispatch, source_id]);

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
              <b>{new Date(version.created_at).toLocaleString()}</b>
              <div>
                <div>
                  Photometry: {version?.data?.photometry ? "yes" : "no"}
                </div>
                <div>
                  classifications:{" "}
                  {version?.data?.classifications ? "yes" : "no"}
                </div>
              </div>
              <Link
                href={`/public/sources/${source_id}`}
                target="_blank"
                rel="noreferrer"
                underline="hover"
              >
                Link to this version
              </Link>
            </div>
          );
        })
      ) : (
        <div style={{ display: "flex", justifyContent: "center" }}>
          {isVersions ? (
            <CircularProgress size={24} />
          ) : (
            "No public page available!"
          )}
        </div>
      )}
    </div>
  );
};

SourcePublishHistory.propTypes = {
  source_id: PropTypes.string.isRequired,
};

export default SourcePublishHistory;
