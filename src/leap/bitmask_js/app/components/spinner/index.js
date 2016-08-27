import React from 'react';
import './spinner.css';

class Spinner extends React.Component {
  render() {
    let props = {}
    return <div className="spinner">
      <div className="spin1"></div>
      <div className="spin2"></div>
      <div className="spin3"></div>
    </div>
  }
}

export default Spinner