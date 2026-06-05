import React, { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";

import Typography from "@mui/material/Typography";
import Drawer from "@mui/material/Drawer";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import IconButton from "@mui/material/IconButton";
import { makeStyles } from "tss-react/mui";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import useMediaQuery from "@mui/material/useMediaQuery";
import ExpandMore from "@mui/icons-material/ExpandMore";
import ExpandLess from "@mui/icons-material/ExpandLess";
import MenuIcon from "@mui/icons-material/Menu";

import HomeIcon from "@mui/icons-material/Home";
import StorageIcon from "@mui/icons-material/Storage";
import SearchIcon from "@mui/icons-material/Search";
import StarIcon from "@mui/icons-material/Star";
import GroupWorkIcon from "@mui/icons-material/GroupWork";
import LocalCafeIcon from "@mui/icons-material/LocalCafe";
import SettingsInputAntennaIcon from "@mui/icons-material/SettingsInputAntenna";
import WorkOutlinedIcon from "@mui/icons-material/WorkOutlined";
import SubwayRoundedIcon from "@mui/icons-material/SubwayRounded";
import TroubleshootIcon from "@mui/icons-material/Troubleshoot";
import InfoIcon from "@mui/icons-material/Info";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";

import MyLocationIcon from "@mui/icons-material/MyLocation";
import WifiIcon from "@mui/icons-material/Wifi";
import AbcIcon from "@mui/icons-material/Abc";
import HourglassEmptyOutlinedIcon from "@mui/icons-material/HourglassEmptyOutlined";
import ZoomInOutlinedIcon from "@mui/icons-material/ZoomInOutlined";
import ShareIcon from "@mui/icons-material/Share";
import AnimationIcon from "@mui/icons-material/Animation";
import PieChartIcon from "@mui/icons-material/PieChart";
import TornadoOutlinedIcon from "@mui/icons-material/TornadoOutlined";
import PhotoSizeSelectLargeOutlinedIcon from "@mui/icons-material/PhotoSizeSelectLargeOutlined";
import SentimentSatisfiedIcon from "@mui/icons-material/SentimentSatisfied";
import RestoreIcon from "@mui/icons-material/Restore";
import WallpaperOutlinedIcon from "@mui/icons-material/WallpaperOutlined";
import LocalOfferIcon from "@mui/icons-material/LocalOffer";
import SummarizeIcon from "@mui/icons-material/Summarize";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";

import AssessmentIcon from "@mui/icons-material/Assessment";
import GroupIcon from "@mui/icons-material/Group";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as Actions from "../../ducks/sidebar";

import HeaderContent from "./HeaderContent";
import hydrate from "../../actions";

const drawerWidth = 170;

const useStyles = makeStyles()(
  (theme) =>
    ({
      root: {
        display: "flex",
        padding: 0,
        margin: 0,
      },
      appBar: {
        position: "fixed",
        zIndex: 150,
        transition: theme.transitions.create(["margin", "width"], {
          easing: theme.transitions.easing.sharp,
          duration: theme.transitions.duration.leavingScreen,
        }),
        height: "fit-content",
        background: theme.palette.primary.dark,
        padding: 0,
        margin: 0,
      },
      appBarShift: {
        width: `calc(100% - ${drawerWidth}px)`,
        marginLeft: drawerWidth,
        transition: theme.transitions.create(["margin", "width"], {
          easing: theme.transitions.easing.easeOut,
          duration: theme.transitions.duration.enteringScreen,
        }),
      },
      drawer: {
        maxWidth: drawerWidth,
        flexShrink: 0,
      },
      drawerPaper: {
        zIndex: 140,
        maxWidth: drawerWidth,
        background: theme.palette.primary.light,
        fontSize: "1.2em",
        padding: 0,
      },
      drawerPaperTemporary: {
        zIndex: 140,
        width: "fit-content",
        background: theme.palette.primary.light,
        fontSize: "1.2em",
        padding: 0,
      },
      toolbar: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingLeft: "1.5rem",
        paddingRight: 0,
        [theme.breakpoints.up("md")]: {
          paddingRight: "1rem",
        },
      },
      drawerHeader: {
        display: "flex",
        alignItems: "center",
        // necessary for content to be below app bar
        ...theme.mixins.toolbar,
        paddingTop: "3em",
      },
      link: {
        color: theme.palette.info.main,
        textDecoration: "none",
      },
      bold: {
        color: theme.palette.info.main,
        fontWeight: "bold",
      },
      icon: {
        color: theme.palette.info.main,
      },
      minimized: {
        display: "none",
        transition: theme.transitions.create(["display"], {
          easing: theme.transitions.easing.easeOut,
          duration: theme.transitions.duration.enteringScreen,
        }),
      },
    }) as any,
);

interface SidebarLinkTextProps {
  route?: string;
  title: string;
  open: boolean;
}

const SidebarLinkText = ({ route, title, open }: SidebarLinkTextProps) => {
  const { classes } = useStyles() as any;
  const currentRoute = useLocation().pathname;

  return (
    <ListItemText
      primary={
        <Typography
          className={currentRoute === route ? classes.bold : undefined}
        >
          {title}
        </Typography>
      }
      className={!open ? classes.minimized : undefined}
    />
  );
};

const SidebarAndHeader = () => {
  const { classes } = useStyles() as any;
  const dispatch = useAppDispatch();
  const open = useAppSelector((state) => (state as any).sidebar.open);
  const currentUser = useAppSelector((state) => (state as any).profile);
  const isSmall = useMediaQuery((theme: any) => theme.breakpoints.down("md"));

  const [OtherOpen, setOtherOpen] = React.useState(false);

  const [AdminOpen, setAdminOpen] = React.useState(false);

  const [temporaryOpen, setTemporaryOpen] = React.useState(false);

  const timerRef = useRef<any>(null);
  const TIMEOUT = 700;

  function mouseEnter() {
    if (!temporaryOpen && !open && !isSmall) {
      timerRef.current = setTimeout(() => {
        setTemporaryOpen(true);
      }, TIMEOUT);
    }
  }

  function mouseLeave() {
    clearTimeout(timerRef.current);
    setTemporaryOpen(false);

    setOtherOpen(false);

    setAdminOpen(false);
  }

  const handleToggleSidebarOpen = () => {
    if (open) {
      setOtherOpen(false);

      setAdminOpen(false);
    }
    dispatch(Actions.toggleSidebar());
  };

  useEffect(() => {
    if (isSmall && open) {
      dispatch(Actions.setSidebar(false));
      setTemporaryOpen(false);
    }
  }, [isSmall, dispatch]);

  const drawerType = temporaryOpen || isSmall ? "temporary" : "permanent";

  const hydrateIfDashboardClicked = (url: string) => {
    clearTimeout(timerRef.current);
    if (url === "/") {
      dispatch(hydrate(true));
    }
  };

  return (
    <>
      <AppBar className={classes.appBar}>
        <Toolbar className={classes.toolbar}>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            onClick={handleToggleSidebarOpen}
            edge="start"
            className={(classes as any).menuButton}
          >
            <MenuIcon />
          </IconButton>
          <HeaderContent />
        </Toolbar>
      </AppBar>
      <Drawer
        className={classes.drawer}
        variant={drawerType}
        anchor="left"
        open={open || temporaryOpen}
        onClose={isSmall ? handleToggleSidebarOpen : undefined}
        classes={{
          paper:
            drawerType === "temporary"
              ? classes.drawerPaperTemporary
              : classes.drawerPaper,
        }}
        PaperProps={{ onMouseEnter: mouseEnter, onMouseLeave: mouseLeave }}
      >
        {!isSmall && <div className={classes.drawerHeader} />}
        <List>
          <Link
            to="/"
            onClick={() => hydrateIfDashboardClicked("/")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarDashboardButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <HomeIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/"
                  title="Dashboard"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/sources"
            onClick={() => hydrateIfDashboardClicked("/sources")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarSourcesButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <StorageIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/sources"
                  title="Sources"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/candidates"
            onClick={() => hydrateIfDashboardClicked("/candidates")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarCandidatesButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <SearchIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/candidates"
                  title="Candidates"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/favorites"
            onClick={() => hydrateIfDashboardClicked("/favorites")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarFavoritesButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <StarIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/favorites"
                  title="Favorites"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/groups"
            onClick={() => hydrateIfDashboardClicked("/groups")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarGroupsButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <GroupWorkIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/groups"
                  title="Groups"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/runs"
            onClick={() => hydrateIfDashboardClicked("/runs")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarObserving RunsButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <LocalCafeIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/runs"
                  title="Observing Runs"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/gcn_events"
            onClick={() => hydrateIfDashboardClicked("/gcn_events")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarGCN EventsButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <SettingsInputAntennaIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/gcn_events"
                  title="GCN Events"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/followup_requests"
            onClick={() => hydrateIfDashboardClicked("/followup_requests")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarFollowup RequestsButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <WorkOutlinedIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/followup_requests"
                  title="Followup Requests"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/shifts"
            onClick={() => hydrateIfDashboardClicked("/shifts")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarShiftsButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <SubwayRoundedIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/shifts"
                  title="Shifts"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/summary_search"
            onClick={() => hydrateIfDashboardClicked("/summary_search")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarSummary SearchButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <TroubleshootIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/summary_search"
                  title="Summary Search"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <Link
            to="/about"
            onClick={() => hydrateIfDashboardClicked("/about")}
            className={classes.link}
          >
            <ListItem
              {...({ name: "sidebarAboutButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  <InfoIcon className={classes.icon} />
                </ListItemIcon>
                <SidebarLinkText
                  route="/about"
                  title="About"
                  open={open || temporaryOpen}
                />
              </ListItemButton>
            </ListItem>
          </Link>

          <>
            <ListItem
              {...({ name: "sidebarOtherButton" } as any)}
              disablePadding
              sx={{ display: "block" }}
              className={classes.link}
            >
              <ListItemButton
                sx={{
                  minHeight: 48,
                  justifyContent: open || temporaryOpen ? "initial" : "center",
                  px: 2.5,
                }}
                onClick={() => setOtherOpen(!OtherOpen)}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: open || temporaryOpen ? 2 : "auto",
                    justifyContent: "center",
                  }}
                >
                  {!(open || temporaryOpen) && OtherOpen ? (
                    <ExpandLess />
                  ) : (
                    <MoreHorizIcon className={classes.icon} />
                  )}
                </ListItemIcon>
                <SidebarLinkText title="Other" open={open || temporaryOpen} />
                {(open || temporaryOpen) && OtherOpen ? <ExpandLess /> : null}
                {!OtherOpen && (open || temporaryOpen) ? <ExpandMore /> : null}
              </ListItemButton>
            </ListItem>
            <Collapse in={OtherOpen} timeout="auto" unmountOnExit>
              <Divider />
              <List component="div" disablePadding>
                <Link
                  to="/telescopes"
                  onClick={() => hydrateIfDashboardClicked("/telescopes")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarTelescopesButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <MyLocationIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/telescopes"
                        title="Telescopes"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/instruments"
                  onClick={() => hydrateIfDashboardClicked("/instruments")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarInstrumentsButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <WifiIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/instruments"
                        title="Instruments"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/mmadetectors"
                  onClick={() => hydrateIfDashboardClicked("/mmadetectors")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarMMADetectorsButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <AbcIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/mmadetectors"
                        title="MMADetectors"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/allocations"
                  onClick={() => hydrateIfDashboardClicked("/allocations")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarAllocationsButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <HourglassEmptyOutlinedIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/allocations"
                        title="Allocations"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/observations"
                  onClick={() => hydrateIfDashboardClicked("/observations")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarObservationsButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <ZoomInOutlinedIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/observations"
                        title="Observations"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/sharing_services"
                  onClick={() => hydrateIfDashboardClicked("/sharing_services")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarSharing ServicesButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <ShareIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/sharing_services"
                        title="Sharing Services"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/moving_objects/obsplan"
                  onClick={() =>
                    hydrateIfDashboardClicked("/moving_objects/obsplan")
                  }
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarMoving ObjectsButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <AnimationIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/moving_objects/obsplan"
                        title="Moving Objects"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/earthquakes"
                  onClick={() => hydrateIfDashboardClicked("/earthquakes")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarEarthquakesButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <PieChartIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/earthquakes"
                        title="Earthquakes"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/galaxies"
                  onClick={() => hydrateIfDashboardClicked("/galaxies")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarGalaxiesButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <TornadoOutlinedIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/galaxies"
                        title="Galaxies"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/spatial_catalogs"
                  onClick={() => hydrateIfDashboardClicked("/spatial_catalogs")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarSpatial CatalogsButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <PhotoSizeSelectLargeOutlinedIcon
                          className={classes.icon}
                        />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/spatial_catalogs"
                        title="Spatial Catalogs"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/services"
                  onClick={() => hydrateIfDashboardClicked("/services")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarAnalysis ServicesButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <SentimentSatisfiedIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/services"
                        title="Analysis Services"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/recurring_apis"
                  onClick={() => hydrateIfDashboardClicked("/recurring_apis")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarRecurring APIButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <RestoreIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/recurring_apis"
                        title="Recurring API"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                <Link
                  to="/taxonomies"
                  onClick={() => hydrateIfDashboardClicked("/taxonomies")}
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarTaxonomiesButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <WallpaperOutlinedIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/taxonomies"
                        title="Taxonomies"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>

                {(currentUser.permissions?.includes("Manage sources") ||
                  currentUser.permissions?.includes("System admin") ||
                  false) && (
                  <Link
                    to="/tag_management"
                    onClick={() => hydrateIfDashboardClicked("/tag_management")}
                    className={classes.link}
                  >
                    <ListItem
                      {...({ name: "sidebarTag ManagementButton" } as any)}
                      disablePadding
                      sx={{ display: "block" }}
                    >
                      <ListItemButton
                        sx={{
                          minHeight: 48,
                          justifyContent:
                            open || temporaryOpen ? "initial" : "center",
                          px: 2.5,
                        }}
                      >
                        <ListItemIcon
                          sx={{
                            minWidth: 0,
                            mr: open || temporaryOpen ? 2 : "auto",
                            justifyContent: "center",
                          }}
                        >
                          <LocalOfferIcon className={classes.icon} />
                        </ListItemIcon>
                        <SidebarLinkText
                          route="/tag_management"
                          title="Tag Management"
                          open={open || temporaryOpen}
                        />
                      </ListItemButton>
                    </ListItem>
                  </Link>
                )}

                <Link
                  to="/candidates/scan_reports"
                  onClick={() =>
                    hydrateIfDashboardClicked("/candidates/scan_reports")
                  }
                  className={classes.link}
                >
                  <ListItem
                    {...({ name: "sidebarScanning reportButton" } as any)}
                    disablePadding
                    sx={{ display: "block" }}
                  >
                    <ListItemButton
                      sx={{
                        minHeight: 48,
                        justifyContent:
                          open || temporaryOpen ? "initial" : "center",
                        px: 2.5,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open || temporaryOpen ? 2 : "auto",
                          justifyContent: "center",
                        }}
                      >
                        <SummarizeIcon className={classes.icon} />
                      </ListItemIcon>
                      <SidebarLinkText
                        route="/candidates/scan_reports"
                        title="Scanning report"
                        open={open || temporaryOpen}
                      />
                    </ListItemButton>
                  </ListItem>
                </Link>
              </List>
              <Divider />
            </Collapse>
          </>

          {(currentUser.permissions?.includes("Manage users") ||
            currentUser.permissions?.includes("System admin") ||
            false) && (
            <>
              <ListItem
                {...({ name: "sidebarAdminButton" } as any)}
                disablePadding
                sx={{ display: "block" }}
                className={classes.link}
              >
                <ListItemButton
                  sx={{
                    minHeight: 48,
                    justifyContent:
                      open || temporaryOpen ? "initial" : "center",
                    px: 2.5,
                  }}
                  onClick={() => setAdminOpen(!AdminOpen)}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 0,
                      mr: open || temporaryOpen ? 2 : "auto",
                      justifyContent: "center",
                    }}
                  >
                    {!(open || temporaryOpen) && AdminOpen ? (
                      <ExpandLess />
                    ) : (
                      <AdminPanelSettingsIcon className={classes.icon} />
                    )}
                  </ListItemIcon>
                  <SidebarLinkText title="Admin" open={open || temporaryOpen} />
                  {(open || temporaryOpen) && AdminOpen ? <ExpandLess /> : null}
                  {!AdminOpen && (open || temporaryOpen) ? (
                    <ExpandMore />
                  ) : null}
                </ListItemButton>
              </ListItem>
              <Collapse in={AdminOpen} timeout="auto" unmountOnExit>
                <Divider />
                <List component="div" disablePadding>
                  {(currentUser.permissions?.includes("System admin") ||
                    false) && (
                    <Link
                      to="/db_stats"
                      onClick={() => hydrateIfDashboardClicked("/db_stats")}
                      className={classes.link}
                    >
                      <ListItem
                        {...({ name: "sidebarDB StatsButton" } as any)}
                        disablePadding
                        sx={{ display: "block" }}
                      >
                        <ListItemButton
                          sx={{
                            minHeight: 48,
                            justifyContent:
                              open || temporaryOpen ? "initial" : "center",
                            px: 2.5,
                          }}
                        >
                          <ListItemIcon
                            sx={{
                              minWidth: 0,
                              mr: open || temporaryOpen ? 2 : "auto",
                              justifyContent: "center",
                            }}
                          >
                            <AssessmentIcon className={classes.icon} />
                          </ListItemIcon>
                          <SidebarLinkText
                            route="/db_stats"
                            title="DB Stats"
                            open={open || temporaryOpen}
                          />
                        </ListItemButton>
                      </ListItem>
                    </Link>
                  )}

                  {(currentUser.permissions?.includes("Manage users") ||
                    currentUser.permissions?.includes("System admin") ||
                    false) && (
                    <Link
                      to="/user_management"
                      onClick={() =>
                        hydrateIfDashboardClicked("/user_management")
                      }
                      className={classes.link}
                    >
                      <ListItem
                        {...({ name: "sidebarUser ManagementButton" } as any)}
                        disablePadding
                        sx={{ display: "block" }}
                      >
                        <ListItemButton
                          sx={{
                            minHeight: 48,
                            justifyContent:
                              open || temporaryOpen ? "initial" : "center",
                            px: 2.5,
                          }}
                        >
                          <ListItemIcon
                            sx={{
                              minWidth: 0,
                              mr: open || temporaryOpen ? 2 : "auto",
                              justifyContent: "center",
                            }}
                          >
                            <GroupIcon className={classes.icon} />
                          </ListItemIcon>
                          <SidebarLinkText
                            route="/user_management"
                            title="User Management"
                            open={open || temporaryOpen}
                          />
                        </ListItemButton>
                      </ListItem>
                    </Link>
                  )}
                </List>
                <Divider />
              </Collapse>
            </>
          )}
        </List>
      </Drawer>
    </>
  );
};

export default SidebarAndHeader;
