import React from 'react'
import App from '../app'


class DebugPanel extends React.Component {

  constructor(props) {
    super(props)
    this.click = this.click.bind(this)
  }

  componentDidMount() {
    this.click(window.location.hash.replace('#', ''))
  }

  click(panel_name) {
    window.location.hash = panel_name
    App.show(panel_name)
  }

  panel(panel_name) {
    return elem(
      'a',
      { onClick: () => this.click(panel_name), key: panel_name },
      panel_name
    )
  }

  render() {
    return elem('div', {className: 'debug-panel'},
      this.panel('splash'),
      this.panel('greeter'),
      this.panel('wizard'),
      this.panel('main')
    )
  }

}

export default DebugPanel