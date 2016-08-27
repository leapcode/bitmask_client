//
// A bootstrap panel, but with some extra options
//

import React from 'react'
// import {Panel} from 'react-bootstrap'

class Area extends React.Component {

  static get defaultProps() {return{
     position: null,  // top or bottom
     size: 'small',   // small or big
     type: null,      // light or dark
     className: null
  }}

  constructor(props) {
    super(props)
  }

  render() {
    let style = {}
    let innerstyle = {}
    if (this.props.position == 'top') {
      style.borderBottomRightRadius = '0px'
      style.borderBottomLeftRadius = '0px'
      style.marginBottom = '0px'
      style.borderBottom = '0px'
      if (this.props.size == 'big') {
        innerstyle.padding = '25px'
      }
    } else if (this.props.position == 'bottom') {
      style.borderTopRightRadius = '0px'
      style.borderTopLeftRadius = '0px'
      style.borderTop = '0px'
      if (this.props.size == 'big') {
        innerstyle.padding = '15px 25px'
      }
    }

    let type = this.props.type ? "area-" + this.props.type : ""
    let className = ['panel', 'panel-default', type, this.props.className].join(' ')
    return(
      <div className={className} style={style}>
        <div className="panel-body" style={innerstyle}>
          {this.props.children}
        </div>
      </div>
    )
  }

}

// Area.propTypes = {
//   children: React.PropTypes.oneOfType([
//     React.PropTypes.element,
//     React.PropTypes.arrayOf(React.PropTypes.element)
//   ])
// }

//Area.propTypes = {
//  children: React.PropTypes.element.isRequired
//}

export default Area
