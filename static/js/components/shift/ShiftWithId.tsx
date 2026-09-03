import withRouter from "../withRouter";
import ShiftPage from "./ShiftPage";

interface ShiftWithIdProps {
  route: {
    id: string;
  };
}

const ShiftWithId = ({ route }: ShiftWithIdProps) => (
  <ShiftPage route={route} />
);

export default withRouter(ShiftWithId);
