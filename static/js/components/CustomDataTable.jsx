import React, { memo } from "react";
import MUIDataTable from "mui-datatables";

class CustomDataTable extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <div>
        <MUIDataTable
          title={this.props.title}
          data={this.props.data}
          columns={this.props.columns}
          options={this.props.options}
        />
      </div>
    );
  }
}

const customComparator = (prevProps, nextProps) => {
  function areEqual(array1, array2) {
    if (array1.length === array2.length) {
      return array1.every((element) => {
        if (array2.includes(element)) {
          return true;
        }

        return false;
      });
    }
    return false;
  }
  return areEqual(nextProps.data, prevProps.data);
};

export default memo(CustomDataTable, customComparator);
