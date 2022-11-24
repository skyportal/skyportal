import React, { Component, memo } from "react";
import PropTypes from "prop-types";

import MUIDataTable from "mui-datatables";

class CustomDataTable extends Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  render() {
    const { title, data, columns, options } = this.props;
    return (
      <div>
        <MUIDataTable
          title={title}
          data={data}
          columns={columns}
          options={options}
        />
      </div>
    );
  }
}

CustomDataTable.propTypes = {
  title: PropTypes.string.isRequired,
  data: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
  columns: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
  options: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
};

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
  return (
    areEqual(nextProps.data, prevProps.data) &&
    areEqual(nextProps.groupIds, prevProps.groupIds)
  );
};

export default memo(CustomDataTable, customComparator);
