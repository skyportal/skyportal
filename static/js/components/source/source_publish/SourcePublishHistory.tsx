import { useEffect, useState } from "react";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";
import Link from "@mui/material/Link";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import InfoIcon from "@mui/icons-material/InfoOutlined";
import moment from "moment";
import {
  deletePublicSourcePage,
  fetchPublicSourcePages,
} from "../../../ducks/public_pages/public_source_page";
import { useAppDispatch, useAppSelector } from "../../../types/hooks";

const useStyles = makeStyles()(() => ({
  versionHistory: {
    width: "100%",
    padding: "0 0.3rem",
  },
  versionHistoryLine: {
    border: "1px solid #e0e0e0",
    display: "flex",
    padding: "0.25rem 0.5rem",
    justifyContent: "space-between",
    alignItems: "center",
    borderRadius: "0.5rem",
    marginBottom: "0.3rem",
  },
  dateAndRelease: {
    display: "flex",
    flexDirection: "column",
  },
  date: {
    display: "flex",
    gap: "1rem",
  },
  infoIcon: {
    display: "flex",
    alignItems: "center",
  },
  release: {
    fontSize: "0.8rem",
  },
  actions: {
    display: "flex",
  },
  noVersion: {
    display: "flex",
    justifyContent: "center",
    padding: "1rem 0",
    color: "gray",
  },
}));

interface SourcePublishHistoryProps {
  sourceId: string;
  versions: any[];
}

const SourcePublishHistory = ({
  sourceId,
  versions,
}: SourcePublishHistoryProps) => {
  const { classes: styles } = useStyles();
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(true);
  const manageSourcesAccess = useAppSelector(
    (state) => state.profile,
  ).permissions?.includes("Manage sources");

  useEffect(() => {
    setLoading(true);
    dispatch(fetchPublicSourcePages(sourceId)).then(() => setLoading(false));
  }, [dispatch, sourceId]);

  const deleteVersion = (id: number) => {
    dispatch(deletePublicSourcePage(id));
  };

  return (
    <div className={styles.versionHistory}>
      {versions.length > 0 ? (
        versions.map((version) => {
          return (
            <div
              className={styles.versionHistoryLine}
              key={`version_${version.id}}`}
            >
              <div className={styles.dateAndRelease}>
                <div className={styles.date}>
                  {moment(version.created_at).format("MM/DD/YY HH:mm")} UTC
                  <Tooltip
                    title={
                      <>
                        Photometry: {version.options.photometry} <br />
                        Spectroscopy: {version.options.spectroscopy} <br />
                        Classifications: {version.options.classifications}
                      </>
                    }
                    placement="right"
                  >
                    <div className={styles.infoIcon}>
                      <InfoIcon fontSize="small" color="primary" />
                    </div>
                  </Tooltip>
                </div>
                {version.release_link_name ? (
                  <Link
                    href={`/public/releases/${version.release_link_name}`}
                    className={styles.release}
                    target="_blank"
                    underline="hover"
                  >
                    {version.release_link_name}
                  </Link>
                ) : (
                  <div className={styles.release}>No release</div>
                )}
              </div>
              <div className={styles.actions}>
                <Button
                  href={`/public${
                    version.release_link_name
                      ? `/releases/${version.release_link_name}`
                      : ""
                  }/sources/${sourceId}/version/${version?.hash}`}
                  target="_blank"
                >
                  <VisibilityIcon />
                </Button>
                {manageSourcesAccess && (
                  <Button onClick={() => deleteVersion(version.id)}>
                    <DeleteIcon />
                  </Button>
                )}
              </div>
            </div>
          );
        })
      ) : (
        <div className={styles.noVersion}>
          {loading ? (
            <CircularProgress size={24} />
          ) : (
            <div>No public page available yet!</div>
          )}
        </div>
      )}
    </div>
  );
};

export default SourcePublishHistory;
