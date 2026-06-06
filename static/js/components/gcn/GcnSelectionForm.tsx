import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import React, { Suspense, useEffect, useState } from "react";

import useMediaQuery from "@mui/material/useMediaQuery";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import Grid from "@mui/material/Grid";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import { useTheme } from "@mui/material/styles";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import { useAppDispatch, useAppSelector } from "../../types/hooks";

import {
  useGetGalaxyCatalogsQuery,
  useLazyGetGcnEventGalaxiesQuery,
} from "../../ducks/galaxies";
import { useLazyGetInstrumentSkymapQuery } from "../../ducks/instrument";
import {
  useLazyGetGcnEventObservationsQuery,
  useSubmitObservationsTreasureMapMutation,
} from "../../ducks/observations";
import * as sourcesActions from "../../ducks/sources";
import { useLazyGetSourcesInGcnQuery } from "../../ducks/sourcesingcn";

import AddCatalogQueryPage from "../catalog_query/AddCatalogQueryPage";
import AddSurveyEfficiencyObservationsPage from "../survey_efficiency/AddSurveyEfficiencyObservationsPage";
import ExecutedObservationsTable from "../observation/ExecutedObservationsTable";
import GalaxyTable from "../galaxy/GalaxyTable";
import LocalizationPlot from "../localization/LocalizationPlot";
import SourceTable from "../source/SourceTable";
import ProgressIndicator from "../ProgressIndicators";

import { useGetLocalizationQuery } from "../../ducks/localization";
import Spinner from "../Spinner";

const GcnReport = React.lazy(() => import("./GcnReport"));
const GcnSummary = React.lazy(() => import("./GcnSummary"));

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  formGroup: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(8rem, 1fr))",
    justifyContent: "space-evenly",
    alignItems: "center",
    width: "100%",
  },
  formGroupSmall: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "flex-end",
    alignItems: "right",
  },
  formItem: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-start",
    alignItems: "center",
    margin: 0,
  },
  formContainer: {
    maxWidth: "95vw",
    width: "100%",
    marginTop: "0.3rem",
  },
  formContainerItem: {
    maxWidth: "87vw",
    width: "100%",
  },
  localizationPlotSmall: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    maxWidth: "90vw",
    width: "100%",
  },
  buttons: {
    display: "grid",
    gridGap: "1rem",
    gridTemplateColumns: "repeat(auto-fit, minmax(5rem, 1fr))",
    "& > button": {
      maxHeight: "4rem",
      // no space between 2 lines of text
      lineHeight: "1rem",
    },
    marginBottom: "1rem",
  },
}));

interface GcnEventSourcesPageProps {
  dateobs: string;
  sources?: Record<string, any> | null;
  localizationName: string;
  sourceFilteringState: Record<string, any>;
}

const GcnEventSourcesPage = ({
  dateobs,
  sources = null,
  localizationName,
  sourceFilteringState,
}: GcnEventSourcesPageProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const sourcesState = useAppSelector(
    (state) => state["sources"].gcnEventSources,
  ) as any;
  const [sourcesRowsPerPage, setSourcesRowsPerPage] = useState(100);
  const [filtering, setFiltering] = useState<Record<string, any>>({
    ...sourceFilteringState,
    localizationName,
    pageNumber: 1,
    numPerPage: sourcesRowsPerPage,
  });
  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);
  const [fetchSourcesInGcn] = useLazyGetSourcesInGcnQuery();

  const handleSourcesTableSorting = (sortData: any, filterData: any) => {
    const data = {
      ...sourceFilteringState,
      ...filterData,
      localizationName,
      pageNumber: 1,
      numPerPage: sourcesRowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(sourcesActions.fetchGcnEventSources(dateobs, data));
    setFiltering(data);
  };

  const handleSourcesTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    setSourcesRowsPerPage(numPerPage);
    const data: Record<string, any> = {
      ...sourceFilteringState,
      ...filterData,
      localizationName,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data["sortBy"] = sortData.name;
      data["sortOrder"] = sortData.direction;
    }
    dispatch(sourcesActions.fetchGcnEventSources(dateobs, data));
    setFiltering(data);
  };

  const handleSourcesDownload = async () => {
    const sourceAll: any[] = [];
    if (sourcesState.totalMatches === 0) {
      dispatch(showNotification("No sources to download", "warning"));
    } else {
      setDownloadProgressTotal(sourcesState.totalMatches);
      for (
        let i = 1;
        i <= Math.ceil(sourcesState.totalMatches / sourcesState.numPerPage);
        i += 1
      ) {
        const data = {
          ...filtering,
          pageNumber: i,
          numPerPage: sourcesState.numPerPage,
        };
        /* eslint-disable no-await-in-loop */
        const result = (await dispatch(
          sourcesActions.fetchSources(data),
        )) as any;
        if (result && result.data && result?.status === "success") {
          sourceAll.push(...result.data.sources);
          setDownloadProgressCurrent(sourceAll.length);
          setDownloadProgressTotal(sourcesState.totalMatches);
        } else if (result && result?.status !== "success") {
          // break the loop and set progress to 0 and show error message
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (sourceAll?.length === 0) {
            dispatch(
              showNotification(
                "Failed to fetch some sources. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some sources, please try again. Sources fetched so far will be downloaded.",
                "error",
              ),
            );
          }
          break;
        }
      }
    }
    setDownloadProgressCurrent(0);
    setDownloadProgressTotal(0);
    if (sourceAll?.length === sourcesState.totalMatches?.length) {
      dispatch(showNotification("Sources downloaded successfully"));
    }

    // for all the sources, fetch the "sourcesConfirmedInGcn" status
    try {
      const sourcesInGcn = await fetchSourcesInGcn({
        dateobs,
        localizationName,
        sourcesIdList: sourceAll.map((source) => source.id),
      }).unwrap();
      sourceAll.forEach((source) => {
        const match = sourcesInGcn.find(
          (item: any) => item.obj_id === source.id,
        );
        if (match) {
          source.gcn = {
            status: match.confirmed ? "Highlighted" : "Rejected",
            explanation: match.explanation,
            notes: match.notes,
          };
        } else {
          source.gcn = {
            status: "Undefined",
            explanation: "",
            notes: "",
          };
        }
      });
    } catch {
      // notification handled by baseQuery
    }
    return sourceAll;
  };

  return (
    <div className={(classes as any).sourceList}>
      {sources?.["sources"]?.length === 0 && (
        <Typography variant="h5" align="center">
          No sources found within localization with these filters.
        </Typography>
      )}
      <SourceTable
        title=""
        sources={sources?.["sources"]}
        paginateCallback={handleSourcesTablePagination}
        pageNumber={sources?.["pageNumber"]}
        totalMatches={sources?.["totalMatches"]}
        numPerPage={sources?.["numPerPage"]}
        sortingCallback={handleSourcesTableSorting}
        downloadCallback={handleSourcesDownload}
        includeGcnStatus
        sourceInGcnFilter={sourceFilteringState}
      />
      <Dialog open={downloadProgressTotal > 0} maxWidth="md">
        <DialogContent
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <Typography variant="h6" display="inline">
            Downloading {downloadProgressTotal} sources
          </Typography>
          <div
            style={{
              height: "5rem",
              width: "5rem",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <ProgressIndicator
              current={downloadProgressCurrent}
              total={downloadProgressTotal}
              percentage={false}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

interface MyObjectFieldTemplateProps {
  uiSchema: Record<string, any>;
  properties: any[];
}

const MyObjectFieldTemplate = (props: MyObjectFieldTemplateProps) => {
  const { properties, uiSchema } = props;

  return (
    <Grid
      container
      direction="column"
      alignItems="center"
      spacing={2}
      {...({ justify: "space-between" } as any)}
    >
      {uiSchema["ui:grid"].map((row: any) => (
        <Grid
          container
          direction="row"
          alignItems="center"
          spacing={2}
          key={JSON.stringify(row)}
          {...({ justify: "space-between" } as any)}
        >
          {Object.keys(row).map((fieldName) => (
            <Grid size={row[fieldName]} key={fieldName}>
              {properties.find((p) => p.name === fieldName).content}
            </Grid>
          ))}
        </Grid>
      ))}
    </Grid>
  );
};

interface GcnSelectionFormProps {
  dateobs: string;
}

const GcnSelectionForm = ({ dateobs }: GcnSelectionFormProps) => {
  const theme = useTheme();
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [fetchInstrumentSkymap] = useLazyGetInstrumentSkymapQuery();
  const [selectedLocalizationName, setSelectedLocalizationName] = useState<
    string | null
  >(null);

  const projectionOptions = ["orthographic", "mollweide"];

  const displayOptions = [
    "localization",
    "sources",
    "galaxies",
    "instrument",
    "observations",
  ];
  const displayOptionsDefault = Object.fromEntries(
    displayOptions.map((x) => [x, x === "localization"]),
  );

  const gcnEvent = useAppSelector((state) => state["gcnEvent"]) as any;
  const groups = (useGetGroupsQuery().data?.userAccessible ?? []) as any[];
  const galaxyCatalogs = (useGetGalaxyCatalogsQuery().data ?? []) as any[];
  const [selectedFields, setSelectedFields] = useState<any[]>([]);

  const [selectedInstrumentId, setSelectedInstrumentId] = useState<any>(null);
  const [selectedLocalizationId, setSelectedLocalizationId] =
    useState<any>(null);

  const selectedLocalizationLoadName = gcnEvent?.localizations?.find(
    (loc: any) => loc.id === selectedLocalizationId,
  )?.localization_name;
  const { data: analysisLoc, isFetching: fetchingLocalization } =
    useGetLocalizationQuery(
      {
        dateobs: gcnEvent?.dateobs,
        localization_name: selectedLocalizationLoadName,
      },
      {
        skip: !gcnEvent?.dateobs || !selectedLocalizationLoadName,
      },
    );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmittingTreasureMap, setIsSubmittingTreasureMap] =
    useState<any>(null);
  const [checkedDisplayState, setCheckedDisplayState] = useState<
    Record<string, any>
  >(displayOptionsDefault);
  const [skymapInstrument, setSkymapInstrument] = useState<any>(null);

  const [tabIndex, setTabIndex] = useState(1);
  const [selectedProjection, setSelectedProjection] = useState(
    projectionOptions[0],
  );

  const [sourceFilteringState, setSourceFilteringState] = useState<
    Record<string, any>
  >({
    startDate: null,
    endDate: null,
    localizationName: null,
    group_ids: [],
    localizationCumprob: null,
    requireDetections: true,
  });

  const [hasFetchedObservations, setHasFetchedObservations] = useState(false);

  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const handleChangeTab = (_event: any, newValue: number) => {
    setTabIndex(newValue);
  };

  const defaultStartDate = dayjs
    .utc(gcnEvent?.dateobs)
    .format("YYYY-MM-DD HH:mm:ss");
  const defaultEndDate = dayjs
    .utc(gcnEvent?.dateobs)
    .add(7, "day")
    .format("YYYY-MM-DD HH:mm:ss");
  const [formDataState, setFormDataState] = useState<Record<string, any>>({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
  });

  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { instrumentList } = useAppSelector(
    (state) => state["instruments"],
  ) as any;
  const sortedInstrumentList = [...instrumentList];
  sortedInstrumentList.sort((i1: any, i2: any) =>
    i1.name.localeCompare(i2.name),
  );

  const gcnEventSources = useAppSelector(
    (state) => state?.["sources"]?.gcnEventSources,
  ) as any;
  const [fetchGcnEventGalaxies, { data: gcnEventGalaxies }] =
    useLazyGetGcnEventGalaxiesQuery();
  const [gcnEventObservations, setGcnEventObservations] = useState<any>(null);
  const [fetchGcnEventObservations] = useLazyGetGcnEventObservationsQuery();
  const [submitObservationsTreasureMap] =
    useSubmitObservationsTreasureMapMutation();

  useEffect(() => {
    const setDefaults = async () => {
      // reorder the instrument list by instrument id, and also make sure that the instrument called ZTF is first
      const orderedInstrumentList = [...instrumentList];
      orderedInstrumentList.sort((i1: any, i2: any) => {
        if (i1.name === "ZTF") {
          return -1;
        }
        if (i2.name === "ZTF") {
          return 1;
        }
        if (i1.id > i2.id) {
          return 1;
        }
        if (i2.id > i1.id) {
          return -1;
        }
        return 0;
      });
      setSelectedInstrumentId(orderedInstrumentList[0]?.id);
      setSelectedLocalizationId(gcnEvent.localizations[0]?.id);
      setSelectedLocalizationName(gcnEvent.localizations[0]?.localization_name);
    };
    if (
      dateobs === gcnEvent?.dateobs &&
      dateobs &&
      instrumentList.length > 0 &&
      gcnEvent?.localizations?.length > 0 &&
      (gcnEvent?.localizations?.find(
        (loc: any) => loc.id === selectedLocalizationId,
      ) ||
        selectedLocalizationId === null) &&
      fetchingLocalization === false
    ) {
      setDefaults();
    }

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instrumentList]);

  const isBig = useMediaQuery(theme.breakpoints.up("md"));

  useEffect(() => {
    if (isBig && tabIndex === 0) {
      setTabIndex(1);
    }
  });

  const handleOnChange = (position: number) => {
    const checkedDisplayStateCopy = JSON.parse(
      JSON.stringify(checkedDisplayState),
    );
    const optionKey = displayOptions[position];
    if (optionKey !== undefined) {
      checkedDisplayStateCopy[optionKey] = !checkedDisplayStateCopy[optionKey];
    }
    setCheckedDisplayState(checkedDisplayStateCopy);
  };

  const handleSubmitTreasureMap = async (id: any, filterParams: any) => {
    if (!hasFetchedObservations) {
      dispatch(
        showNotification(
          "Please fetch observations before submitting to treasure map",
          "error",
        ),
      );
      return;
    }
    setIsSubmittingTreasureMap(id);
    const data = {
      startDate: filterParams.startDate,
      endDate: filterParams.endDate,
      localizationCumprob: filterParams.localizationCumprob,
      localizationName: filterParams.localizationName,
      localizationDateobs: dateobs,
      numberObservations: filterParams?.numberDetections || 1,
      requireDetections: filterParams?.requireDetections,
    };
    try {
      await submitObservationsTreasureMap({ id, data }).unwrap();
    } catch {
      // error notification handled by the baseQuery
    }
    setIsSubmittingTreasureMap(null);
  };

  const handleExecutedDownload = async () => {
    const observationsAll: any[] = [];
    if (gcnEventObservations.totalMatches === 0) {
      dispatch(showNotification("No observations to download", "warning"));
    } else {
      setDownloadProgressTotal(gcnEventObservations.totalMatches);
      for (
        let i = 1;
        i <= Math.ceil(gcnEventObservations.totalMatches / 100);
        i += 1
      ) {
        try {
          const result: any = await fetchGcnEventObservations({
            dateobs: gcnEvent?.dateobs,
            filterParams: {
              ...formDataState,
              instrumentName: instLookUp[selectedInstrumentId]?.name,
              telescopeName:
                telLookUp[instLookUp[selectedInstrumentId]?.telescope_id]?.name,
              numberObservations: formDataState?.["numberDetections"] || 1,
              numPerPage: 100,
              pageNumber: i,
              includeGeoJSON: true,
            },
          }).unwrap();
          observationsAll.push(...result.observations);
          setDownloadProgressCurrent(observationsAll.length);
          setDownloadProgressTotal(gcnEventObservations.totalMatches);
        } catch {
          // break the loop and set progress to 0 and show error message
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (gcnEventObservations.observations?.length === 0) {
            dispatch(
              showNotification(
                "Failed to fetch some observations. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some observations, please try again. Observations fetched so far will be downloaded.",
                "error",
              ),
            );
          }
          break;
        }
      }
    }
    setDownloadProgressCurrent(0);
    setDownloadProgressTotal(0);
    if (observationsAll?.length === gcnEventObservations.totalMatches?.length) {
      dispatch(showNotification("Observations downloaded successfully"));
    }
    return observationsAll;
  };

  const displayOptionsAvailable: Record<string, boolean> = {
    localization: !!gcnEvent?.localizations?.length,
    sources: !!gcnEventSources,
    galaxies: !!gcnEventGalaxies,
    instruments: !!sortedInstrumentList,
    observations: !!gcnEventObservations,
  };

  const instLookUp: Record<string, any> = {};
  sortedInstrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const telLookUp: Record<string, any> = {};
  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const locLookUp: Record<string, any> = {};
  gcnEvent?.localizations?.forEach((loc: any) => {
    locLookUp[loc.id] = loc;
  });

  const [selectedFormData, setSelectedFormData] = useState<Record<string, any>>(
    {},
  );

  useEffect(() => {
    const fetchSkymapInstrument = async () => {
      fetchInstrumentSkymap({
        id: instLookUp[selectedInstrumentId]?.id,
        localization: locLookUp[selectedLocalizationId],
      })
        .unwrap()
        .then((response: any) => setSkymapInstrument(response))
        .catch(() => {});
    };
    if (
      instLookUp[selectedInstrumentId] &&
      Object.keys(locLookUp).includes(selectedLocalizationId?.toString())
    ) {
      fetchSkymapInstrument();
    }
  }, [
    dispatch,
    setSkymapInstrument,
    selectedLocalizationId,
    selectedInstrumentId,
  ]);

  if (gcnEvent?.dateobs !== dateobs) return <Spinner />;

  const handleSelectedInstrumentChange = (e: any) => {
    setSelectedInstrumentId(e.target.value);
  };

  const handleSelectedLocalizationChange = (e: any) => {
    setSelectedLocalizationId(e.target.value);
    setSelectedLocalizationName(locLookUp[e.target.value].localization_name);
  };

  const showError = (message: string) => {
    dispatch(showNotification(message, "error", 4000));
  };

  const handleSubmit = async ({ formData }: { formData: any }) => {
    const { queryList = [] } = formData;

    if (queryList.includes("sources") && !formData?.group_ids?.length) {
      showError("Please select at least one group when querying sources.");
      return;
    }
    setIsSubmitting(true);

    const cleanDate = (date: string) =>
      date?.replace("+00:00", "").replace(".000Z", "");
    formData.startDate = cleanDate(formData.startDate);
    formData.endDate = cleanDate(formData.endDate);
    formData.numPerPage = 100;
    formData.pageNumber = 1;

    if (selectedLocalizationId && locLookUp[selectedLocalizationId]) {
      formData.localizationName =
        locLookUp[selectedLocalizationId].localization_name;
    }

    const fetchSources = async () => {
      await dispatch(
        sourcesActions.fetchGcnEventSources(gcnEvent?.dateobs, formData),
      );
      setSourceFilteringState(formData);
    };

    const fetchObservations = async () => {
      const instrument = instLookUp[selectedInstrumentId];
      const telescope = instrument ? telLookUp[instrument.telescope_id] : null;

      if (!instrument || !telescope) {
        showError(
          "Please select an instrument and telescope before fetching observations",
        );
        setIsSubmitting(false);
        return false;
      }

      try {
        const result = await fetchGcnEventObservations({
          dateobs: gcnEvent?.dateobs,
          filterParams: {
            ...formData,
            instrumentName: instrument.name,
            telescopeName: telescope.name,
            numberObservations: formData?.numberDetections || 1,
          },
        }).unwrap();
        setGcnEventObservations(result);
      } catch {
        // error notification handled by the baseQuery
      }
      setHasFetchedObservations(true);
      return true;
    };

    const fetchGalaxies = async () => {
      formData.numPerPage = 100;
      await fetchGcnEventGalaxies({
        dateobs: gcnEvent?.dateobs,
        filterParams: formData,
      });
    };

    formData.includeGeoJSON = true;

    if (queryList.includes("sources")) await fetchSources();
    if (queryList.includes("observations")) {
      const isObservationsFetched = await fetchObservations();
      if (!isObservationsFetched) return;
    }
    if (queryList.includes("galaxies")) await fetchGalaxies();

    setFormDataState(formData);
    setIsSubmitting(false);
  };

  function validate(formData: any, errors: any) {
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError("Start Date must come before End Date");
    }
    if (
      formData.localizationCumprob < 0 ||
      formData.localizationCumprob > 1.01
    ) {
      errors.cumulative.addError(
        "Value of cumulative should be between 0 and 1",
      );
    }
    return errors;
  }

  const GcnSourceSelectionFormSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        title: "Start Date",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        title: "End Date",
        default: defaultEndDate,
      },
      numberDetections: {
        type: "number",
        title: "Min Number of Detections/Observations",
        default: 2,
        minimum: 1,
      },
      localizationCumprob: {
        type: "number",
        title: "Cumulative Probability",
        default: 0.95,
        minimum: 0,
        maximum: 1,
      },
      maxDistance: {
        type: "number",
        title: "Maximum Distance [Mpc]",
        minimum: 0,
      },
      localizationRejectSources: {
        type: "boolean",
        title: "Do not display rejected sources",
      },
      excludeForcedPhotometry: {
        type: "boolean",
        title: "Exclude forced photometry",
        default: false,
      },
      requireDetections: {
        type: "boolean",
        title: "Require detections",
        default: true,
      },
      queryList: {
        type: "array",
        items: {
          type: "string",
          enum: ["sources", "galaxies", "observations"],
        },
        uniqueItems: true,
        default: ["sources"],
        title: "Query list",
      },
      group_ids: {
        title: "Groups",
        type: "array",
        items: {
          type: "integer",
          enum: groups.map((group) => group.id),
        },
        uniqueItems: true,
      },
      ...(galaxyCatalogs?.length > 0 && {
        catalog_name: {
          type: "string",
          title: "Galaxy Catalog",
          enum: galaxyCatalogs.map((catalog) => catalog?.catalog_name),
          default: galaxyCatalogs[0]?.catalog_name,
        },
      }),
    },
    required: [
      "startDate",
      "endDate",
      "localizationCumprob",
      "queryList",
      ...(galaxyCatalogs?.length > 0 ? ["catalog_name"] : []),
      "requireDetections",
    ],
  };

  const uiSchema = {
    group_ids: {
      "ui:enumNames": groups.map((group) => group.name),
    },
    "ui:grid": [
      { startDate: 6, endDate: 6 },
      { numberDetections: 4, localizationCumprob: 4, maxDistance: 4 },
      {
        requireDetections: 4,
        excludeForcedPhotometry: 4,
        localizationRejectSources: 4,
      },
      galaxyCatalogs?.length > 0
        ? { queryList: 4, catalog_name: 4, group_ids: 4 }
        : { queryList: 6, group_ids: 6 },
    ],
  };

  return (
    <Grid container spacing={4}>
      <Grid
        size={{ sm: 4 }}
        sx={{ display: { xs: "none", sm: "none", md: "block" } }}
      >
        {Object.keys(locLookUp).includes(analysisLoc?.id?.toString() ?? "") &&
        !fetchingLocalization ? (
          <div style={{ marginTop: "0.5rem" }}>
            <LocalizationPlot
              localization={analysisLoc}
              sources={gcnEventSources}
              galaxies={gcnEventGalaxies}
              instrument={skymapInstrument}
              observations={gcnEventObservations}
              options={checkedDisplayState}
              selectedFields={selectedFields}
              setSelectedFields={setSelectedFields}
              projection={selectedProjection}
            />
            <InputLabel
              style={{ marginTop: "0.5rem", marginBottom: "0.25rem" }}
              id="projection"
            >
              Projection
            </InputLabel>
            <Select
              labelId="projection"
              id="projection"
              value={selectedProjection}
              onChange={(e) => setSelectedProjection(e.target.value)}
              style={{ width: "100%" }}
            >
              {projectionOptions.map((option) => (
                <MenuItem value={option} key={option}>
                  {option}
                </MenuItem>
              ))}
            </Select>
            <InputLabel
              style={{ marginTop: "0.5rem", marginBottom: "0.25rem" }}
              id="showOnPlot"
            >
              Show/Hide on Plot
            </InputLabel>
            <FormGroup className={classes.formGroup}>
              {displayOptions.map((option, index) => (
                <FormControlLabel
                  control={
                    <Checkbox
                      onChange={() => handleOnChange(index)}
                      checked={
                        !!checkedDisplayState[displayOptions[index] ?? ""]
                      }
                    />
                  }
                  label={option}
                  key={option}
                  disabled={!displayOptionsAvailable[option]}
                  className={classes.formItem}
                />
              ))}
            </FormGroup>
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: "100%",
            }}
          >
            <CircularProgress />
          </div>
        )}
      </Grid>
      <Grid size={{ sm: 12, md: 8 }}>
        <Tabs
          value={tabIndex}
          onChange={handleChangeTab}
          aria-label="gcn_tabs"
          variant="scrollable"
          {...({ xs: 12 } as any)}
          sx={{
            display: {
              maxWidth: "95vw",
              width: "100&",
              "& > button": { lineHeight: "1.5rem" },
            },
          }}
        >
          {/* the first tab called skymap has to be hidden until we reach the sm breakpoint */}
          <Tab label="Skymap" sx={{ display: { sm: "block", md: "none" } }} />
          <Tab label="Query Form" />
          <Tab label="Sources" />
          <Tab label="Galaxies" />
          <Tab label="Observations" />
        </Tabs>

        {tabIndex === 0 && (
          <Box sx={{ display: { sm: "block", md: "none" } }}>
            {Object.keys(locLookUp).includes(
              analysisLoc?.id?.toString() ?? "",
            ) && !fetchingLocalization ? (
              <Grid container spacing={2}>
                <Grid
                  size={{ sm: 8, md: 12 }}
                  className={classes.localizationPlotSmall}
                >
                  <LocalizationPlot
                    localization={analysisLoc}
                    sources={gcnEventSources}
                    galaxies={gcnEventGalaxies}
                    instrument={skymapInstrument}
                    observations={gcnEventObservations}
                    options={checkedDisplayState}
                    selectedFields={selectedFields}
                    setSelectedFields={setSelectedFields}
                    projection={selectedProjection}
                  />
                </Grid>
                <Grid size={{ xs: 9, sm: 4, md: 12 }}>
                  <InputLabel
                    style={{ marginTop: "0.5rem", marginBottom: "0.25rem" }}
                    id="projection"
                  >
                    Projection
                  </InputLabel>
                  <Select
                    labelId="projection"
                    id="projection"
                    value={selectedProjection}
                    onChange={(e) => setSelectedProjection(e.target.value)}
                    style={{ width: "100%" }}
                  >
                    {projectionOptions.map((option) => (
                      <MenuItem value={option} key={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </Select>
                  <InputLabel
                    style={{ marginTop: "0.5rem", marginBottom: "0.25rem" }}
                    id="showOnPlot"
                  >
                    Show/Hide on Plot
                  </InputLabel>
                  <FormGroup className={classes.formGroupSmall}>
                    {displayOptions.map((option, index) => (
                      <FormControlLabel
                        control={
                          <Checkbox
                            onChange={() => handleOnChange(index)}
                            checked={
                              !!checkedDisplayState[displayOptions[index] ?? ""]
                            }
                          />
                        }
                        label={option}
                        key={option}
                        disabled={!displayOptionsAvailable[option]}
                        className={classes.formItem}
                      />
                    ))}
                  </FormGroup>
                </Grid>
              </Grid>
            ) : (
              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  height: "100%",
                }}
              >
                <CircularProgress />
              </div>
            )}
          </Box>
        )}

        {tabIndex === 1 && (
          <Grid
            container
            spacing={1}
            className={classes.formContainer}
            alignItems="center"
          >
            <Grid size={{ sm: 12 }} className={classes.formContainerItem}>
              <InputLabel id="localizationSelectLabel">Localization</InputLabel>
              <Select
                fullWidth
                inputProps={{ MenuProps: { disableScrollLock: true } }}
                labelId="localizationSelectLabel"
                value={selectedLocalizationId || ""}
                onChange={handleSelectedLocalizationChange}
              >
                {gcnEvent?.localizations?.map((localization: any) => (
                  <MenuItem value={localization.id} key={localization.id}>
                    {`Skymap: ${localization.localization_name} / Created: ${localization.created_at}`}
                  </MenuItem>
                ))}
              </Select>
            </Grid>
            <Grid size={{ sm: 12 }} className={classes.formContainerItem}>
              <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
              <Select
                fullWidth
                inputProps={{ MenuProps: { disableScrollLock: true } }}
                labelId="instrumentSelectLabel"
                value={selectedInstrumentId || ""}
                onChange={handleSelectedInstrumentChange}
              >
                {sortedInstrumentList?.map((instrument: any) => (
                  <MenuItem
                    value={instrument.id}
                    key={instrument.id}
                    className={(classes as any).instrumentSelectItem}
                  >
                    {`${telLookUp[instrument.telescope_id]?.name} / ${
                      instrument.name
                    }`}
                  </MenuItem>
                ))}
              </Select>
            </Grid>
            <Grid
              size={{ xs: 11, sm: 12 }}
              data-testid="gcnsource-selection-form"
              sx={{ mt: "0.8rem" }}
            >
              <Form
                schema={GcnSourceSelectionFormSchema as any}
                formData={selectedFormData}
                onChange={((e: any) => setSelectedFormData(e.formData)) as any}
                uiSchema={uiSchema}
                templates={{
                  ObjectFieldTemplate: MyObjectFieldTemplate as any,
                }}
                validator={validator}
                onSubmit={handleSubmit as any}
                customValidate={validate}
                disabled={isSubmitting}
                liveValidate
              >
                <Button
                  primary
                  type="submit"
                  sx={{ my: "1rem" }}
                  async
                  loading={isSubmitting}
                >
                  Submit
                </Button>
              </Form>
            </Grid>
            {gcnEvent && selectedLocalizationId ? (
              <Grid size={{ xs: 11, sm: 12 }}>
                <div className={classes.buttons}>
                  <Suspense fallback={<CircularProgress />}>
                    <GcnSummary dateobs={dateobs} />
                  </Suspense>
                  <Suspense fallback={<CircularProgress />}>
                    <GcnReport dateobs={dateobs} />
                  </Suspense>
                  <AddSurveyEfficiencyObservationsPage />
                  <AddCatalogQueryPage />
                  {isSubmittingTreasureMap === selectedInstrumentId ? (
                    <CircularProgress />
                  ) : (
                    <Button
                      secondary
                      onClick={() => {
                        handleSubmitTreasureMap(
                          selectedInstrumentId,
                          formDataState,
                        );
                      }}
                      type="submit"
                      size="small"
                      data-testid={`treasuremapRequest_${selectedInstrumentId}`}
                    >
                      Send to Treasure Map
                    </Button>
                  )}
                </div>
              </Grid>
            ) : (
              <CircularProgress />
            )}
          </Grid>
        )}

        {tabIndex === 2 && (
          <div>
            {gcnEventSources?.sources ? (
              <div>
                {selectedLocalizationName && (
                  <GcnEventSourcesPage
                    dateobs={dateobs}
                    sources={gcnEventSources}
                    localizationName={selectedLocalizationName}
                    sourceFilteringState={sourceFilteringState}
                  />
                )}
              </div>
            ) : (
              <Typography variant="h5">
                Need to fetch sources from the query form
              </Typography>
            )}
          </div>
        )}

        {tabIndex === 3 && (
          <div>
            {gcnEventGalaxies?.galaxies ? (
              <div>
                {gcnEventGalaxies?.galaxies.length === 0 ? (
                  <Typography variant="h5">None</Typography>
                ) : (
                  <div>
                    <GalaxyTable
                      galaxies={gcnEventGalaxies.galaxies}
                      totalMatches={gcnEventGalaxies.totalMatches}
                      serverSide={false}
                      {...({ showTitle: true } as any)}
                    />
                  </div>
                )}
              </div>
            ) : (
              <Typography variant="h5">Fetching galaxies...</Typography>
            )}
          </div>
        )}

        {tabIndex === 4 && (
          <div>
            {gcnEventObservations?.observations ? (
              <div>
                {gcnEventObservations?.observations.length === 0 ? (
                  <Typography variant="h5">None</Typography>
                ) : (
                  <div>
                    <ExecutedObservationsTable
                      observations={gcnEventObservations.observations}
                      totalMatches={gcnEventObservations.totalMatches}
                      numPerPage={
                        formDataState["numPerPage"] ||
                        gcnEventObservations.numPerPage ||
                        100
                      }
                      downloadCallback={handleExecutedDownload}
                      serverSide={false}
                    />
                    <Dialog open={downloadProgressTotal > 0} maxWidth="md">
                      <DialogContent
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "center",
                          alignItems: "center",
                        }}
                      >
                        <Typography variant="h6" display="inline">
                          Downloading {downloadProgressTotal} observations
                        </Typography>
                        <div
                          style={{
                            height: "5rem",
                            width: "5rem",
                            display: "flex",
                            flexDirection: "column",
                            justifyContent: "center",
                            alignItems: "center",
                          }}
                        >
                          <ProgressIndicator
                            current={downloadProgressCurrent}
                            total={downloadProgressTotal}
                            percentage={false}
                          />
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                )}
              </div>
            ) : (
              <Typography variant="h5">Fetching observations...</Typography>
            )}
          </div>
        )}
      </Grid>
    </Grid>
  );
};

export default GcnSelectionForm;

export { MyObjectFieldTemplate };
