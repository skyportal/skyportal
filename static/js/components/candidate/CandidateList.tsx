import { useGetProfileQuery, useIsReadOnly } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useEffect, useRef, useState } from "react";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import {
  useGetCandidatesQuery,
  useGetAnnotationsInfoQuery,
  useGenerateSurveyThumbnailMutation,
} from "../../ducks/candidate/candidates";

import { makeStyles } from "tss-react/mui";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ArrowUpward from "@mui/icons-material/ArrowUpward";
import ArrowDownward from "@mui/icons-material/ArrowDownward";
import SortIcon from "@mui/icons-material/Sort";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import Paper from "@mui/material/Paper";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { ViewportList } from "react-viewport-list";

import { showNotification } from "baselayer/components/Notifications";
import ThumbnailList from "../thumbnail/ThumbnailList";
import SaveCandidateButton from "./SaveCandidateButton";
import FilterCandidateList from "./FilterCandidateList";
import ScanningPageCandidateAnnotations, {
  getAnnotationValueString,
} from "./ScanningPageCandidateAnnotations";
import EditSourceGroups from "../source/EditSourceGroups";
import RejectButton from "../RejectButton";
import VegaPhotometry from "../plot/VegaPhotometry";
import Spinner from "../Spinner";
import AddClassificationsScanningPage from "./AddClassificationsScanningPage";
import Button from "../Button";
import DisplayPhotStats from "../source/DisplayPhotStats";
import CandidatePlugins from "./CandidatePlugins";

import { dec_to_dms, ra_to_hours } from "../../units";

import * as candidatesActions from "../../ducks/candidate/candidates";
import { photometryMinimalApi } from "../../ducks/photometry_minimal";

const numPerPage = 50;

const useStyles = makeStyles()((theme) => ({
  listPaper: {
    borderColor: (theme.palette.grey as any)[350],
    borderWidth: "2px",
    marginBottom: "1rem",
  },
  listItem: {
    padding: 0,
    margin: 0,
    minWidth: "100%",
    display: "flex",
    flexDirection: "column",
  },
  candidatePaper: {
    display: "grid",
    padding: "0.5rem",
    alignItems: "center",
    gridColumnGap: 0,
    gridRowGap: "0.5rem",
    justifyContent: "space-between",
    // we change the order of the children and the layout based on the screen size
    [theme.breakpoints.up("lg")]: {
      gridTemplateColumns: "32% 16% 32% 20%",
      gridTemplateAreas: `"thumbnails info photometry annotations"`,
    },
    [theme.breakpoints.down("lg")]: {
      gridTemplateAreas: `"thumbnails info" "photometry annotations"`,
      gridTemplateColumns: "60% 40%",
    },
    [theme.breakpoints.down("sm")]: {
      gridTemplateAreas: `"info" "thumbnails" "photometry" "annotations"`,
      gridTemplateColumns: "100%",
    },
  },
  thumbnailsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(9rem, 1fr))",
    columnGap: 0,
    rowGap: "0.5rem",
    gridAutoFlow: "row",
  },
  backToTop: {
    position: "absolute",
    bottom: 0,
    right: 0,
    display: "flex",
    gap: "1rem",
  },
  groupsList: {
    display: "flex",
    flexDirection: "row",
    height: "1.6rem",
    alignItems: "center",
    gap: "0.1rem",
  },
  classificationsList: {
    display: "flex",
    flexFlow: "row wrap",
    alignItems: "center",
  },
  spinnerDiv: {
    paddingTop: "2rem",
  },
  infoItem: {
    display: "flex",
    "& > span": {
      paddingLeft: "0.25rem",
      paddingBottom: "0.1rem",
    },
    flexFlow: "row wrap",
    paddingBottom: "0.25rem",
  },
  infoItemPadded: {
    "& > span": {
      paddingLeft: "0.25rem",
      paddingBottom: "0.1rem",
    },
    paddingBottom: "0.25rem",
  },
  saveCandidateButton: {
    margin: "0.25rem 0",
  },
  sortButtton: {
    "&:hover": {
      color: theme.palette.primary.main,
    },
  },
  chip: {
    margin: theme.spacing(0.2),
  },
  position: {
    fontWeight: "bold",
    fontSize: "105%",
  },
  idButton: {
    textTransform: "none",
    marginBottom: theme.spacing(0.5),
    fontSize: "0.9rem",
  },
  scrollContainer: {
    maxHeight: "calc(100vh - 12.5rem)",
    width: "100%",
    display: "flex",
    flexDirection: "column",
    overflowX: "hidden",
    overflowY: "auto",
  },
}));

const getMostRecentClassification = (classifications: any[]) => {
  // Display the most recent non-zero probability class
  const filteredClasses = classifications?.filter(
    (i: any) => i.probability > 0,
  );
  const sortedClasses = filteredClasses?.sort((a: any, b: any) =>
    a.modified < b.modified ? 1 : -1,
  );
  const recentClassification =
    sortedClasses?.length > 0 ? `${sortedClasses[0].classification}` : null;

  return recentClassification;
};

interface CustomSortToolbarProps {
  setQueryInProgress: (...a: any[]) => void;
  filterGroups: any[];
  filterFormData?: Record<string, any> | null;
  loaded: boolean;
  sortOrder?: string | null;
  setSortOrder: (...a: any[]) => void;
  setSearchParams: (params: Record<string, any>) => void;
}

const CustomSortToolbar = ({
  filterGroups,
  filterFormData = null,
  setQueryInProgress,
  loaded,
  sortOrder = null,
  setSortOrder,
  setSearchParams,
}: CustomSortToolbarProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const { selectedAnnotationSortOptions } = useAppSelector(
    (state) => state["candidates"],
  );

  const handleSort = async () => {
    const calculateSortOrder = () => {
      // 1. click once to sort by ascending order
      if (sortOrder === null) {
        return "asc";
      }
      // 2. click again to sort by descending order
      if (sortOrder === "asc") {
        return "desc";
      }
      // 3. click again to remove sorting
      return null;
    };
    const newSortOrder = calculateSortOrder();
    setSortOrder(newSortOrder);

    setQueryInProgress(true);
    let data: any = {
      pageNumber: 1,
      numPerPage,
      groupIDs: filterGroups?.map((g: any) => g.id).join(),
    };
    if (filterFormData !== null) {
      data = {
        ...data,
        ...filterFormData,
      };
    }
    // apply the sorting last, in case we need to overwrite
    // the sorting from the filterFormData
    data = {
      ...data,
      sortByAnnotationOrigin: newSortOrder
        ? selectedAnnotationSortOptions.origin
        : null,
      sortByAnnotationKey: newSortOrder
        ? selectedAnnotationSortOptions.key
        : null,
      sortByAnnotationOrder: newSortOrder,
    };

    dispatch(
      candidatesActions.setCandidatesAnnotationSortOptions({
        ...selectedAnnotationSortOptions,
        order: newSortOrder,
      }),
    );

    // Trigger a new search; the query result drives the loading state.
    setSearchParams(data);
  };

  // Wait until sorted data is received before rendering the toolbar
  return loaded ? (
    <Tooltip title="Sort on Selected Annotation">
      <span>
        <IconButton
          onClick={handleSort}
          disabled={selectedAnnotationSortOptions === null}
          className={classes.sortButtton}
          data-testid="sortOnAnnotationButton"
          size="large"
        >
          <>
            <SortIcon />
            {sortOrder !== null && sortOrder === "asc" && <ArrowUpward />}
            {sortOrder !== null && sortOrder === "desc" && <ArrowDownward />}
          </>
        </IconButton>
      </span>
    </Tooltip>
  ) : (
    <span />
  );
};

interface CandidateThumbnailsProps {
  id: string;
  ra: number;
  dec: number;
  thumbnails?: any[] | null;
}

const CandidateThumbnails = ({
  id,
  ra,
  dec,
  thumbnails = null,
}: CandidateThumbnailsProps) => {
  const { classes } = useStyles();
  const [generateSurveyThumbnailMutation] =
    useGenerateSurveyThumbnailMutation();

  const [ps1GenerationInProgressList, setPS1GenerationInProgressList] =
    useState<any[]>([]);
  const generateSurveyThumbnail = (objID: string) => {
    setPS1GenerationInProgressList([...ps1GenerationInProgressList, objID]);
    generateSurveyThumbnailMutation(objID)
      .unwrap()
      .finally(() => {
        setPS1GenerationInProgressList(
          ps1GenerationInProgressList.filter((ps1_id) => ps1_id !== objID),
        );
      });
  };

  const hasPS1 = thumbnails?.map((t: any) => t.type)?.includes("ps1");
  const displayTypes = hasPS1
    ? ["new", "ref", "sub", "sdss", "ls", "ps1"]
    : ["new", "ref", "sub", "sdss", "ls"];
  return (
    <div>
      {!thumbnails ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div>
          <div className={classes.thumbnailsGrid}>
            <ThumbnailList
              ra={ra}
              dec={dec}
              thumbnails={thumbnails}
              size="100%"
              minSize="6rem"
              maxSize="8.8rem"
              titleSize="0.7rem"
              displayTypes={displayTypes}
              useGrid={false}
              noMargin
            />
          </div>
          {!hasPS1 && (
            <Button
              primary
              disabled={ps1GenerationInProgressList.includes(id)}
              size="small"
              onClick={() => {
                generateSurveyThumbnail(id);
              }}
              data-testid={`generatePS1Button${id}`}
            >
              Generate PS1 Cutout
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

interface CandidateInfoProps {
  candidateObj: any;
  filterGroups: any[];
  selectedAnnotationSortOptions?: {
    origin: string;
    key: string;
    order?: string;
  } | null;
}

const CandidateInfo = ({
  candidateObj,
  filterGroups,
  selectedAnnotationSortOptions = null,
}: CandidateInfoProps) => {
  const { classes } = useStyles();

  const allGroups = (useGetGroupsQuery().data?.all ?? []).filter(
    (g) => !g["single_user_group"],
  );
  const userAccessibleGroups = useGetGroupsQuery().data?.userAccessible ?? [];
  const isReadOnly = useIsReadOnly();

  const candidateHasAnnotationWithSelectedKey = (obj: any) => {
    const annotation = obj.annotations.find(
      (a: any) => a.origin === selectedAnnotationSortOptions?.origin,
    );
    if (annotation === undefined) {
      return false;
    }
    return (selectedAnnotationSortOptions?.key as string) in annotation.data;
  };

  const getCandidateSelectedAnnotationValue = (obj: any) => {
    const annotation = obj.annotations.find(
      (a: any) => a.origin === selectedAnnotationSortOptions?.origin,
    );
    return getAnnotationValueString(
      annotation.data[selectedAnnotationSortOptions?.key as string],
    );
  };

  const recentHumanClassification =
    candidateObj.classifications && candidateObj.classifications.length > 0
      ? getMostRecentClassification(
          candidateObj.classifications.filter(
            (c: any) => c?.ml === false || c?.ml === null,
          ),
        )
      : null;

  const recentMLClassification =
    candidateObj.classifications && candidateObj.classifications.length > 0
      ? getMostRecentClassification(
          candidateObj.classifications.filter((c: any) => c?.ml === true),
        )
      : null;

  return (
    <div>
      {!candidateObj?.annotations ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div style={{ fontSize: "0.875rem", minWidth: "100%" }}>
          <span>
            <a
              href={`/source/${candidateObj.id}`}
              target="_blank"
              data-testid={candidateObj.id}
              rel="noreferrer"
            >
              <Button primary size="small" className={classes.idButton}>
                {candidateObj.id}&nbsp;
                <OpenInNewIcon fontSize="inherit" />
              </Button>
            </a>
          </span>
          {candidateObj.is_source ? (
            <div>
              <div>
                <Chip size="small" label="Previously Saved" color="primary" />
                <RejectButton objID={candidateObj.id} />
              </div>
              <div className={classes.infoItem}>
                <div className={classes.groupsList}>
                  <b>Saved groups: </b>
                  <EditSourceGroups
                    source={{
                      id: candidateObj.id,
                      currentGroupIds: candidateObj.saved_groups?.map(
                        (g: any) => g.id,
                      ),
                    }}
                    groups={allGroups}
                    icon
                  />
                </div>
                <span>
                  {candidateObj.saved_groups?.map((group: any) => (
                    <Chip
                      label={
                        group.nickname
                          ? group.nickname.substring(0, 15)
                          : group.name.substring(0, 15)
                      }
                      key={group.id}
                      size="small"
                      className={classes.chip}
                    />
                  ))}
                </span>
              </div>
            </div>
          ) : (
            <div>
              <Chip size="small" label="NOT SAVED" />
              <RejectButton objID={candidateObj.id} />
            </div>
          )}
          {/* If candidate is either unsaved or is not yet saved to all groups being filtered on, show the "Save to..." button */}{" "}
          {!isReadOnly &&
            Boolean(
              !candidateObj.is_source ||
              (candidateObj.is_source &&
                filterGroups?.filter(
                  (g) =>
                    !candidateObj.saved_groups
                      ?.map((x: any) => x.id)
                      ?.includes(g.id),
                ).length),
            ) && (
              <div className={classes.saveCandidateButton}>
                <SaveCandidateButton
                  candidate={candidateObj}
                  userGroups={
                    // Filter out groups the candidate is already saved to
                    candidateObj.is_source
                      ? userAccessibleGroups?.filter(
                          (g) =>
                            !candidateObj.saved_groups
                              ?.map((x: any) => x.id)
                              ?.includes(g.id),
                        )
                      : userAccessibleGroups
                  }
                  filterGroups={
                    // Filter out groups the candidate is already saved to
                    candidateObj.is_source
                      ? filterGroups?.filter(
                          (g) =>
                            !candidateObj.saved_groups
                              ?.map((x: any) => x.id)
                              ?.includes(g.id),
                        )
                      : filterGroups
                  }
                />
              </div>
            )}
          {/* if we have associated_objs, show their IDs here (clickable, send to source page in another tab when clicked) */}
          {candidateObj.associated_objs &&
            candidateObj.associated_objs.length > 0 && (
              <div className={classes.infoItem}>
                <b>Matches with: </b>
                {candidateObj.associated_objs.map((a: any) => (
                  <span
                    key={a.obj_id}
                    className={(classes as any).associatedObj}
                  >
                    <a
                      href={`/source/${a.obj_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {a.obj_id}
                    </a>
                  </span>
                ))}
              </div>
            )}
          {candidateObj.last_detected_at && (
            <div className={classes.infoItem}>
              <b>Last detected: </b>
              <span>
                {
                  (
                    String(candidateObj.last_detected_at).split(".")[0] ?? ""
                  ).split("T")[1]
                }
                &nbsp;&nbsp;
                {
                  (
                    String(candidateObj.last_detected_at).split(".")[0] ?? ""
                  ).split("T")[0]
                }
              </span>
            </div>
          )}
          <div className={classes.infoItem}>
            <b>Coordinates: </b>
            <div>
              <span className={classes.position}>
                {ra_to_hours(candidateObj.ra)} &nbsp;
                {dec_to_dms(candidateObj.dec)}
              </span>
            </div>
            <div>
              (&alpha;,&delta;= {candidateObj.ra.toFixed(3)}, &nbsp;
              {candidateObj.dec.toFixed(3)})
            </div>
            <div>
              (l,b= {candidateObj.gal_lon.toFixed(3)}, &nbsp;
              {candidateObj.gal_lat.toFixed(3)})
            </div>
          </div>
          <div className={classes.infoItem}>
            <CandidatePlugins {...({ candidate: candidateObj } as any)} />
          </div>
          {candidateObj.photstats && (
            <div className={classes.infoItem}>
              <DisplayPhotStats
                photstats={candidateObj.photstats[0]}
                display_header
              />
            </div>
          )}
          <div className={classes.infoItemPadded}>
            <b>Classification(s): </b>
            <AddClassificationsScanningPage obj_id={candidateObj.id} />
            <div className={classes.classificationsList}>
              {recentHumanClassification && (
                <span>
                  <Chip
                    size="small"
                    label={recentHumanClassification}
                    color="primary"
                    className={classes.chip}
                  />
                </span>
              )}
              {recentMLClassification && (
                <span>
                  <Chip
                    size="small"
                    label={
                      <span
                        style={
                          {
                            display: "flex",
                            direction: "row",
                            alignItems: "center",
                          } as any
                        }
                      >
                        <Tooltip title="classification from an ML classifier">
                          <span>{`ML: ${recentMLClassification}`}</span>
                        </Tooltip>
                      </span>
                    }
                    className={classes.chip}
                  />
                </span>
              )}
            </div>
          </div>
          {selectedAnnotationSortOptions !== null &&
            candidateHasAnnotationWithSelectedKey(candidateObj) && (
              <div className={classes.infoItem}>
                <b>
                  {selectedAnnotationSortOptions.key} (
                  {selectedAnnotationSortOptions.origin}):
                </b>
                <span>{getCandidateSelectedAnnotationValue(candidateObj)}</span>
              </div>
            )}
        </div>
      )}
    </div>
  );
};

interface CandidatePhotometryProps {
  sourceId: string;
}

const CandidatePhotometry = ({ sourceId }: CandidatePhotometryProps) => (
  <div>
    <VegaPhotometry
      sourceId={sourceId}
      style={{
        width: "68%",
        height: "100%",
        minHeight: "18rem",
        maxHeight: "18rem",
      }}
    />
  </div>
);

interface CandidateAutoannotationsProps {
  annotations?: any[] | null;
  filterGroups?: any[];
}

const CandidateAutoannotations = ({
  annotations = null,
  filterGroups = [],
}: CandidateAutoannotationsProps) => (
  <div>
    {!annotations ? (
      <div>
        <CircularProgress />
      </div>
    ) : (
      <div
        style={{
          overflowWrap: "break-word",
        }}
      >
        {annotations && (
          <ScanningPageCandidateAnnotations
            annotations={annotations}
            filterGroups={filterGroups || []}
          />
        )}
      </div>
    )}
  </div>
);

interface CandidateProps {
  candidate: any;
  filterGroups?: any[];
  index: number;
  totalMatches: number;
}

const Candidate = ({
  candidate,
  filterGroups = [],
  index,
  totalMatches,
}: CandidateProps) => {
  const { classes } = useStyles();
  return (
    <Paper
      variant="outlined"
      className={classes.listPaper}
      data-testid={`candidate-${index}`}
    >
      <div className={classes.candidatePaper}>
        <div style={{ gridArea: "thumbnails" }}>
          <CandidateThumbnails
            id={candidate.id}
            ra={candidate.ra}
            dec={candidate.dec}
            thumbnails={candidate.thumbnails}
          />
        </div>
        <div style={{ gridArea: "info", padding: "0 0 0 0.25rem" }}>
          <CandidateInfo candidateObj={candidate} filterGroups={filterGroups} />
        </div>
        <div style={{ gridArea: "photometry" }}>
          <CandidatePhotometry sourceId={candidate.id} />
        </div>
        <div
          style={{
            gridArea: "annotations",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            minHeight: "100%",
            paddingLeft: "1rem",
          }}
        >
          <CandidateAutoannotations
            annotations={candidate.annotations}
            filterGroups={filterGroups}
          />
          {/* here show a counter, saying this is candidate n/m */}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              paddingTop: "0.5rem",
            }}
          >
            <Typography fontWeight="bold">
              {`${index}/${totalMatches}`}
            </Typography>
          </div>
        </div>
      </div>
    </Paper>
  );
};

Candidate.displayName = "Candidate";

const CandidateList = () => {
  const ref = useRef<any>(null);
  const [queryInProgress, setQueryInProgress] = useState(false);
  const [filterGroups, setFilterGroups] = useState<any[]>([]);
  const { classes } = useStyles();

  // The active query args for `getCandidates`. `null` until the first search is
  // submitted; setting it (with a new `pageNumber`) drives a refetch.
  const [searchParams, setSearchParams] = useState<Record<string, any> | null>(
    null,
  );

  const { selectedAnnotationSortOptions } = useAppSelector(
    (state) => state["candidates"],
  );

  // Server list, paged + accumulated by the RTK Query `merge` in the duck.
  const { data: candidatesData, isFetching: candidatesFetching } =
    useGetCandidatesQuery(searchParams ?? {}, { skip: searchParams === null });
  const candidates = candidatesData?.candidates ?? null;
  const pageNumber = candidatesData?.pageNumber ?? 1;
  const totalMatches = candidatesData?.totalMatches ?? 0;
  const queryID = candidatesData?.queryID ?? null;

  const [sortOrder, setSortOrder] = useState(
    selectedAnnotationSortOptions ? selectedAnnotationSortOptions.order : null,
  );

  const scanningProfiles = (useGetProfileQuery().data?.preferences as any)
    ?.scanningProfiles;

  const defaultScanningProfile = scanningProfiles?.find(
    (profile: any) => profile.default,
  );

  const userAccessibleGroups = useGetGroupsQuery().data?.userAccessible ?? [];

  // Prefetch the annotation-info cache so child components (filter form,
  // preferences) read it from the shared RTK Query cache.
  useGetAnnotationsInfoQuery(undefined);

  const filterFormData = useAppSelector(
    (state) => state["candidates"].filterFormData,
  );

  const dispatch = useAppDispatch();

  // Mirror the query's loading state into `queryInProgress` so the existing
  // spinners (also toggled by the filter/sort handlers) stay in sync.
  useEffect(() => {
    setQueryInProgress(candidatesFetching);
  }, [candidatesFetching]);

  useEffect(() => {
    if (defaultScanningProfile?.sortingOrder) {
      dispatch(
        candidatesActions.setCandidatesAnnotationSortOptions({
          origin: defaultScanningProfile.sortingOrigin,
          key: defaultScanningProfile.sortingKey,
          order: defaultScanningProfile.sortingOrder,
        }),
      );
      setSortOrder(defaultScanningProfile.sortingOrder);
    }
  }, [dispatch, defaultScanningProfile]);

  // Refresh photometry cache on page change
  useEffect(() => {
    dispatch(photometryMinimalApi.util.invalidateTags(["Photometry"]));
  }, [pageNumber, dispatch]);

  const fetchPage = (offset: number) => {
    if (!queryInProgress && (candidates?.length ?? 0) < totalMatches) {
      dispatch(showNotification("Loading more candidates..."));
      setSearchParams({
        ...(searchParams ?? {}),
        pageNumber: pageNumber + offset,
        numPerPage,
        queryID,
      });
    }
  };

  // ViewportList only knows a candidate's position within the current page, so
  // add the page offset to get its position in the full result set.
  const globalIndex = (pageIndex: number) =>
    (pageNumber - 1) * numPerPage + pageIndex + 1;

  return (
    <div style={{ position: "relative" }}>
      <div>
        <FilterCandidateList
          userAccessibleGroups={userAccessibleGroups}
          setQueryInProgress={setQueryInProgress}
          setFilterGroups={setFilterGroups}
          numPerPage={numPerPage}
          annotationFilterList=""
          setSortOrder={setSortOrder}
          setSearchParams={setSearchParams}
        />
        <Box style={{ marginTop: "0.75rem" }}>
          {queryInProgress ? (
            <Spinner />
          ) : (
            <div>
              <Paper
                variant="outlined"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "1rem",
                }}
              >
                <div style={{ padding: "0.5rem 0.5rem 0.5rem 1rem" }}>
                  <Typography variant="h6">
                    Found {totalMatches} candidates.
                  </Typography>
                </div>
                <div style={{ display: "flex", flexDirection: "row" }}>
                  <CustomSortToolbar
                    filterGroups={filterGroups}
                    filterFormData={filterFormData}
                    setQueryInProgress={setQueryInProgress}
                    loaded={!queryInProgress}
                    sortOrder={sortOrder}
                    setSortOrder={setSortOrder}
                    setSearchParams={setSearchParams}
                  />
                </div>
              </Paper>
              <div className={classes.scrollContainer} ref={ref}>
                <ViewportList viewportRef={ref} count={candidates?.length || 0}>
                  {(index: number) => (
                    <div
                      key={candidates[index].id}
                      className={classes.listItem}
                    >
                      <Candidate
                        candidate={candidates[index]}
                        filterGroups={filterGroups}
                        index={globalIndex(index)}
                        totalMatches={totalMatches}
                      />
                    </div>
                  )}
                </ViewportList>
              </div>
            </div>
          )}
        </Box>
      </div>
      <div className={classes.backToTop}>
        <Button
          primary
          onClick={() => fetchPage(-1)}
          size="small"
          disabled={pageNumber === 1 || queryInProgress}
        >
          <ArrowBackIcon />
          Previous
        </Button>
        <Button
          primary
          onClick={() => fetchPage(1)}
          size="small"
          disabled={pageNumber * numPerPage >= totalMatches || queryInProgress}
        >
          Next
          <ArrowForwardIcon />
        </Button>
        <Button
          primary
          onClick={() => window.scrollTo({ top: 0 })}
          size="small"
        >
          Back to top <ArrowUpward />
        </Button>
      </div>
    </div>
  );
};

export default CandidateList;
