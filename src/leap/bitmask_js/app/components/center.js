//
// puts a block right in the center of the window
//

import React from 'react'

class Center extends React.Component {

  static get defaultProps() {return{
    width: null
  }}

  constructor(props) {
    super(props)
  }

  render() {
    let style = null
    if (this.props.width) {
      style = {width: this.props.width + 'px'}
    }
    return (
      <div className="center-container">
        <div className="center-item" style={style}>
          {this.props.children}
        </div>
      </div>
    )
  }
}

Center.propTypes = {
  children: React.PropTypes.oneOfType([
    React.PropTypes.element,
    React.PropTypes.arrayOf(React.PropTypes.element)
  ])
}

export default Center
