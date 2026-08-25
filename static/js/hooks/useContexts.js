import { useContext } from "react";
import { useLocation } from "react-router-dom";

import { UnifiedBuilderContext } from "../contexts/UnifiedBuilderContext";
import { ConditionContext } from "../contexts/ConditionContext";

export const useAnnotationBuilder = () => {
  const context = useContext(UnifiedBuilderContext);

  if (!context) {
    throw new Error(
      "useAnnotationBuilder must be used within an AnnotationBuilderProvider",
    );
  }

  return context;
};

export const useConditionContext = () => {
  const context = useContext(ConditionContext);
  if (!context) {
    throw new Error(
      "useConditionContext must be used within a ConditionProvider",
    );
  }
  return context;
};

export const useFilterBuilder = () => {
  const context = useContext(UnifiedBuilderContext);
  if (!context) {
    throw new Error(
      "useFilterBuilder must be used within FilterBuilderProvider",
    );
  }
  return context;
};

export const useCurrentBuilder = () => {
  const location = useLocation();
  const context = useContext(UnifiedBuilderContext);

  if (!context) {
    throw new Error(
      "useCurrentBuilder must be used within a UnifiedBuilderProvider",
    );
  }

  // The UnifiedBuilderContext already handles mode switching internally
  // so we can just return the context directly
  return context;
};
