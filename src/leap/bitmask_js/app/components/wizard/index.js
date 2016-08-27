//
// The provider setup wizard
//

import React from 'react'
import App from 'app'

import ProviderSelectStage from './provider_select_stage'
import './wizard.less'

export default class Wizard extends React.Component {

  constructor(props) {
    super(props)
    this.state = {
      stage: 'provider'
    }
  }

  setStage(stage) {
    this.setState({stage: stage})
  }

  render() {
    let stage = null
    switch(this.state.stage) {
      case 'provider':
        stage = <ProviderSelectStage />
        break
    }
    return(
      <div className="wizard">
        {stage}
      </div>
    )
  }

}
