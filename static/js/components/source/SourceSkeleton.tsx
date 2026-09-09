import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import Skeleton from "@mui/material/Skeleton";
import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";

import { useCommentPanel } from "../../contexts/CommentPanelContext";
import { useGetProfileQuery } from "../../ducks/profile";
import FavoritesButton from "../listing/FavoritesButton";
import { SlowLoadNotice } from "../Spinner";

interface SourceSkeletonProps {
  /** Known from the route before any data arrives, so it can be shown at once. */
  objId: string;
}

interface SectionProps {
  name: string;
  /** Where the loaded page puts this section when both columns are stacked. */
  order: number;
  titleWidth: string;
  /** Left out for a section that loads collapsed, so only its title shows. */
  bodyHeight?: string;
  buttons?: number;
}

const LEFT_SECTIONS: SectionProps[] = [
  { name: "surveys", order: 2, titleWidth: "5rem", bodyHeight: "2.5rem" },
  {
    name: "photometry",
    order: 4,
    titleWidth: "8rem",
    bodyHeight: "65vh",
    buttons: 4,
  },
  {
    name: "spectroscopy",
    order: 5,
    titleWidth: "9rem",
    bodyHeight: "55vh",
    buttons: 2,
  },
  { name: "followup", order: 10, titleWidth: "7rem", bodyHeight: "10rem" },
  { name: "forcedPhotometry", order: 11, titleWidth: "11rem" },
  { name: "observingRun", order: 12, titleWidth: "14rem", bodyHeight: "8rem" },
];

const ButtonRow = ({ count }: { count: number }) => (
  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
    {[...Array(count)].map((_, index) => (
      <Skeleton
        key={`button-${index}`}
        variant="rounded"
        width={110}
        height={30}
      />
    ))}
  </div>
);

const Section = ({ titleWidth, bodyHeight, buttons = 0 }: SectionProps) => (
  <Paper style={{ padding: "0.5rem" }}>
    <Skeleton variant="text" width={titleWidth} height={32} />
    {bodyHeight && (
      <Skeleton variant="rounded" width="100%" height={bodyHeight} />
    )}
    {buttons > 0 && (
      <div style={{ marginTop: "0.5rem" }}>
        <ButtonRow count={buttons} />
      </div>
    )}
  </Paper>
);

/**
 * The source page's layout, drawn before its data arrives.
 *
 * The object's name is known from the URL, so there is no reason to show
 * nothing at all: the page keeps its shape and fills in, rather than sitting
 * behind a whole-page spinner that is indistinguishable from a hang. The two
 * columns and their sections mirror the loaded page, so the content lands in
 * place instead of being reflowed once it arrives.
 */
const SourceSkeleton = ({ objId }: SourceSkeletonProps) => {
  const theme = useTheme();
  const downLg = useMediaQuery(theme.breakpoints.down("lg"));
  const { data: profile } = useGetProfileQuery();
  const { inline: inlineComments } = useCommentPanel();
  // A profile that has not arrived yet counts as writable: that is the common
  // case, and guessing read-only would drop blocks the page then has to add.
  const canWrite = !profile || (profile.permissions?.length ?? 0) > 0;

  const rightSections: SectionProps[] = [
    {
      name: "annotations",
      order: 6,
      titleWidth: "10rem",
      bodyHeight: "52vh",
      ...(canWrite ? { buttons: 3 } : {}),
    },
    ...(canWrite && inlineComments
      ? [
          {
            name: "comments",
            order: 3,
            titleWidth: "7rem",
            bodyHeight: "60vh",
          },
        ]
      : []),
    { name: "centroidPlot", order: 8, titleWidth: "8rem", bodyHeight: "50vh" },
    { name: "hrDiagram", order: 9, titleWidth: "7rem", bodyHeight: "19rem" },
    {
      name: "classifications",
      order: 13,
      titleWidth: "9rem",
      bodyHeight: "6rem",
    },
    { name: "analysis", order: 14, titleWidth: "10rem", bodyHeight: "8rem" },
    {
      name: "notification",
      order: 15,
      titleWidth: "11rem",
      bodyHeight: "8rem",
    },
  ];

  // Stacked on a narrow screen, the loaded page interleaves the two columns.
  const mainSections = downLg
    ? [...LEFT_SECTIONS, ...rightSections].sort((a, b) => a.order - b.order)
    : LEFT_SECTIONS;

  return (
    <Grid container spacing={1.5}>
      <Grid container size={{ xs: 12, lg: 7 }} spacing={1.5}>
        <Grid size={12}>
          <Paper style={{ padding: "0.5rem" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                columnGap: "0.25rem",
                marginBottom: "0.25rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  columnGap: "0.25rem",
                }}
              >
                {canWrite && <FavoritesButton sourceID={objId} />}
                {/*
                  Deliberately not an <h6>: the loaded page's heading is one, and
                  the frontend tests wait on //h6[text()="<obj id>"] to know the
                  source page is ready. Matching it here would report "loaded"
                  while this placeholder is still on screen.
                */}
                <div
                  style={{
                    lineHeight: "1em",
                    fontSize: "200%",
                    fontWeight: 900,
                    display: "inline-block",
                    margin: 0,
                    color:
                      theme.palette.mode === "dark"
                        ? theme.palette.secondary.main
                        : theme.palette.primary.main,
                  }}
                >
                  {objId}
                </div>
              </div>
              <Skeleton variant="circular" width={26} height={26} />
            </div>

            <Skeleton variant="text" width="30%" height={24} />

            {/* coordinates, redshift, TNS name */}
            <Skeleton variant="text" width="70%" height={24} />
            <Skeleton variant="text" width="55%" height={24} />
            <Skeleton variant="text" width="65%" height={24} />

            {/* the action buttons (search alerts, finding chart, ...) */}
            <div style={{ margin: "0.75rem 0" }}>
              <ButtonRow count={7} />
            </div>

            <Skeleton
              variant="rounded"
              width="100%"
              height="4rem"
              style={{ marginBottom: "0.5rem" }}
            />
            <Skeleton
              variant="text"
              width="40%"
              height={24}
              style={{ marginBottom: "0.5rem" }}
            />

            {/* cutouts: 3 columns over 2 rows */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, minmax(0, 13rem))",
                gap: "0.5rem",
              }}
            >
              {[...Array(6)].map((_, index) => (
                <div key={`thumbnail-${index}`}>
                  <Skeleton variant="text" width="60%" height={20} />
                  <Skeleton
                    variant="rounded"
                    sx={{ width: "100%", height: "auto", aspectRatio: "1 / 1" }}
                  />
                </div>
              ))}
            </div>
          </Paper>
          <SlowLoadNotice overlay />
        </Grid>
        {mainSections.map((section) => (
          <Grid size={12} key={section.name}>
            <Section {...section} />
          </Grid>
        ))}
      </Grid>

      {!downLg && (
        <Grid
          container
          size={5}
          spacing={1.5}
          sx={{ alignContent: "flex-start" }}
        >
          {rightSections.map((section) => (
            <Grid size={12} key={section.name}>
              <Section {...section} />
            </Grid>
          ))}
        </Grid>
      )}
    </Grid>
  );
};

export default SourceSkeleton;
