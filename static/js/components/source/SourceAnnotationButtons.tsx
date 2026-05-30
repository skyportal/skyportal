import React, { useState } from "react";

import CircularProgress from "@mui/material/CircularProgress";
import Button from "../Button";

import SourceAnnotationButtonPlugins from "./SourceAnnotationButtonPlugins";

import { useAppDispatch } from "../../types/hooks";
import * as sourceActions from "../../ducks/source";
import type { Source } from "../../types";

interface SourceAnnotationButtonsProps {
  source: Source;
}

const SourceAnnotationButtons = ({ source }: SourceAnnotationButtonsProps) => {
  const dispatch = useAppDispatch();

  const [isSubmittingAnnotationGaia, setIsSubmittingAnnotationGaia] =
    useState<any>(null);
  const handleAnnotationGaia = async (id: string) => {
    setIsSubmittingAnnotationGaia(id);
    await dispatch(sourceActions.fetchGaia(id));
    setIsSubmittingAnnotationGaia(null);
  };

  const [isSubmittingAnnotationWise, setIsSubmittingAnnotationWise] =
    useState<any>(null);
  const handleAnnotationWise = async (id: string) => {
    setIsSubmittingAnnotationWise(id);
    await dispatch(sourceActions.fetchWise(id));
    setIsSubmittingAnnotationWise(null);
  };

  const [isSubmittingAnnotationQuasar, setIsSubmittingAnnotationQuasar] =
    useState<any>(null);
  const handleAnnotationQuasar = async (id: string) => {
    setIsSubmittingAnnotationQuasar(id);
    await dispatch(sourceActions.fetchVizier(id, "VII/290"));
    setIsSubmittingAnnotationQuasar(null);
  };

  const [isSubmittingAnnotationGalex, setIsSubmittingAnnotationGalex] =
    useState<any>(null);
  const handleAnnotationGalex = async (id: string) => {
    setIsSubmittingAnnotationGalex(id);
    await dispatch(sourceActions.fetchVizier(id, "II/335/galex_ais"));
    setIsSubmittingAnnotationGalex(null);
  };

  const [isSubmittingAnnotationPhotoz, setIsSubmittingAnnotationPhotoz] =
    useState<any>(null);
  const handleAnnotationPhotoz = async (id: string) => {
    setIsSubmittingAnnotationPhotoz(id);
    await dispatch(sourceActions.fetchPhotoz(id));
    setIsSubmittingAnnotationPhotoz(null);
  };

  const [isSubmittingAnnotationPS1, setIsSubmittingAnnotationPS1] =
    useState<any>(null);
  const handleAnnotationPS1 = async (id: string) => {
    setIsSubmittingAnnotationPS1(id);
    await dispatch(sourceActions.fetchPS1(id));
    setIsSubmittingAnnotationPS1(null);
  };

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        flexDirection: "row",
        gap: "0.5rem",
      }}
    >
      {isSubmittingAnnotationGaia === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationGaia(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`gaiaRequest_${source.id}`}
        >
          Gaia
        </Button>
      )}
      {isSubmittingAnnotationWise === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationWise(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`wiseRequest_${source.id}`}
        >
          WISE Colors
        </Button>
      )}
      {isSubmittingAnnotationQuasar === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationQuasar(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`quasarRequest_${source.id}`}
        >
          Million Quasar
        </Button>
      )}
      {isSubmittingAnnotationGalex === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationGalex(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`galexRequest_${source.id}`}
        >
          GALEX
        </Button>
      )}
      {isSubmittingAnnotationPhotoz === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationPhotoz(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`photozRequest_${source.id}`}
        >
          Photoz
        </Button>
      )}
      {isSubmittingAnnotationPS1 === source.id ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <Button
          secondary
          onClick={() => {
            handleAnnotationPS1(source.id);
          }}
          size="small"
          type="submit"
          data-testid={`ps1Request_${source.id}`}
        >
          PS1
        </Button>
      )}
      <SourceAnnotationButtonPlugins {...({ source } as any)} />
    </div>
  );
};

export default SourceAnnotationButtons;
