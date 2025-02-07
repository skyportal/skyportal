import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import { fetchPublicReleases } from "../../../ducks/public_pages/public_release";
import ReleasesList from "../../release/ReleasesList";

const useStyles = makeStyles(() => ({
  sourcePublishRelease: {
    marginBottom: "1rem",
    display: "flex",
    flexDirection: "column",
    padding: "0 0.3rem",
    "& .MuiGrid-item": {
      paddingTop: "0",
    },
  },
  noRelease: {
    display: "flex",
    justifyContent: "center",
    padding: "1.5rem 0",
    color: "gray",
  },
  releaseItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0.5rem 1rem",
    border: "1px solid #e0e0e0",
  },
}));

const SourcePublishRelease = ({
  sourceReleaseId,
  setSourceReleaseId,
  setOptions,
}) => {
  const styles = useStyles();
  const dispatch = useDispatch();
  const [isLoading, setIsLoading] = useState(true);
  const releases = useSelector((state) => state.publicReleases);
  const manageSourcesAccess = useSelector(
    (state) => state.profile,
  ).permissions?.includes("Manage sources");

  useEffect(() => {
    setIsLoading(true);
    dispatch(fetchPublicReleases()).then(() => setIsLoading(false));
  }, [dispatch]);

  const formSchema = {
    type: "object",
    properties: {
      release: {
        type: ["integer", "null"],
        anyOf: [
          {
            enum: [null],
            title: "- - Select a release - -",
          },
          ...releases.map((item) => ({
            enum: [item.id],
            type: "integer",
            title: item.name,
          })),
        ],
        default: null,
      },
    },
  };

  const handleReleaseChange = (data) => {
    setSourceReleaseId(data.release);
    if (releases.length > 0 && data.release) {
      setOptions(releases.find((item) => item.id === data.release).options);
    }
  };

  return (
    <div className={styles.sourcePublishRelease}>
      <div style={{ display: "flex", justifyContent: "end" }}>
        <Link
          href="/public/releases"
          target="_blank"
          style={{ fontSize: "0.7rem" }}
        >
          Public releases
        </Link>
      </div>
      {manageSourcesAccess && (
        <>
          {releases.length > 0 ? (
            <Form
              formData={
                sourceReleaseId ? { release: sourceReleaseId } : undefined
              }
              onChange={({ formData }) => handleReleaseChange(formData)}
              schema={formSchema}
              liveValidate
              validator={validator}
              uiSchema={{
                "ui:submitButtonOptions": { norender: true },
              }}
            />
          ) : (
            <div className={styles.noRelease}>
              {isLoading ? (
                <CircularProgress size={24} />
              ) : (
                <div>No releases available yet! Create the first one here.</div>
              )}
            </div>
          )}
        </>
      )}
      <ReleasesList />
    </div>
  );
};

SourcePublishRelease.propTypes = {
  sourceReleaseId: PropTypes.number,
  setSourceReleaseId: PropTypes.func.isRequired,
  setOptions: PropTypes.func.isRequired,
};

SourcePublishRelease.defaultProps = {
  sourceReleaseId: null,
};

export default SourcePublishRelease;
