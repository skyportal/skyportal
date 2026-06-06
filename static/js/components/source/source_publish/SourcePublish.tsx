import { useGetProfileQuery } from "../../../ducks/profile";
import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import CircularProgress from "@mui/material/CircularProgress";
import { useGeneratePublicSourcePageMutation } from "../../../ducks/public_pages/public_source_page";
import Button from "../../Button";
import SourcePublishOptions from "./SourcePublishOptions";
import SourcePublishHistory from "./SourcePublishHistory";
import SourcePublishRelease from "./SourcePublishRelease";

const useStyles = makeStyles()(() => ({
  expandButton: {
    backgroundColor: "#80808017",
    width: "100%",
    display: "flex",
    justifyContent: "space-between",
    color: "gray",
    fontSize: "1rem",
    borderBottom: "2px solid #e0e0e0",
    borderRadius: "0",
    marginBottom: "0.5rem",
  },
  versionHistoryTitle: {
    marginBottom: "0.5rem",
    fontSize: "1.15rem",
  },
}));

interface SourcePublishProps {
  sourceId: string;
  isElements: {
    summary?: boolean;
    photometry?: boolean;
    spectroscopy?: boolean;
    classifications?: boolean;
  };
}

const SourcePublish = ({ sourceId, isElements }: SourcePublishProps) => {
  const { classes: styles } = useStyles();
  const [generatePublicSourcePage] = useGeneratePublicSourcePageMutation();
  const { data: currentUser } = useGetProfileQuery();
  const manageSourcesAccess =
    currentUser?.permissions?.includes("Manage sources");
  const displayOptions =
    manageSourcesAccess &&
    (isElements.summary ||
      isElements.photometry ||
      isElements.spectroscopy ||
      isElements.classifications);

  const [sourcePublishDialogOpen, setSourcePublishDialogOpen] = useState(false);
  const [publishButton, setPublishButton] = useState({
    text: "Publish",
    color: "",
  });
  const [sourcePublishReleaseOpen, setSourcePublishReleaseOpen] =
    useState(true);
  const [sourcePublishOptionsOpen, setSourcePublishOptionsOpen] =
    useState(false);
  const [sourcePublishHistoryOpen, setSourcePublishHistoryOpen] =
    useState(true);
  const [sourceReleaseId, setSourceReleaseId] = useState<any>(null);
  const [options, setOptions] = useState<Record<string, any>>({
    include_summary: true,
    include_photometry: true,
    include_spectroscopy: true,
    include_classifications: true,
    groups: [],
    streams: [],
  });
  const publish = async () => {
    if (manageSourcesAccess) {
      setPublishButton({ text: "loading", color: "" });
      try {
        await generatePublicSourcePage({
          sourceId,
          payload: {
            options,
            release_id: sourceReleaseId,
          },
        }).unwrap();
        setPublishButton({ text: "Done", color: "green" });
      } catch {
        setPublishButton({ text: "Error", color: "red" });
      }
      setTimeout(() => {
        setPublishButton({ text: "Publish", color: "" });
      }, 2000);
    }
  };

  return (
    <div>
      <Button
        secondary
        size="small"
        onClick={() => setSourcePublishDialogOpen(true)}
      >
        <Tooltip title="Click here if you want to see the public access information">
          <span>Public access</span>
        </Tooltip>
      </Button>
      <Dialog
        open={sourcePublishDialogOpen}
        onClose={() => setSourcePublishDialogOpen(false)}
        PaperProps={{ style: { maxWidth: "800px" } }}
      >
        <DialogTitle>Public access information</DialogTitle>
        <DialogContent style={{ paddingBottom: "0.5rem" }}>
          <div style={{ marginBottom: "1rem" }}>
            You are about to change the public access settings for this source
            page. The data you selected will be available to everyone on the
            internet. Are you sure you want to do this ?
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              margin: "1.5rem 0",
            }}
          >
            <Tooltip
              title={
                manageSourcesAccess
                  ? ""
                  : "You do not have permission to publish this source"
              }
            >
              <div>
                <Button
                  variant="contained"
                  onClick={publish}
                  style={{
                    backgroundColor: publishButton.color,
                    color: "white",
                  }}
                  disabled={
                    !manageSourcesAccess || publishButton.text !== "Publish"
                  }
                >
                  {publishButton.text === "loading" ? (
                    <CircularProgress size={24} />
                  ) : (
                    publishButton.text
                  )}
                </Button>
              </div>
            </Tooltip>
          </div>
          <div>
            <Button
              className={styles.expandButton}
              size="small"
              variant="text"
              onClick={() =>
                setSourcePublishReleaseOpen(!sourcePublishReleaseOpen)
              }
            >
              Release {manageSourcesAccess ? "(optional)" : "list"}
              {sourcePublishReleaseOpen ? <ExpandLess /> : <ExpandMore />}
            </Button>
            {sourcePublishReleaseOpen && (
              <SourcePublishRelease
                sourceReleaseId={sourceReleaseId}
                setSourceReleaseId={setSourceReleaseId}
                setOptions={setOptions}
              />
            )}
          </div>
          {displayOptions && (
            <div>
              <Button
                className={styles.expandButton}
                size="small"
                variant="text"
                onClick={() =>
                  setSourcePublishOptionsOpen(!sourcePublishOptionsOpen)
                }
              >
                Options
                {sourcePublishOptionsOpen ? <ExpandLess /> : <ExpandMore />}
              </Button>
              {sourcePublishOptionsOpen && (
                <SourcePublishOptions
                  options={options}
                  setOptions={setOptions}
                  isElements={isElements}
                />
              )}
            </div>
          )}
          <div>
            <Button
              className={styles.expandButton}
              size="small"
              variant="text"
              onClick={() =>
                setSourcePublishHistoryOpen(!sourcePublishHistoryOpen)
              }
            >
              Version history
              {sourcePublishHistoryOpen ? <ExpandLess /> : <ExpandMore />}
            </Button>
            {sourcePublishHistoryOpen && (
              <SourcePublishHistory sourceId={sourceId} />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SourcePublish;
