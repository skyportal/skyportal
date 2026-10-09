import { lazy, Suspense, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import Grid from "@mui/material/Grid";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { skipToken } from "@reduxjs/toolkit/query";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import Spinner from "../Spinner";
import { DownloadProgressDialog } from "../ProgressIndicators";
import AddCatalogQueryPage from "../catalog_query/AddCatalogQueryPage";
import ExecutedObservationsTable from "../observation/ExecutedObservationsTable";
import SourceTable from "../source/SourceTable";
import AddSurveyEfficiencyObservationsPage from "../survey_efficiency/AddSurveyEfficiencyObservationsPage";
import GcnEventAssociations from "./GcnEventAssociations";
import GcnGalaxiesTab from "./GcnGalaxiesTab";
import GcnSourcesQueryForm from "./GcnSourcesQueryForm";

import { useAppDispatch } from "../../types/hooks";
import {
  useGetGalaxyCatalogsQuery,
  useGetGcnEventGalaxiesQuery,
} from "../../ducks/galaxies";
import { useGetGcnEventQuery } from "../../ducks/gcnEvent";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useLazyGetInstrumentSkymapQuery } from "../../ducks/instrument";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useGetLocalizationQuery } from "../../ducks/localization";
import {
  useLazyGetGcnEventObservationsQuery,
  useSubmitObservationsTreasureMapMutation,
} from "../../ducks/observations";
import {
  useFetchGcnEventSourcesQuery,
  useLazyFetchGcnEventSourcesQuery,
} from "../../ducks/sources";
import { useLazyGetSourcesInGcnQuery } from "../../ducks/sourcesingcn";
import { useGetTelescopesQuery } from "../../ducks/telescopes";

const LocalizationPlot = lazy(() => import("../localization/LocalizationPlot"));
const GcnReport = lazy(() => import("./GcnReport"));
const GcnSummary = lazy(() => import("./GcnSummary"));

dayjs.extend(utc);

const PROJECTIONS = ["orthographic", "mollweide"];

const PLOT_LAYERS = {
  localization: "localization",
  sources: "sources",
  galaxies: "galaxies",
  instrument: "instrument",
  observations: "observations",
  sun_moon: "sun/moon",
  galactic_plane: "galactic plane",
};

type PlotLayers = Partial<Record<keyof typeof PLOT_LAYERS, boolean>>;

const GCN_STATUS_LABELS: Record<string, string> = {
  confirmed: "Highlighted",
  rejected: "Rejected",
  ambiguous: "Ambiguous",
};

const cleanDate = (date: string) =>
  date?.replace("+00:00", "").replace(".000Z", "");

const validate = (formData: any, errors: any) => {
  if (
    formData.startDate &&
    formData.endDate &&
    formData.startDate > formData.endDate
  ) {
    errors.startDate.addError("Start Date must come before End Date");
  }
  if (formData.localizationCumprob < 0 || formData.localizationCumprob > 1.01) {
    errors.localizationCumprob.addError(
      "Cumulative probability should be between 0 and 1",
    );
  }
  return errors;
};

const useDownloadAll = (label: string) => {
  const dispatch = useAppDispatch();
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const Label = label.charAt(0).toUpperCase() + label.slice(1);

  const download = async (
    total: number,
    numPerPage: number,
    fetchPage: (pageNumber: number) => Promise<any[]>,
  ) => {
    const all: any[] = [];
    if (!total) {
      dispatch(showNotification(`No ${label} to download`, "warning"));
      return all;
    }
    setProgress({ current: 0, total });
    for (let page = 1; page <= Math.ceil(total / numPerPage); page += 1) {
      try {
        // eslint-disable-next-line no-await-in-loop
        all.push(...(await fetchPage(page)));
        setProgress({ current: all.length, total });
      } catch {
        dispatch(
          showNotification(
            all.length
              ? `Failed to fetch some ${label}, please try again. ${Label} fetched so far will be downloaded.`
              : `Failed to fetch some ${label}. Download cancelled.`,
            "error",
          ),
        );
        break;
      }
    }
    setProgress({ current: 0, total: 0 });
    if (all.length === total) {
      dispatch(showNotification(`${Label} downloaded successfully`));
    }
    return all;
  };

  return { download, progress };
};

interface GcnEventSourcesPageProps {
  dateobs: string;
  sources: any;
  localizationName: string;
  sourceFilteringState: Record<string, any>;
  setGcnSourcesArgs: (args: { dateobs: any; filterParams?: any }) => void;
}

const GcnEventSourcesPage = ({
  dateobs,
  sources,
  localizationName,
  sourceFilteringState,
  setGcnSourcesArgs,
}: GcnEventSourcesPageProps) => {
  const [numPerPage, setNumPerPage] = useState(100);
  const [filtering, setFiltering] = useState<Record<string, any>>({
    ...sourceFilteringState,
    localizationName,
    pageNumber: 1,
    numPerPage,
  });
  const [fetchSourcesInGcn] = useLazyGetSourcesInGcnQuery();
  const [fetchGcnEventSources] = useLazyFetchGcnEventSourcesQuery();
  const { download, progress } = useDownloadAll("sources");

  const query = (params: Record<string, any>) => {
    const filterParams = {
      ...sourceFilteringState,
      ...params,
      localizationName,
    };
    setGcnSourcesArgs({ dateobs, filterParams });
    setFiltering(filterParams);
  };

  const handleDownload = async () => {
    const all = await download(
      sources.totalMatches,
      sources.numPerPage,
      async (pageNumber) => {
        const result: any = await fetchGcnEventSources({
          dateobs,
          filterParams: {
            ...filtering,
            pageNumber,
            numPerPage: sources.numPerPage,
          },
        }).unwrap();
        // RTK Query results are frozen; copy them before attaching `gcn` below.
        return result.sources.map((source: any) => ({ ...source }));
      },
    );
    if (!all.length) return all;
    const { data: sourcesInGcn } = await fetchSourcesInGcn({
      dateobs,
      sourcesIDList: all.map((source) => source.id),
    });
    if (!sourcesInGcn) return all;
    all.forEach((source) => {
      const match = sourcesInGcn.find((item: any) => item.obj_id === source.id);
      source.gcn = match
        ? {
            status: GCN_STATUS_LABELS[match.status ?? ""] ?? "Pending",
            explanation: match.explanation,
            notes: match.notes,
          }
        : { status: "Undefined", explanation: "", notes: "" };
    });
    return all;
  };

  return (
    <>
      {sources.sources.length === 0 ? (
        <Typography
          variant="body1"
          color="textSecondary"
          align="center"
          sx={{ py: 3 }}
        >
          No sources found within localization with these filters.
        </Typography>
      ) : (
        <SourceTable
          title=""
          sources={sources.sources}
          paginateCallback={(
            pageNumber: number,
            perPage: number,
            sortData: any,
            filterData: any,
          ) => {
            setNumPerPage(perPage);
            query({
              ...filterData,
              pageNumber,
              numPerPage: perPage,
              ...(sortData?.name && {
                sortBy: sortData.name,
                sortOrder: sortData.direction,
              }),
            });
          }}
          pageNumber={sources.pageNumber}
          totalMatches={sources.totalMatches}
          numPerPage={sources.numPerPage}
          sortingCallback={(sortData: any, filterData: any) =>
            query({
              ...filterData,
              pageNumber: 1,
              numPerPage,
              sortBy: sortData.name,
              sortOrder: sortData.direction,
            })
          }
          downloadCallback={handleDownload}
          includeGcnStatus
          sourceInGcnFilter={sourceFilteringState}
          gcnEventDateobs={dateobs}
        />
      )}
      <DownloadProgressDialog {...progress} label="sources" />
    </>
  );
};

interface MyObjectFieldTemplateProps {
  uiSchema: Record<string, any>;
  properties: any[];
}

const MyObjectFieldTemplate = ({
  properties,
  uiSchema,
}: MyObjectFieldTemplateProps) => (
  <Grid container spacing={2.5} sx={{ flexDirection: "column", width: "100%" }}>
    {uiSchema["ui:grid"].map((row: any) =>
      row.__section ? (
        <Grid key={`section-${row.__section}`} sx={{ width: "100%" }}>
          <Typography
            variant="subtitle2"
            sx={{
              fontWeight: 600,
              color: "text.secondary",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              pb: 0.5,
              borderBottom: 1,
              borderColor: "divider",
            }}
          >
            {row.__section}
          </Typography>
        </Grid>
      ) : (
        <Grid
          container
          spacing={2}
          key={JSON.stringify(row)}
          sx={{ alignItems: "flex-start", width: "100%" }}
        >
          {Object.keys(row).map((fieldName) => (
            <Grid size={row[fieldName]} key={fieldName}>
              {properties.find((p) => p.name === fieldName)?.content}
            </Grid>
          ))}
        </Grid>
      ),
    )}
  </Grid>
);

interface SkymapControlsProps {
  projection: string;
  setProjection: (projection: string) => void;
  layers: PlotLayers;
  setLayers: (layers: PlotLayers) => void;
  available: PlotLayers;
  column?: boolean;
}

const SkymapControls = ({
  projection,
  setProjection,
  layers,
  setLayers,
  available,
  column = false,
}: SkymapControlsProps) => (
  <>
    <InputLabel id="projection" sx={{ mt: 1, mb: 0.5 }}>
      Projection
    </InputLabel>
    <Select
      labelId="projection"
      id="projection"
      value={projection}
      onChange={(e) => setProjection(e.target.value)}
      fullWidth
    >
      {PROJECTIONS.map((option) => (
        <MenuItem value={option} key={option}>
          {option}
        </MenuItem>
      ))}
    </Select>
    <InputLabel id="showOnPlot" sx={{ mt: 1, mb: 0.5 }}>
      Show/Hide on Plot
    </InputLabel>
    <FormGroup
      sx={
        column
          ? {}
          : {
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(8rem, 1fr))",
              alignItems: "center",
            }
      }
    >
      {(
        Object.entries(PLOT_LAYERS) as [keyof typeof PLOT_LAYERS, string][]
      ).map(([layer, label]) => (
        <FormControlLabel
          key={layer}
          label={label}
          disabled={!available[layer]}
          sx={{ m: 0 }}
          control={
            <Checkbox
              checked={!!layers[layer]}
              onChange={() => setLayers({ ...layers, [layer]: !layers[layer] })}
            />
          }
        />
      ))}
    </FormGroup>
  </>
);

const centered = (
  <Box
    sx={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      height: "100%",
    }}
  >
    <CircularProgress />
  </Box>
);

interface GcnSelectionFormProps {
  dateobs: string;
}

const GcnSelectionForm = ({ dateobs }: GcnSelectionFormProps) => {
  const dispatch = useAppDispatch();
  const isBig = useMediaQuery(useTheme().breakpoints.up("md"));
  const [fetchInstrumentSkymap] = useLazyGetInstrumentSkymapQuery();
  const [fetchGcnEventObservations] = useLazyGetGcnEventObservationsQuery();
  const [submitObservationsTreasureMap] =
    useSubmitObservationsTreasureMapMutation();
  const { download: downloadObservations, progress: observationsProgress } =
    useDownloadAll("observations");

  const { data: gcnEvent } = useGetGcnEventQuery(dateobs ?? skipToken) as {
    data: any;
  };
  const groups = (useGetGroupsQuery().data?.userAccessible ?? []) as any[];
  const galaxyCatalogs = (useGetGalaxyCatalogsQuery().data ?? []) as any[];
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery() as {
    data: any[];
  };

  const [selectedFields, setSelectedFields] = useState<number[]>([]);
  const [selectedInstrumentId, setSelectedInstrumentId] = useState<any>(null);
  const [selectedLocalizationId, setSelectedLocalizationId] =
    useState<any>(null);
  const [plotLayers, setPlotLayers] = useState<PlotLayers>({
    localization: true,
    sun_moon: true,
  });
  const [projection, setProjection] = useState("orthographic");
  const [skymapInstrument, setSkymapInstrument] = useState<any>(null);
  const [tabIndex, setTabIndex] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [treasureMapSubmittingId, setTreasureMapSubmittingId] =
    useState<any>(null);
  const [hasFetchedObservations, setHasFetchedObservations] = useState(false);
  const [gcnEventObservations, setGcnEventObservations] = useState<any>(null);
  const [selectedFormData, setSelectedFormData] = useState<any>({});
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

  const defaultStartDate = dayjs
    .utc(gcnEvent?.dateobs)
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs
    .utc(gcnEvent?.dateobs)
    .add(7, "day")
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const [formDataState, setFormDataState] = useState<any>({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
  });

  const selectedLocalization = gcnEvent?.localizations?.find(
    (loc: any) => loc.id === selectedLocalizationId,
  );
  const selectedLocalizationName = selectedLocalization?.localization_name;
  const instLookUp = Object.fromEntries(instrumentList.map((i) => [i.id, i]));
  const telLookUp = Object.fromEntries(
    telescopeList.map((tel: any) => [tel.id, tel]),
  );
  const selectedInstrument = instLookUp[selectedInstrumentId];

  const {
    data: analysisLoc,
    isFetching: fetchingLocalization,
    isLoading: loadingLocalization,
  } = useGetLocalizationQuery(
    {
      dateobs: gcnEvent?.dateobs,
      localization_name: selectedLocalizationName,
    },
    { skip: !gcnEvent?.dateobs || !selectedLocalizationName },
  );

  const [gcnSourcesArgs, setGcnSourcesArgs] = useState<{
    dateobs: any;
    filterParams?: any;
  } | null>(null);
  const { data: gcnEventSources, isFetching: sourcesFetching } =
    useFetchGcnEventSourcesQuery(gcnSourcesArgs!, {
      skip: gcnSourcesArgs == null,
    }) as any;
  const [gcnGalaxiesArgs, setGcnGalaxiesArgs] = useState<{
    dateobs: any;
    filterParams?: any;
  } | null>(null);
  const { data: gcnEventGalaxies, isFetching: galaxiesFetching } =
    useGetGcnEventGalaxiesQuery(gcnGalaxiesArgs!, {
      skip: gcnGalaxiesArgs == null,
    }) as any;

  useEffect(() => {
    if (
      !dateobs ||
      dateobs !== gcnEvent?.dateobs ||
      !instrumentList.length ||
      !gcnEvent?.localizations?.length ||
      (selectedLocalizationId !== null && !selectedLocalization) ||
      fetchingLocalization
    ) {
      return;
    }
    const defaultInstrument =
      instrumentList.find((i) => i.name === "ZTF") ??
      [...instrumentList].sort((a, b) => a.id - b.id)[0];
    setSelectedInstrumentId(defaultInstrument?.id);
    setSelectedLocalizationId(gcnEvent.localizations[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instrumentList]);

  useEffect(() => {
    if (isBig && tabIndex === 0) setTabIndex(1);
  }, [isBig, tabIndex]);

  useEffect(() => {
    if (!selectedInstrument || !selectedLocalization) return;
    fetchInstrumentSkymap({
      id: selectedInstrumentId,
      localization: selectedLocalization,
    }).then(({ data }) => data && setSkymapInstrument(data));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLocalizationId, selectedInstrumentId]);

  if (gcnEvent?.dateobs !== dateobs) return <Spinner />;

  const queryParams = (formData: any) => ({
    ...formData,
    startDate: cleanDate(formData.startDate),
    endDate: cleanDate(formData.endDate),
    numPerPage: 100,
    pageNumber: 1,
    ...(selectedLocalizationName && {
      localizationName: selectedLocalizationName,
    }),
  });

  const handleSourcesSearch = (formData: any) => {
    const params = queryParams(formData);
    setGcnSourcesArgs({ dateobs, filterParams: params });
    setSourceFilteringState(params);
  };

  const handleSubmit = async ({ formData }: any) => {
    const telescope = telLookUp[selectedInstrument?.telescope_id];
    if (!selectedInstrument || !telescope) {
      dispatch(
        showNotification(
          "Please select an instrument and telescope before fetching observations",
          "error",
          4000,
        ),
      );
      return;
    }
    setIsSubmitting(true);
    const params = { ...queryParams(formData), includeGeoJSON: true };
    const { data } = await fetchGcnEventObservations({
      dateobs,
      filterParams: {
        ...params,
        instrumentName: selectedInstrument.name,
        telescopeName: telescope.name,
        numberObservations: params.numberDetections || 1,
      },
    });
    if (data) setGcnEventObservations(data);
    setHasFetchedObservations(true);
    setFormDataState(params);
    setIsSubmitting(false);
  };

  const handleSubmitTreasureMap = async () => {
    if (!hasFetchedObservations) {
      dispatch(
        showNotification(
          "Please fetch observations before submitting to treasure map",
          "error",
        ),
      );
      return;
    }
    const { startDate, endDate, localizationCumprob, localizationName } =
      formDataState;
    setTreasureMapSubmittingId(selectedInstrumentId);
    await submitObservationsTreasureMap({
      id: selectedInstrumentId,
      data: {
        startDate,
        endDate,
        localizationCumprob,
        localizationName,
        localizationDateobs: dateobs,
      },
    });
    setTreasureMapSubmittingId(null);
  };

  const handleExecutedDownload = () =>
    downloadObservations(
      gcnEventObservations.totalMatches,
      100,
      async (pageNumber) => {
        const result: any = await fetchGcnEventObservations({
          dateobs,
          filterParams: {
            ...formDataState,
            instrumentName: selectedInstrument?.name,
            telescopeName: telLookUp[selectedInstrument?.telescope_id]?.name,
            numberObservations: formDataState.numberDetections || 1,
            numPerPage: 100,
            pageNumber,
            includeGeoJSON: true,
          },
        }).unwrap();
        return result.observations;
      },
    );

  const observationsSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        format: "date-time",
        title: "Start Date",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        format: "date-time",
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
      requireDetections: {
        type: "boolean",
        title: "Require detections",
        default: true,
      },
      group_ids: {
        title: "Groups",
        type: "array",
        items: { type: "integer", enum: groups.map((group) => group.id) },
        uniqueItems: true,
      },
    },
    required: [
      "startDate",
      "endDate",
      "localizationCumprob",
      "requireDetections",
    ],
  };

  const uiSchema = {
    group_ids: { "ui:enumNames": groups.map((group) => group.name) },
    "ui:grid": [
      { __section: "Time range" },
      { startDate: 6, endDate: 6 },
      { __section: "Filters" },
      { numberDetections: 4, localizationCumprob: 4, requireDetections: 4 },
      { __section: "Groups" },
      { group_ids: 12 },
    ],
  };

  const plot = analysisLoc?.id === selectedLocalizationId &&
    !loadingLocalization && (
      <Suspense fallback={<CircularProgress />}>
        <LocalizationPlot
          localization={analysisLoc}
          sources={gcnEventSources}
          galaxies={gcnEventGalaxies}
          instrument={skymapInstrument}
          observations={gcnEventObservations}
          options={plotLayers}
          selectedFields={selectedFields}
          setSelectedFields={setSelectedFields}
          projection={projection}
        />
      </Suspense>
    );

  const controls = {
    projection,
    setProjection,
    layers: plotLayers,
    setLayers: setPlotLayers,
    available: {
      localization: !!gcnEvent.localizations?.length,
      sources: !!gcnEventSources,
      galaxies: !!gcnEventGalaxies,
      instrument: !!skymapInstrument,
      observations: !!gcnEventObservations,
      sun_moon: true,
      galactic_plane: true,
    },
  };

  const selectSx = { mt: "0.3rem", maxWidth: "87vw" };

  return (
    <Grid container spacing={4}>
      <Grid size={{ sm: 4 }} sx={{ display: { xs: "none", md: "block" } }}>
        {plot ? (
          <Box sx={{ mt: 1 }}>
            {plot}
            <SkymapControls {...controls} />
          </Box>
        ) : (
          centered
        )}
      </Grid>
      <Grid size={{ sm: 12, md: 8 }}>
        <Box sx={selectSx}>
          <InputLabel id="localizationSelectLabel">Localization</InputLabel>
          <Select
            fullWidth
            inputProps={{ MenuProps: { disableScrollLock: true } }}
            labelId="localizationSelectLabel"
            value={selectedLocalizationId || ""}
            onChange={(e) => setSelectedLocalizationId(e.target.value)}
          >
            {gcnEvent.localizations?.map((localization: any) => (
              <MenuItem value={localization.id} key={localization.id}>
                {`Skymap: ${localization.localization_name} / Created: ${localization.created_at}`}
              </MenuItem>
            ))}
          </Select>
        </Box>
        <Tabs
          value={tabIndex}
          onChange={(_, value) => setTabIndex(value)}
          aria-label="gcn_tabs"
          variant="scrollable"
          sx={{ maxWidth: "95vw" }}
        >
          <Tab label="Skymap" sx={{ display: { md: "none" } }} />
          <Tab label="Sources" />
          <Tab label="Associated Events" />
          <Tab label="Galaxies" />
          <Tab label="Observations" />
        </Tabs>

        {tabIndex === 0 && (
          <Box sx={{ display: { md: "none" } }}>
            {plot ? (
              <Grid container spacing={2}>
                <Grid
                  size={{ sm: 8, md: 12 }}
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    alignItems: "center",
                    maxWidth: "90vw",
                    width: "100%",
                  }}
                >
                  {plot}
                </Grid>
                <Grid size={{ xs: 9, sm: 4, md: 12 }}>
                  <SkymapControls {...controls} column />
                </Grid>
              </Grid>
            ) : (
              centered
            )}
          </Box>
        )}

        {tabIndex === 1 && (
          <>
            <GcnSourcesQueryForm
              defaultStartDate={defaultStartDate}
              defaultEndDate={defaultEndDate}
              groups={groups}
              isSubmitting={sourcesFetching}
              onSearch={handleSourcesSearch}
            />
            {gcnEventSources?.sources ? (
              selectedLocalizationName && (
                <GcnEventSourcesPage
                  dateobs={dateobs}
                  sources={gcnEventSources}
                  localizationName={selectedLocalizationName}
                  sourceFilteringState={sourceFilteringState}
                  setGcnSourcesArgs={setGcnSourcesArgs}
                />
              )
            ) : (
              <Typography variant="body1">
                {gcnSourcesArgs == null
                  ? "Run the query to list sources in this localization."
                  : "Fetching sources..."}
              </Typography>
            )}
          </>
        )}

        {tabIndex === 2 && (
          <Box sx={{ p: "0.5rem" }}>
            <GcnEventAssociations dateobs={dateobs} />
          </Box>
        )}

        {tabIndex === 3 && (
          <GcnGalaxiesTab
            dateobs={dateobs}
            localizationName={selectedLocalizationName}
            galaxyCatalogs={galaxyCatalogs}
            galaxies={gcnEventGalaxies}
            isFetching={galaxiesFetching}
            hasRun={gcnGalaxiesArgs != null}
            onSearch={setGcnGalaxiesArgs}
          />
        )}

        {tabIndex === 4 && (
          <>
            <Box sx={selectSx}>
              <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
              <Select
                fullWidth
                inputProps={{ MenuProps: { disableScrollLock: true } }}
                labelId="instrumentSelectLabel"
                value={selectedInstrumentId || ""}
                onChange={(e) => setSelectedInstrumentId(e.target.value)}
              >
                {[...instrumentList]
                  .sort((a, b) => a.name.localeCompare(b.name))
                  .map((instrument) => (
                    <MenuItem value={instrument.id} key={instrument.id}>
                      {`${telLookUp[instrument.telescope_id]?.name} / ${instrument.name}`}
                    </MenuItem>
                  ))}
              </Select>
            </Box>
            <Box
              data-testid="gcnsource-selection-form"
              sx={{ mt: "0.8rem", maxWidth: "87vw" }}
            >
              <Form
                schema={observationsSchema as any}
                formData={selectedFormData}
                onChange={(e: any) => setSelectedFormData(e.formData)}
                uiSchema={uiSchema}
                templates={{
                  ObjectFieldTemplate: MyObjectFieldTemplate as any,
                }}
                validator={validator}
                onSubmit={handleSubmit}
                customValidate={validate}
                disabled={isSubmitting}
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
            </Box>
            {selectedLocalizationId ? (
              <Box
                sx={{
                  display: "grid",
                  gap: "1rem",
                  gridTemplateColumns: "repeat(auto-fit, minmax(5rem, 1fr))",
                  mb: "1rem",
                  maxWidth: "87vw",
                  "& > button": { maxHeight: "4rem", lineHeight: "1rem" },
                }}
              >
                <Suspense fallback={<CircularProgress />}>
                  <GcnSummary dateobs={dateobs} />
                </Suspense>
                <Suspense fallback={<CircularProgress />}>
                  <GcnReport dateobs={dateobs} />
                </Suspense>
                <AddSurveyEfficiencyObservationsPage dateobs={dateobs} />
                <AddCatalogQueryPage dateobs={dateobs} />
                {treasureMapSubmittingId === selectedInstrumentId ? (
                  <CircularProgress />
                ) : (
                  <Button
                    secondary
                    onClick={handleSubmitTreasureMap}
                    size="small"
                    data-testid={`treasuremapRequest_${selectedInstrumentId}`}
                  >
                    Send to Treasure Map
                  </Button>
                )}
              </Box>
            ) : (
              <CircularProgress />
            )}
            {!gcnEventObservations?.observations ? (
              <Typography variant="h5">Fetching observations...</Typography>
            ) : gcnEventObservations.observations.length === 0 ? (
              <Typography
                variant="body1"
                color="textSecondary"
                align="center"
                sx={{ py: 3 }}
              >
                No observations found within localization with these filters.
              </Typography>
            ) : (
              <>
                <ExecutedObservationsTable
                  observations={gcnEventObservations.observations}
                  totalMatches={gcnEventObservations.totalMatches}
                  numPerPage={
                    formDataState.numPerPage ||
                    gcnEventObservations.numPerPage ||
                    100
                  }
                  downloadCallback={handleExecutedDownload}
                  serverSide={false}
                />
                <DownloadProgressDialog
                  {...observationsProgress}
                  label="observations"
                />
              </>
            )}
          </>
        )}
      </Grid>
    </Grid>
  );
};

export default GcnSelectionForm;

export { MyObjectFieldTemplate };
