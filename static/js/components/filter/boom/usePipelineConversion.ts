import { useCallback, useState } from "react";

import { useFilterBuilder } from "../../../hooks/useContexts";
import { usePostFilterElementMutation } from "../../../ducks/boom_filter_modules";
import { decompileFilterPipeline } from "../../../utils/mongoPipelineDecompiler";
import { surveyToken } from "./dialog/ModuleStreams";

const KINDS = [
  { kind: "variables", setter: "setCustomVariables", type: "number" },
  { kind: "listVariables", setter: "setCustomListVariables", type: "array" },
  {
    kind: "switchCases",
    setter: "setCustomSwitchCases",
    type: "switch_variable",
  },
];

const usePipelineConversion = (streamName?: string) => {
  const builder = useFilterBuilder();
  const [postElement] = usePostFilterElementMutation();
  const [conversion, setConversion] = useState<any>(null);

  const convert = useCallback(
    (pipeline: any[]): any => {
      const token = surveyToken(streamName);
      return decompileFilterPipeline(pipeline, {
        schema: builder.schema,
        fieldOptions: builder.fieldOptions,
        customVariables: builder.customVariables,
        customListVariables: builder.customListVariables,
        customSwitchCases: builder.customSwitchCases,
        reservedNames: builder.catalogNames,
        streams: token ? [token] : [],
      });
    },
    [
      streamName,
      builder.schema,
      builder.fieldOptions,
      builder.customVariables,
      builder.customListVariables,
      builder.customSwitchCases,
      builder.catalogNames,
    ],
  );

  const adopt = useCallback(
    (original: any[], result: any) => {
      KINDS.forEach(({ kind, setter }) => {
        const added = result.newVariables[kind];
        if (added.length === 0) return;
        builder[setter]((prev: any[]) => [
          ...prev.filter((v) => !added.some((a: any) => a.name === v.name)),
          ...added,
        ]);
      });
      setConversion({ original, newVariables: result.newVariables });
    },
    [builder],
  );

  const saveNewVariables = useCallback(async () => {
    if (!conversion) return;
    await Promise.all(
      KINDS.flatMap(({ kind, type }) =>
        conversion.newVariables[kind].map(({ name, ...data }: any) =>
          postElement({
            name,
            data: { type, ...data },
            elements: kind,
          }).unwrap(),
        ),
      ),
    );
    setConversion(null);
  }, [conversion, postElement]);

  return {
    conversion,
    convert,
    adopt,
    saveNewVariables,
    clearConversion: () => setConversion(null),
  };
};

export default usePipelineConversion;
