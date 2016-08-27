import React from 'react'

class StageLayout extends React.Component {

  static get defaultProps() {return{
    title: 'untitled',
    subtitle: null,
    buttons: null
  }}

  constructor(props) {
    super(props)
  }

  render() {
    let subtitle = null
    if (this.props.subtitle) {
      subtitle = <span>{this.props.subtitle}</span>
    }
    return(
      <div className="stage">
        <div className="header">
          {this.props.title}
          {subtitle}
        </div>
        <div className="body">
          {this.props.children}
        </div>
        <div className="footer">
          {this.props.buttons}
        </div>
      </div>
    )
  }
}

export default StageLayout