import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import { useAppSelector } from "../../../types/hooks";
import { useGetPublicReleasesQuery } from "../../../ducks/public_pages/public_release";
import ReleasesList from "../../release/ReleasesList";

const useStyles = makeStyles()(() => ({
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

interface SourcePublishReleaseProps {
  sourceReleaseId?: number | null;
  setSourceReleaseId: (...args: any[]) => void;
  setOptions: (...args: any[]) => void;
}

const SourcePublishRelease = ({
  sourceReleaseId = null,
  setSourceReleaseId,
  setOptions,
}: SourcePublishReleaseProps) => {
  const { classes: styles } = useStyles();
  const { data: releasesData, isLoading: loading } =
    useGetPublicReleasesQuery();
  const releases = (releasesData ?? []) as any[];
  const manageSourcesAccess = useAppSelector(
    (state) => state.profile,
  ).permissions?.includes("Manage sources");

  const formSchema = {
    type: "object",
    properties: {
      release: {
        type: "integer",
        title: "Release",
        oneOf: releases.map((item) => ({
          enum: [item.id],
          title: item.name,
        })),
      },
    },
  };

  const handleReleaseChange = (data: any) => {
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
              onChange={
                (({ formData }: { formData: any }) =>
                  handleReleaseChange(formData)) as any
              }
              schema={formSchema as any}
              liveValidate
              validator={validator}
              uiSchema={{
                release: {
                  "ui:placeholder": "Choose an option",
                },
                "ui:submitButtonOptions": { norender: true },
              }}
            />
          ) : (
            <div className={styles.noRelease}>
              {loading ? (
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

export default SourcePublishRelease;
