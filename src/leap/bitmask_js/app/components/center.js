//
// puts a block right in the center of the window
//

import React from 'react'

const CONTAINER_CSS = {
  position: 'absolute',
  display: 'flex',
  justifyContent: 'center',
  alignContent: 'center',
  alignItems: 'center',
  top: "0px",
  left: "0px",
  height: "100%",
  width: "100%"
}

const ITEM_CSS = {
  flex: "0 1 auto"
}

class Center extends React.Component {

  static get defaultProps() {return{
    width: null
  }}

  constructor(props) {
    super(props)
  }

  render() {
    let style = this.props.width ? Object.assign({width: this.props.width + 'px'}, ITEM_CSS) : ITEM_CSS
    return (
      <div className="center-container" style={CONTAINER_CSS}>
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
