//
// This is the layout for a service section in the main window.
// It does not do anything except for arrange items using css and html.
//

import React from 'react'

export default class SectionLayout extends React.Component {

  static get defaultProps() {return{
    icon: null,
    buttons: null,
    status: null,
    className: "",
    style: {}
  }}

  constructor(props) {
    super(props)
  }

  render() {
    let className = ["service-section", this.props.className].join(' ')
    let status = null
    let icon = null
    let buttons = null

    if (this.props.status) {
      status = (
        <div className="status">
          <img src={'img/' + this.props.status + '.svg' } />
        </div>
      )
    }
    if (this.props.icon) {
      icon = (
        <div className="icon">
          <img src={'img/' + this.props.icon + '.svg'} />
        </div>
      )
    }
    if (this.props.buttons)
      buttons = (
        <div className="buttons">
          {this.props.buttons}
        </div>
      )
    return(
      <div className={className} style={this.props.style}>
        {icon}
        <div className="body">
          {this.props.children}
        </div>
        {buttons}
        {status}
      </div>
    )
  }
}
