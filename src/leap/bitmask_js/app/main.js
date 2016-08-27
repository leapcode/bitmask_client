import React from 'react'
import ReactDOM from 'react-dom'

import PanelSwitcher from 'components/panel_switcher'
import App from 'app'

class Main extends React.Component {
  render() {
    return React.createElement(PanelSwitcher)
  }

  //
  // main entry point for app execution
  //
  componentDidMount() {
    App.start()
  }
}

ReactDOM.render(
  React.createElement(Main),
  document.getElementById('app')
)