import { UnifiedBuilderProvider } from "../../../contexts/UnifiedBuilderContext";
import AnnotationBuilderContent from "./AnnotationBuilderContent";

const AnnotationBuilder = () => {
  return (
    <UnifiedBuilderProvider mode="annotation">
      <AnnotationBuilderContent />
    </UnifiedBuilderProvider>
  );
};

export default AnnotationBuilder;
