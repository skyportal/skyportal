// Baselayer components
import { Notifications } from "baselayer/components/Notifications";
import WebSocket from "baselayer/components/WebSocket";
import messageHandler from "baselayer/MessageHandler";

// React and Redux
import React, { useEffect, Suspense } from "react";
import { Provider } from "react-redux";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";

// MUI
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { useTheme } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";
import useMediaQuery from "@mui/material/useMediaQuery";

// Store
import store from "../../store";
import { useAppSelector } from "../../types/hooks";

// Actions
import hydrate from "../../actions";
import * as rotateLogoActions from "../../ducks/logo";
import * as hydrationActions from "../../ducks/hydration";

// Components
import Theme from "../Theme";
import Spinner from "../Spinner";
import NoMatchingRoute from "../NoMatchingRoute";
import SidebarAndHeader from "./SidebarAndHeader";
import ErrorBoundary from "../ErrorBoundary";

const HomePage = React.lazy(() => import("../templates/HomePage"));
const Source = React.lazy(() => import("../source/Source"));
const FavoritesPage = React.lazy(() => import("../listing/FavoritesPage"));
const Groups = React.lazy(() => import("../group/Groups"));
const Group = React.lazy(() => import("../group/Group"));
const Profile = React.lazy(() => import("../user/Profile"));
const CandidateList = React.lazy(() => import("../candidate/CandidateList"));
const ReportsList = React.lazy(
  () => import("../candidate/scan_reports/ReportsList"),
);
const SourceList = React.lazy(() => import("../source/SourceList"));
const UserInfo = React.lazy(() => import("../user/UserInfo"));
const UploadPhotometry = React.lazy(
  () => import("../photometry/UploadPhotometry"),
);
const About = React.lazy(() => import("../About"));
const RunSummary = React.lazy(() => import("../observing_run/RunSummary"));
const SourceAnalysisPage = React.lazy(
  () => import("../source/SourceAnalysisPage"),
);
const ShareDataForm = React.lazy(() => import("../source/ShareDataForm"));
const Filter = React.lazy(() => import("../filter/Filter"));
const ObservingRunPage = React.lazy(
  () => import("../observing_run/ObservingRunPage"),
);
const AllocationPage = React.lazy(() => import("../allocation/AllocationPage"));
const AllocationSummary = React.lazy(
  () => import("../allocation/AllocationSummary"),
);
const InstrumentSummary = React.lazy(
  () => import("../instrument/InstrumentSummary"),
);
const TelescopeSummary = React.lazy(
  () => import("../telescope/TelescopeSummary"),
);
const ObservationPage = React.lazy(
  () => import("../observation/ObservationPage"),
);
const GalaxyPage = React.lazy(() => import("../galaxy/GalaxyPage"));
const SpatialCatalogPage = React.lazy(
  () => import("../spatial_catalog/SpatialCatalogPage"),
);
const FollowupRequestPage = React.lazy(
  () => import("../followup_request/FollowupRequestPage"),
);
const GroupSources = React.lazy(() => import("../group/GroupSources"));
const UserManagement = React.lazy(() => import("../user/UserManagement"));
const UploadSpectrum = React.lazy(() => import("../spectrum/UploadSpectrum"));
const Observability = React.lazy(() => import("../source/Observability"));
const FindingChart = React.lazy(() => import("../FindingChart"));
const Periodogram = React.lazy(() => import("../Periodogram"));
const DBStats = React.lazy(() => import("../DBStats"));
const GcnEvents = React.lazy(() => import("../gcn/GcnEvents"));
const GcnEventPage = React.lazy(() => import("../gcn/GcnEventPage"));
const TelescopePage = React.lazy(() => import("../telescope/TelescopePage"));
const InstrumentPage = React.lazy(() => import("../instrument/InstrumentPage"));
const MMADetectorPage = React.lazy(
  () => import("../mma_detector/MMADetectorPage"),
);
const EarthquakesPage = React.lazy(
  () => import("../earthquake/EarthquakesPage"),
);
const EarthquakePage = React.lazy(() => import("../earthquake/EarthquakePage"));
const AnalysisServicePage = React.lazy(
  () => import("../analysis/AnalysisServicePage"),
);
const RecurringAPIPage = React.lazy(() => import("../RecurringAPIPage"));
const ShiftNoId = React.lazy(() => import("../shift/ShiftNoId"));
const ShiftWithId = React.lazy(() => import("../shift/ShiftWithId"));
const SummarySearch = React.lazy(() => import("../summary/SummarySearch"));
const TagManagement = React.lazy(() => import("../TagManagement"));
const TaxonomyPage = React.lazy(() => import("../taxonomy/TaxonomyPage"));
const SharingServicesPage = React.lazy(
  () => import("../sharing_service/SharingServicesPage"),
);
const SharingServiceSubmissionsPage = React.lazy(
  () => import("../sharing_service/SharingServiceSubmissionsPage"),
);
const MovingObjectObsPlanPage = React.lazy(
  () => import("../moving_object/MovingObjectObsPlanPage"),
);

messageHandler.init(store.dispatch, store.getState);

const useStyles = makeStyles()((theme) => ({
  content: {
    flexGrow: 1,
    transition: theme.transitions.create("margin", {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
    marginTop: "2.5em", // top bar height
    "& a": {
      textDecoration: "none",
      color: "gray",
      fontWeight: "bold",
    },
  },
}));

interface LazyRouteProps {
  Component: React.ElementType;
}

const LazyRoute = ({ Component }: LazyRouteProps) => (
  <Suspense fallback={<Spinner />}>
    <Component />
  </Suspense>
);

interface MainContentInternalProps {
  root: string;
}

const MainContentInternal = ({ root }: MainContentInternalProps) => {
  const { open } = useAppSelector((state) => (state as any).sidebar);
  const { classes } = useStyles();
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down("md"));
  const marginLeft = isSmall ? "0" : open ? "170px" : "65px";

  useEffect(() => {
    store.dispatch(rotateLogoActions.rotateLogo());
    setTimeout(() => {
      store.dispatch(hydrationActions.verifyHydration());
    }, 1400);
    setTimeout(() => {
      const { hydratedList, hydrated } = store.getState().hydration;
      if (hydrated === true) {
        // fully hydrated, do nothing except dashboard refresh
        store.dispatch(hydrate(true) as any);
      } else if (hydratedList?.length > 0) {
        // not fully hydrated, hydrate only missing
        const missing = Array.from(
          [...hydrationActions.DUCKS_TO_HYDRATE].filter(
            (x: any) => !hydratedList.includes(x),
          ),
        );
        store.dispatch(hydrate(false, missing) as any);
      } else {
        // not hydrated at all, hydrate everything
        store.dispatch(hydrate() as any);
      }
      store.dispatch(rotateLogoActions.rotateLogo());
    }, 1500);
  }, []);

  const location = useLocation();
  useEffect(() => {
    document.title = "SkyPortal";
  }, [location.pathname]);

  return (
    <>
      <WebSocket
        url={`${
          window.location.protocol === "https:" ? "wss" : "ws"
        }://${root}websocket`}
        auth_url={`${window.location.protocol}//${root}baselayer/socket_auth_token`}
        messageHandler={messageHandler}
        dispatch={store.dispatch}
      />
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <SidebarAndHeader />
        <div
          role="main"
          className={classes.content}
          style={{
            marginLeft,
            padding: location.pathname === "/" ? 0 : "0.625rem",
          }}
        >
          <Notifications />
          <ErrorBoundary key={location.pathname}>
            <Routes>
              <Route path="/" element={<LazyRoute Component={HomePage} />} />
              <Route
                path="/source/:id"
                element={<LazyRoute Component={Source} />}
              />
              <Route
                path="/favorites"
                element={<LazyRoute Component={FavoritesPage} />}
              />
              <Route
                path="/groups"
                element={<LazyRoute Component={Groups} />}
              />
              <Route
                path="/group/:id"
                element={<LazyRoute Component={Group} />}
              />
              <Route
                path="/profile"
                element={<LazyRoute Component={Profile} />}
              />
              <Route
                path="/candidates"
                element={<LazyRoute Component={CandidateList} />}
              />
              <Route
                path="/candidates/scan_reports"
                element={<LazyRoute Component={ReportsList} />}
              />
              <Route
                path="/sources"
                element={<LazyRoute Component={SourceList} />}
              />
              <Route
                path="/user/:id"
                element={<LazyRoute Component={UserInfo} />}
              />
              <Route
                path="/upload_photometry/:id"
                element={<LazyRoute Component={UploadPhotometry} />}
              />
              <Route path="/about" element={<LazyRoute Component={About} />} />
              <Route
                path="/run/:id"
                element={<LazyRoute Component={RunSummary} />}
              />
              <Route
                path="/source/:obj_id/analysis/:analysis_id"
                element={<LazyRoute Component={SourceAnalysisPage} />}
              />
              <Route
                path="/share_data/:id"
                element={<LazyRoute Component={ShareDataForm} />}
              />
              <Route
                path="/filter/:fid"
                element={<LazyRoute Component={Filter} />}
              />
              <Route
                path="/runs"
                element={<LazyRoute Component={ObservingRunPage} />}
              />
              <Route
                path="/allocations"
                element={<LazyRoute Component={AllocationPage} />}
              />
              <Route
                path="/allocation/:id"
                element={<LazyRoute Component={AllocationSummary} />}
              />
              <Route
                path="/instrument/:id"
                element={<LazyRoute Component={InstrumentSummary} />}
              />
              <Route
                path="/telescope/:id"
                element={<LazyRoute Component={TelescopeSummary} />}
              />
              <Route
                path="/observations"
                element={<LazyRoute Component={ObservationPage} />}
              />
              <Route
                path="/galaxies"
                element={<LazyRoute Component={GalaxyPage} />}
              />
              <Route
                path="/spatial_catalogs"
                element={<LazyRoute Component={SpatialCatalogPage} />}
              />
              <Route
                path="/followup_requests"
                element={<LazyRoute Component={FollowupRequestPage} />}
              />
              <Route
                path="/group_sources/:id"
                element={<LazyRoute Component={GroupSources} />}
              />
              <Route
                path="/user_management"
                element={<LazyRoute Component={UserManagement} />}
              />
              <Route
                path="/upload_spectrum/:id"
                element={<LazyRoute Component={UploadSpectrum} />}
              />
              <Route
                path="/observability/:id"
                element={<LazyRoute Component={Observability} />}
              />
              <Route
                path="/source/:id/finder"
                element={<LazyRoute Component={FindingChart} />}
              />
              <Route
                path="/source/:id/periodogram"
                element={<LazyRoute Component={Periodogram} />}
              />
              <Route
                path="/db_stats"
                element={<LazyRoute Component={DBStats} />}
              />
              <Route
                path="/gcn_events"
                element={<LazyRoute Component={GcnEvents} />}
              />
              <Route
                path="/gcn_events/:dateobs"
                element={<LazyRoute Component={GcnEventPage} />}
              />
              <Route
                path="/telescopes"
                element={<LazyRoute Component={TelescopePage} />}
              />
              <Route
                path="/instruments"
                element={<LazyRoute Component={InstrumentPage} />}
              />
              <Route
                path="/mmadetectors"
                element={<LazyRoute Component={MMADetectorPage} />}
              />
              <Route
                path="/earthquakes"
                element={<LazyRoute Component={EarthquakesPage} />}
              />
              <Route
                path="/earthquakes/:event_id"
                element={<LazyRoute Component={EarthquakePage} />}
              />
              <Route
                path="/services"
                element={<LazyRoute Component={AnalysisServicePage} />}
              />
              <Route
                path="/recurring_apis"
                element={<LazyRoute Component={RecurringAPIPage} />}
              />
              <Route
                path="/shifts"
                element={<LazyRoute Component={ShiftNoId} />}
              />
              <Route
                path="/shifts/:id"
                element={<LazyRoute Component={ShiftWithId} />}
              />
              <Route
                path="/summary_search"
                element={<LazyRoute Component={SummarySearch} />}
              />
              <Route
                path="/tag_management"
                element={<LazyRoute Component={TagManagement} />}
              />
              <Route
                path="/taxonomies"
                element={<LazyRoute Component={TaxonomyPage} />}
              />
              <Route
                path="/sharing_services"
                element={<LazyRoute Component={SharingServicesPage} />}
              />
              <Route
                path="/sharing_service/:id/submissions"
                element={
                  <LazyRoute Component={SharingServiceSubmissionsPage} />
                }
              />
              <Route
                path="/moving_objects/obsplan"
                element={<LazyRoute Component={MovingObjectObsPlanPage} />}
              />
              <Route path="*" element={<NoMatchingRoute />} />
            </Routes>
          </ErrorBoundary>
        </div>
      </LocalizationProvider>
    </>
  );
};

const container = document.getElementById("content");
const root = createRoot(container as HTMLElement);

root.render(
  <Provider store={store}>
    <ErrorBoundary>
      <Theme>
        <BrowserRouter basename="/">
          <MainContentInternal root={`${window.location.host}/`} />
        </BrowserRouter>
      </Theme>
    </ErrorBoundary>
  </Provider>,
);
