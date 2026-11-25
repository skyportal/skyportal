import { useGetProfileQuery } from "../../ducks/profile";
import { type ReactNode, useState } from "react";
import Tooltip, { type TooltipProps } from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { alpha, type Theme } from "@mui/material/styles";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import ThumbUpOutlinedIcon from "@mui/icons-material/ThumbUpOutlined";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import ThumbDownOutlinedIcon from "@mui/icons-material/ThumbDownOutlined";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import {
  useAddClassificationVoteMutation,
  useDeleteClassificationMutation,
} from "../../ducks/source";
import { useGetConfigQuery } from "../../ducks/config";

export const cardTooltipSlotProps: TooltipProps["slotProps"] = {
  tooltip: {
    sx: (theme: Theme) => ({
      p: 0,
      maxWidth: 320,
      color: "text.primary",
      bgcolor:
        theme.palette.mode === "dark" ? "background.paper" : "common.white",
      border: 1,
      borderColor: "divider",
      borderRadius: 2,
      boxShadow: theme.shadows[8],
      fontSize: "0.85rem",
      fontWeight: 400,
    }),
  },
};

interface VoteButtonProps {
  id: string;
  up?: boolean;
  active: boolean;
  count?: number;
  onClick: () => void;
}

export const VoteButton = ({
  id,
  up = false,
  active,
  count,
  onClick,
}: VoteButtonProps) => {
  const color = up ? "success" : "error";
  const Icon = up
    ? active
      ? ThumbUpIcon
      : ThumbUpOutlinedIcon
    : active
      ? ThumbDownIcon
      : ThumbDownOutlinedIcon;
  return (
    <Button
      id={id}
      size="small"
      onClick={onClick}
      aria-label={up ? "Upvote" : "Downvote"}
      endIcon={<Icon />}
      sx={(theme: Theme) => {
        const base = active
          ? theme.palette[color].main
          : theme.palette.text.primary;
        return {
          minWidth: 0,
          px: 1.25,
          py: 0.25,
          borderRadius: 999,
          fontWeight: 600,
          fontVariantNumeric: "tabular-nums",
          color: active ? `${color}.main` : "text.secondary",
          bgcolor: alpha(base, active ? 0.12 : 0.05),
          "&:hover": { bgcolor: alpha(base, active ? 0.2 : 0.1) },
          "& .MuiButton-endIcon": { ml: count === undefined ? 0 : 0.5, mr: 0 },
          "& .MuiButton-endIcon svg": { fontSize: "1rem" },
        };
      }}
    >
      {count}
    </Button>
  );
};

interface ClassificationCardProps {
  title: string;
  color?: string;
  action?: ReactNode;
  footer: ReactNode;
  children?: ReactNode;
}

export const ClassificationCard = ({
  title,
  color,
  action,
  footer,
  children,
}: ClassificationCardProps) => (
  <Box sx={{ minWidth: 220 }}>
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        minHeight: 40,
        pl: 1.5,
        pr: 0.5,
      }}
    >
      {color && (
        <Box
          sx={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            bgcolor: color,
            flexShrink: 0,
          }}
        />
      )}
      <Typography sx={{ flex: 1, fontWeight: 600, fontSize: "0.95rem" }}>
        {title}
      </Typography>
      {action}
    </Box>
    {children && <Divider />}
    {children}
    <Divider />
    <Box sx={{ display: "flex", gap: 0.75, px: 1.5, py: 1 }}>{footer}</Box>
  </Box>
);

const formatProbability = (probability: any) =>
  typeof probability === "number" ? `${Math.round(probability * 100)}%` : "–";

interface ClassificationRowProps {
  classifications: Record<string, any>[];
  fontSize?: string;
}

const ClassificationRow = ({
  classifications,
  fontSize = "1rem",
}: ClassificationRowProps) => {
  const dispatch = useAppDispatch();
  const [addClassificationVote] = useAddClassificationVoteMutation();
  const [deleteClassificationMutation] = useDeleteClassificationMutation();
  const { data: currentUser } = useGetProfileQuery();
  const classificationsClasses = (useGetConfigQuery().data as any)
    ?.classificationsClasses;
  const [dialogOpen, setDialogOpen] = useState(false);

  const classification = classifications[0]!;

  const addVote = (vote: number) => {
    addClassificationVote({
      classification_id: classification["id"],
      data: { vote },
    })
      .unwrap()
      .then(() => {
        dispatch(showNotification("Vote registered"));
      })
      .catch(() => {
        // error notification handled by the baseQuery
      });
  };

  const deleteClassification = () => {
    deleteClassificationMutation(classification["id"])
      .unwrap()
      .then(() => {
        dispatch(showNotification("Classification deleted"));
        setDialogOpen(false);
      })
      .catch(() => {
        // error notification handled by the baseQuery
      });
  };

  const votes = classification["votes"] || [];
  const upvotes = votes.filter((v: any) => v.vote === 1);
  const downvotes = votes.filter((v: any) => v.vote === -1);
  const upvoted = upvotes.some((v: any) => v.voter_id === currentUser?.id);
  const downvoted = downvotes.some((v: any) => v.voter_id === currentUser?.id);

  const permission =
    currentUser?.permissions.includes("System admin") ||
    currentUser?.permissions.includes("Manage groups") ||
    JSON.parse(window.localStorage.getItem("CURRENT_GROUP_ADMIN") as string) ||
    currentUser?.username === classification["author_name"];

  const isML = Boolean(classification["ml"]);
  const originColor =
    classificationsClasses?.origin && classification["origin"]
      ? classificationsClasses.origin[classification["origin"]]
      : undefined;
  const backgroundColor = originColor
    ? undefined
    : classificationsClasses?.classification?.[
        classification["classification"]
      ] || "#999999";
  const label = `${isML ? "ML: " : ""}${classification["classification"]}${
    classification["probability"] < 0.1 ? "?" : ""
  }`;

  return (
    <>
      <Tooltip
        disableFocusListener
        disableTouchListener
        slotProps={cardTooltipSlotProps}
        title={
          <ClassificationCard
            title={classification["classification"]}
            color={originColor || backgroundColor}
            action={
              permission && (
                <IconButton
                  id="delete_classification"
                  size="small"
                  aria-label="Delete classification"
                  onClick={() => setDialogOpen(true)}
                  sx={{ color: "text.secondary" }}
                >
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              )
            }
            footer={
              <>
                <VoteButton
                  id="up_vote"
                  up
                  active={upvoted}
                  count={upvotes.length}
                  onClick={() => addVote(upvoted ? 0 : 1)}
                />
                <VoteButton
                  id="down_vote"
                  active={downvoted}
                  count={downvotes.length}
                  onClick={() => addVote(downvoted ? 0 : -1)}
                />
              </>
            }
          >
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 1,
                px: 1.5,
                py: 1,
              }}
            >
              {classifications.map((cls) => (
                <Box
                  key={cls["id"]}
                  sx={{ display: "flex", alignItems: "center", gap: 1.5 }}
                >
                  <Typography
                    sx={{
                      minWidth: 40,
                      fontWeight: 600,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {formatProbability(cls["probability"])}
                  </Typography>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="body2">{cls["taxname"]}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {cls["ml"] ? "ML · " : ""}
                      {cls["author_name"]}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </ClassificationCard>
        }
      >
        <Chip
          label={label}
          size="small"
          sx={{
            fontSize,
            fontWeight: "bold",
            color: originColor || (isML ? "#3063ab" : "#000000"),
            ...(backgroundColor && { backgroundColor }),
          }}
        />
      </Tooltip>
      <ConfirmDeletionDialog
        deleteFunction={deleteClassification}
        dialogOpen={dialogOpen}
        closeDialog={() => setDialogOpen(false)}
        resourceName="classification"
      />
    </>
  );
};

interface ShowClassificationProps {
  classifications: Record<string, any>[];
  taxonomyList: Record<string, any>[];
  shortened?: boolean;
  fontSize?: string;
}

function ShowClassification({
  classifications,
  taxonomyList,
  shortened = false,
  fontSize = "1rem",
}: ShowClassificationProps) {
  const { data: config } = useGetConfigQuery() as { data: any };
  const mlMinProbability =
    typeof config?.["mlClassificationMinProbability"] === "number"
      ? (config["mlClassificationMinProbability"] as number)
      : 0;

  // A probability of exactly 0 is an explicit "not this class" label, so don't
  // advertise the object as being of that class (#3483). A null probability
  // means unspecified and is still shown.
  // An ML classifier scores every source it sees, so a low probability is a
  // guess rather than a finding; below the configured threshold it stays on the
  // source and out of this summary, which reads as the object's identity.
  // `classifications` is frozen RTK Query data, so copy before sorting in place.
  // A human classification always takes precedence over an ML one; each row shows
  // its first entry, so put human labels first, then most recent.
  const sorted_classifications = [...(classifications || [])]
    .filter((c) => c["probability"] !== 0)
    .filter(
      (c) =>
        !c["ml"] ||
        typeof c["probability"] !== "number" ||
        c["probability"] >= mlMinProbability,
    )
    .sort((a, b) => {
      const mlA = a["ml"] ? 1 : 0;
      const mlB = b["ml"] ? 1 : 0;
      if (mlA !== mlB) return mlA - mlB;
      return a["created_at"] > b["created_at"] ? -1 : 1;
    });

  const classificationsGrouped = sorted_classifications.reduce(
    (r: Record<string, any[]>, a: any) => {
      r[a.classification] = [...(r[a.classification] || []), a];
      return r;
    },
    {},
  );

  const keys = Object.keys(classificationsGrouped);
  keys.forEach((key) => {
    const group = classificationsGrouped[key] ?? [];
    // The grouped items are the original frozen RTK Query classification
    // objects, so build new objects with the added `taxname` rather than
    // mutating them in place.
    classificationsGrouped[key] = group.map((item: any) => {
      const matchingTaxonomies: any = taxonomyList.filter(
        (i) => i["id"] === item.taxonomy_id,
      );
      const taxname =
        matchingTaxonomies.length > 0
          ? matchingTaxonomies[0].name
          : "Unknown taxonomy";
      return { ...item, taxname };
    });
  });

  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 0.5,
        maxWidth: "100%",
      }}
    >
      {!shortened && <b>Classification: </b>}
      {keys.map((key) => (
        <ClassificationRow
          key={key}
          classifications={classificationsGrouped[key] ?? []}
          fontSize={fontSize}
        />
      ))}
    </Box>
  );
}

export default ShowClassification;
